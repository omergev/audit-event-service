# app/services/stream_bus.py
import json
import logging
from typing import Any, Dict, Optional

from redis import asyncio as aioredis
from app.config import REDIS_URL, STREAM_CHANNEL

logger = logging.getLogger(__name__)

class RedisBus:
    """Redis Pub/Sub fan-out across multiple workers."""

    def __init__(self, url: str = REDIS_URL, channel: str = STREAM_CHANNEL):
        self._url = url
        self._channel = channel
        self._pub = aioredis.Redis.from_url(self._url, decode_responses=True)

    async def publish(self, event_json: Dict[str, Any]) -> None:
        payload = json.dumps(event_json, separators=(",", ":"), ensure_ascii=False)
        await self._pub.publish(self._channel, payload)


    async def open_subscriber(self):
        """Create and subscribe a dedicated PubSub connection (ignoring subscribe messages)."""
        pubsub = self._pub.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(self._channel)
        return pubsub

    async def get_message(self, pubsub, timeout: float) -> Optional[Dict[str, Any]]:
        """
        Poll with timeout and return decoded JSON dict if a message arrived.
        Returns None on timeout or invalid payload.
        """
        try:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
            if not msg:
                return None
            data = msg.get("data")
            if not data:
                return None
            try:
                return json.loads(data)
            except Exception as ex:
                logger.exception("redis_bus: failed to decode message: %s", ex)
                return None
        except Exception as ex:
            logger.exception("redis_bus: get_message error: %s", ex)
            return None

    async def close_subscriber(self, pubsub) -> None:
        try:
            await pubsub.unsubscribe(self._channel)
        except Exception:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass

# Singleton accessor
_bus: Optional[RedisBus] = None

def get_stream_bus() -> RedisBus:
    global _bus
    if _bus is None:
        _bus = RedisBus()
    return _bus
