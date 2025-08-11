# tests/test_get_events.py

from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
from datetime import datetime, timezone
import time

client = TestClient(app)

def _new_payload(idx: int):
    # Create distinct events ordered by ingestion time
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "logType": "Login",
        "reportingService": str(uuid4()),
        "logLevel": "informational",
        "activityType": f"UserLogin_{idx}",
        "identityType": "User",
        "user": {"identityUuid": f"u-{idx}"},
        "action": "Access",
        "message": f"M{idx}",
        "account": {"accountId": "acme-1", "accountName": "Acme"}
    }

def test_get_events_in_ingestion_order_and_time_format():
    # Arrange: seed a few events to ensure deterministic ingestion order
    created = []
    for i in range(5):
        res = client.post("/events", json=_new_payload(i))
        assert res.status_code == 200
        created.append(res.json())
        time.sleep(0.01)  # keep ingestion ordering stable

    # Act
    res = client.get("/events")
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert len(body) >= len(created)

    # Assert: items are sorted by ingestedAt ASC
    ing_times = [e["ingestedAt"] for e in body]
    assert ing_times == sorted(ing_times)

    # Assert: last 5 contain the 5 we just created, in the same relative order
    created_ids = [e["eventId"] for e in created]
    body_ids = [e["eventId"] for e in body]
    # Filter the order as they appear in the body
    seen = [eid for eid in body_ids if eid in set(created_ids)]
    assert seen[: len(created_ids)] == created_ids

    # Assert: timestamps use 'Z' and are UTC
    for e in body:
        assert isinstance(e["ingestedAt"], str) and e["ingestedAt"].endswith("Z")