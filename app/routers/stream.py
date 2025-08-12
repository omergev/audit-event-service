# app/routers/stream.py
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
from typing import AsyncGenerator

from app.services.stream_bus import get_stream_bus

logger = logging.getLogger(__name__)
router = APIRouter()  # expose /stream at root

@router.get("/stream")
async def stream_ndjson(request: Request):
    """
    NDJSON stream of real-time events.
    A background task reads from the bus's pubsub and enqueues JSON objects to an asyncio.Queue.
    The response generator blocks on queue.get() and yields each object as one NDJSON line.
    """
    bus = get_stream_bus()

    # Open a dedicated subscriber up front so tests can probe "subscriber is ready".
    try:
        pubsub = await bus.open_subscriber()
        logger.debug("stream: subscriber opened")
    except Exception as ex:
        logger.exception("stream: failed to open subscriber: %s", ex)
        raise HTTPException(status_code=503, detail="Stream service unavailable")

    async def gen() -> AsyncGenerator[bytes, None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        stop_event = asyncio.Event()

        async def reader():
            """
            Background reader: pull JSON payloads from the pubsub and push into the queue.
            Backpressure: if the queue is full, drop the oldest to make room.
            """
            try:
                async for msg in pubsub.listen():
                    if stop_event.is_set():
                        break
                    data = msg.get("data")
                    if not data:
                        continue
                    try:
                        obj = json.loads(data)
                    except Exception as ex:
                        logger.exception("stream: failed to decode pubsub message: %s", ex)
                        continue
                    if queue.full():
                        try:
                            _ = queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    await queue.put(obj)
            except asyncio.CancelledError:
                # Normal shutdown path.
                pass
            except Exception as ex:
                logger.exception("stream: reader task error: %s", ex)

        reader_task = asyncio.create_task(reader())

        try:
            while True:
                # Stop if client disconnects.
                if await request.is_disconnected():
                    logger.info("stream: client disconnected")
                    break

                # Block for next event and emit as NDJSON line.
                item = await queue.get()
                line = (json.dumps(item, separators=(",", ":")) + "\n").encode("utf-8")
                yield line
        except asyncio.CancelledError:
            # Stream was cancelled by server shutdown.
            return
        finally:
            # Ensure pubsub is closed and reader is cancelled.
            try:
                stop_event.set()
                reader_task.cancel()
            except Exception:
                pass
            try:
                await bus.close_subscriber(pubsub)
            except Exception:
                pass

    headers = {
        "Cache-Control": "no-store",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen(), media_type="application/x-ndjson", headers=headers)


@router.get("/__stream_probe__")
async def stream_probe():
    """
    Test/diagnostic endpoint: returns the current number of stream subscribers if the bus exposes it.
    Production RedisBus doesn't implement it; in that case we return subscribers=None.
    Tests can monkeypatch a FakeBus that implements subscriber_count().
    """
    bus = get_stream_bus()
    count = None
    # Try sync or async method if provided by the test FakeBus
    if hasattr(bus, "subscriber_count"):
        try:
            maybe_coro = bus.subscriber_count()
            if asyncio.iscoroutine(maybe_coro):
                count = await maybe_coro
            else:
                count = maybe_coro
        except Exception:
            count = None
    return {"subscribers": count}
