# tests/test_stream.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
from datetime import datetime, timezone

client = TestClient(app)

@pytest.mark.skip(reason="SSE /stream not implemented yet")
def test_stream_receives_new_event_after_post():
    # This test is a placeholder: when /stream is implemented, convert to real streaming test.
    with client.stream("GET", "/stream") as s:
        # POST a new event
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "logType": "Login",
            "reportingService": str(uuid4()),
            "logLevel": "informational",
            "activityType": "UserLogin",
            "identityType": "User",
            "user": {"identityUuid": "u-1"},
            "action": "Access",
            "message": "M",
            "account": {"accountId": "acme-1", "accountName": "Acme"}
        }
        post_res = client.post("/events", json=payload)
        assert post_res.status_code == 200

        # Read one chunk (implementation-specific once SSE is ready)
        chunk = next(s.iter_lines(), None)
        assert chunk is not None
