# tests/test_get_event_by_id.py

from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
from datetime import datetime, timezone

client = TestClient(app)

def _new_payload():
    # Minimal valid payload for POST
    return {
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

def test_get_event_by_id_200_round_trip():
    # POST an event, then GET by eventId and compare exact JSON
    post_res = client.post("/events", json=_new_payload())
    assert post_res.status_code == 200
    created = post_res.json()

    get_res = client.get(f"/events/{created['eventId']}")
    assert get_res.status_code == 200
    fetched = get_res.json()

    # Must match exactly the POST response
    assert fetched == created

def test_get_event_by_id_404_when_not_exists():
    # Valid UUID v4 that does not exist should return 404
    nonexist = str(uuid4())
    res = client.get(f"/events/{nonexist}")
    assert res.status_code == 404

def test_get_event_by_id_422_when_invalid_uuid():
    # Not a valid UUID v4 should return 422 (Pydantic validation)
    res = client.get("/events/not-a-uuid")
    assert res.status_code == 422
