# # tests/conftest.py

# import os
# import pytest
# import httpx
# import asyncio
# import json
# from app.main import app

# BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")

# # A simple in-memory Pub/Sub that mimics the Redis interface we use
# class _FakePubSub:
#     def __init__(self, queue: asyncio.Queue):
#         self._q = queue
#         self._closed = False

#     async def listen(self):
#         # Yield dicts like aioredis pubsub.listen() returns
#         while not self._closed:
#             data = await self._q.get()
#             yield {"type": "message", "data": data}

#     async def close(self):
#         self._closed = True

# class _FakeStreamBus:
#     def __init__(self):
#         self._queue = asyncio.Queue()

#     async def open_subscriber(self):
#         return _FakePubSub(self._queue)

#     async def close_subscriber(self, pubsub: _FakePubSub):
#         await pubsub.close()

#     # Match to RedisBus.publish(event_json)
#     async def publish(self, event_json: dict):
#         await self._queue.put(json.dumps(event_json))


# @pytest.fixture(autouse=True)
# def patch_stream_bus(monkeypatch):
#     """
#     Patch app.services.stream_bus.get_stream_bus() to return a shared in-memory bus.
#     This removes the dependency on real Redis during tests and avoids flakiness/timeouts.
#     """
#     from app import services
#     # create a singleton per test session (per worker)
#     fake = _FakeStreamBus()

#     def _get_stream_bus():
#         return fake

#     # Make sure imports line up with your project structure
#     monkeypatch.setattr(services.stream_bus, "get_stream_bus", _get_stream_bus)
#     yield


# @pytest.fixture
# def base_url():
#     # Simple fixture for base URL (can be overridden via env)
#     return BASE_URL


# @pytest.fixture
# async def async_client():
#     # Async HTTP client for tests
#     transport = httpx.ASGITransport(app=app, lifespan="on")
#     async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
#         yield client
