# app/routers/stream.py
from fastapi import APIRouter, Request
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
    GET /stream
    NDJSON stream that emits only real events (no heartbeats).
    A background task reads Redis Pub/Sub and enqueues messages into an asyncio.Queue.
    The generator blocks on queue.get() and yields each event line as it arrives.
    """
    bus = get_stream_bus()

    async def gen() -> AsyncGenerator[bytes, None]:
        pubsub = await bus.open_subscriber()
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        stop_event = asyncio.Event()

        async def reader():
            """Background reader: pull messages from Redis and put into the queue."""
            try:
                async for msg in pubsub.listen():
                    if stop_event.is_set():
                        break
                    if not msg or msg.get("type") != "message":
                        continue
                    data = msg.get("data")
                    if not data:
                        continue
                    try:
                        obj = json.loads(data)
                    except Exception as ex:
                        logger.exception("stream: failed to decode pubsub message: %s", ex)
                        continue
                    # Backpressure: drop oldest if queue is full
                    if queue.full():
                        try:
                            _ = queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    await queue.put(obj)
            except asyncio.CancelledError:
                pass
            except Exception as ex:
                logger.exception("stream: reader task error: %s", ex)

        reader_task = asyncio.create_task(reader())

        try:
            while True:
                if await request.is_disconnected():
                    logger.info("stream: client disconnected")
                    break
                item = await queue.get()  # block until an event arrives
                line = (json.dumps(item, separators=(",", ":")) + "\n").encode("utf-8")
                yield line
        except asyncio.CancelledError:
            return
        finally:
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
