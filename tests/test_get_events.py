# tests/test_get_events.py

from fastapi.testclient import TestClient
import pytest
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

@pytest.mark.skip(reason="Get events endpoint not implemented yet")
def test_get_events_order_and_pagination_basic():
    # Seed a few events to ensure deterministic order by ingestedAt
    created_ids = []
    for i in range(5):
        res = client.post("/events", json=_new_payload(i))
        assert res.status_code == 200
        created_ids.append(res.json()["eventId"])
        # Small sleep to preserve ingestion ordering if needed
        time.sleep(0.01)

    # First page
    res1 = client.get("/events", params={"limit": 3})
    assert res1.status_code == 200
    body1 = res1.json()
    assert "items" in body1 and isinstance(body1["items"], list)
    assert len(body1["items"]) <= 3

    # Items must be ordered by ingestedAt ASC
    times1 = [e["ingestedAt"] for e in body1["items"]]
    assert times1 == sorted(times1)

    # If nextCursor exists, fetch next page
    next_cursor = body1.get("nextCursor")
    if next_cursor:
        res2 = client.get("/events", params={"cursor": next_cursor, "limit": 3})
        assert res2.status_code == 200
        body2 = res2.json()
        times2 = [e["ingestedAt"] for e in body2["items"]]
        assert times2 == sorted(times2)

        # No overlap between pages
        ids1 = {e["eventId"] for e in body1["items"]}
        ids2 = {e["eventId"] for e in body2["items"]}
        assert ids1.isdisjoint(ids2)
