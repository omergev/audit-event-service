# tests/test_integrations.py

from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
from datetime import datetime, timezone

client = TestClient(app)

def _payload():
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "logType": "Login",
        "reportingService": str(uuid4()),
        "logLevel": "informational",
        "activityType": "UserLogin",
        "identityType": "User",
        "user": {"identityUuid": "u-xyz"},
        "action": "Access",
        "message": "M",
        "account": {"accountId": "acme-1", "accountName": "Acme"}
    }

def test_round_trip_post_then_get_exact_match():
    # Ensure POST -> GET returns exactly the same JSON (immutability)
    post_res = client.post("/events", json=_payload())
    assert post_res.status_code == 200
    created = post_res.json()

    get_res = client.get(f"/events/{created['eventId']}")
    assert get_res.status_code == 200
    fetched = get_res.json()

    assert fetched == created
