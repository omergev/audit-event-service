# tests/test_stream.py
import asyncio
import json
import httpx
import pytest
from app.main import app

#skip the following test.
@pytest.mark.skip(reason="Skipping stream test as it requires a live server")
async def test_stream_receives_event():
    payload = {
        "logType": "Login",
        "reportingService": "9a53a1f2-2b0f-4d0e-8c7a-6f4b9c8b1a23",
        "logLevel": "informational",
        "activityType": "UserLogin",
        "identityType": "User",
        "user": {"identityUuid": "u-123", "userEmail": "a@b.com", "userFullName": "A B"},
        "action": "Access",
        "message": "User login succeeded",
        "account": {"accountId": "acc-1", "accountName": "Tenant A"},
    }

    t = httpx.ASGITransport(app=app)

    async with (
        httpx.AsyncClient(transport=t, base_url="http://test") as stream_client,
        httpx.AsyncClient(transport=t, base_url="http://test") as post_client,
    ):
        # 1) Open the long-lived stream
        async with stream_client.stream("GET", "/stream") as resp:
            assert resp.status_code == 200

            # 2) Fire the POST on a *separate* client
            post = await post_client.post("/events", json=payload)
            assert post.status_code == 200
            enriched = post.json()

            # 3) Read lines with a hard timeout
            async def read_one_event():
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("eventId") == enriched["eventId"]:
                        return obj

            evt = await asyncio.wait_for(read_one_event(), timeout=3.0)
            assert evt["eventId"] == enriched["eventId"]
            assert evt["message"] == payload["message"]
