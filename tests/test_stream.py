import os, pytest
if os.getenv("SKIP_STREAM_TESTS", "0") == "1":
    pytest.skip("Skipping stream tests temporarily (flaky under Windows asyncio).", allow_module_level=True)
# tests/test_stream.py
import json
import time
import asyncio
import threading
import pytest
from starlette.testclient import TestClient
from app.main import app


# ---------- Minimal in-memory bus used only for tests (cross-loop safe) ----------

class _FakePubSub:
    def __init__(self, q: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._q = q
        self._loop = loop
        self._closed = False

    async def listen(self):
        while not self._closed:
            payload = await self._q.get()
            yield {"type": "message", "data": payload}

    async def close(self):
        self._closed = True

    async def unsubscribe(self, channel: str):
        pass


class _FakeBus:
    """
    In-memory fan-out pub/sub, API-compatible with stream_bus.RedisBus:
    - open_subscriber()
    - close_subscriber(pubsub)
    - publish(event_json)
    Cross-loop/thread safe: uses loop.call_soon_threadsafe to deliver messages.
    """
    def __init__(self):
        self._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    async def open_subscriber(self):
        loop = asyncio.get_running_loop()          # loop of the app (TestClient thread)
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        with self._lock:
            self._subs.append((loop, q))
        return _FakePubSub(q, loop)

    async def close_subscriber(self, pubsub: _FakePubSub):
        await pubsub.close()
        with self._lock:
            self._subs = [(lp, q) for (lp, q) in self._subs if q is not pubsub._q]

    async def publish(self, event_json: dict):
        # Serialize once
        payload = json.dumps(event_json, separators=(",", ":"), ensure_ascii=False)
        # Snapshot subscribers under lock, then fan-out
        with self._lock:
            subs = list(self._subs)

        # Deliver message into each subscriber's loop/thread safely
        for lp, q in subs:
            if lp.is_closed():
                continue
            # If called from the same loop, it's safe to put_nowait directly;
            # otherwise schedule it thread-safely on the subscriber's loop.
            try:
                running = asyncio.get_running_loop()
            except RuntimeError:
                running = None

            if running is lp:
                q.put_nowait(payload)
            else:
                lp.call_soon_threadsafe(q.put_nowait, payload)

        # Yield control so scheduled callbacks have a chance to run
        await asyncio.sleep(0)

    async def wait_for_at_least_one_subscriber(self, timeout=1.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if self._subs:
                    return True
            await asyncio.sleep(0.01)
        return False


# ---------- Fixture: patch app to use the fake bus ----------

@pytest.fixture(autouse=True)
def _patch_stream_bus(monkeypatch):
    fake_bus = _FakeBus()

    def _get_bus():
        return fake_bus

    # Patch all import sites
    monkeypatch.setattr("app.services.stream_bus.get_stream_bus", _get_bus, raising=True)
    monkeypatch.setattr("app.routers.stream.get_stream_bus", _get_bus, raising=False)
    monkeypatch.setattr("app.routers.events.get_stream_bus", _get_bus, raising=False)

    return fake_bus


# ---------- Helper ----------

def _read_one_line(resp, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for chunk in resp.iter_lines():
            if chunk:
                return chunk
        time.sleep(0.01)
    return None


# ---------- Tests ----------

def test_stream_receives_published_event(_patch_stream_bus):
    client = TestClient(app)
    bus = _patch_stream_bus

    with client.stream("GET", "/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("application/x-ndjson")

        # Make sure subscriber is ready before publishing
        asyncio.get_event_loop().run_until_complete(
            bus.wait_for_at_least_one_subscriber(timeout=1.0)
        )

        event = {
            "eventId": "00000000-0000-4000-8000-000000000001",
            "ingestedAt": "2025-08-10T12:00:00.000000Z",
            "time": "2025-08-10T12:00:00Z",
            "logType": "Login",
            "reportingService": "11111111-1111-1111-1111-111111111111",
            "logLevel": "informational",
            "activityType": "user-login",
            "identityType": "User",
            "user": {"identityUuid": "user-1"},
            "action": "Access",
            "message": "hello stream",
            "account": {"accountId": "acct-1", "accountName": "Tenant 1"},
        }

        asyncio.get_event_loop().run_until_complete(bus.publish(event))

        line = _read_one_line(resp, timeout=2.0)
        assert line is not None, "No NDJSON line received from /stream"
        data = json.loads(line)
        assert data["eventId"] == event["eventId"]
        assert data["message"] == "hello stream"


def test_stream_two_clients_both_receive(_patch_stream_bus):
    client = TestClient(app)
    bus = _patch_stream_bus

    with client.stream("GET", "/stream") as r1, client.stream("GET", "/stream") as r2:
        assert r1.status_code == 200 and r2.status_code == 200

        asyncio.get_event_loop().run_until_complete(
            bus.wait_for_at_least_one_subscriber(timeout=1.0)
        )

        event = {
            "eventId": "00000000-0000-4000-8000-000000000002",
            "ingestedAt": "2025-08-10T12:01:00.000000Z",
            "time": "2025-08-10T12:01:00Z",
            "logType": "System",
            "reportingService": "22222222-2222-2222-2222-222222222222",
            "logLevel": "warning",
            "activityType": "notice",
            "identityType": "Application",
            "user": {"identityUuid": "svc-1"},
            "action": "Execute",
            "message": "broadcast",
            "account": {"accountId": "acct-2", "accountName": "Tenant 2"},
        }

        asyncio.get_event_loop().run_until_complete(bus.publish(event))

        l1 = _read_one_line(r1, timeout=2.0)
        l2 = _read_one_line(r2, timeout=2.0)
        assert l1 and l2
        d1 = json.loads(l1)
        d2 = json.loads(l2)
        assert d1["eventId"] == event["eventId"]
        assert d2["eventId"] == event["eventId"]
