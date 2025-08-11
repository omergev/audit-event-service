# tests/test_events_and_retention.py
import time
import uuid
from sqlalchemy import text
from app.database import engine
from app.main import retention_service  # reuse the running service object
from app.database import engine

def _post_event(client, payload: dict) -> str:
    """Post one event and return eventId."""
    resp = client.post("/events", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "eventId" in data
    return data["eventId"]

def test_events_post_and_retention_delete(client, db_conn):
    # 1) Post three valid events and capture their IDs
    e1 = _post_event(client, {
        "time": "2025-08-10T12:00:00Z",
        "logType": "Login",
        "reportingService": "11111111-1111-1111-1111-111111111111",
        "logLevel": "informational",
        "activityType": "user-login",
        "identityType": "User",
        "action": "Access",
        "message": "User logged in successfully",
        "user": {"identityUuid": "user-1", "userEmail": "u1@example.com", "userFullName": "User One"},
        "account": {"accountId": "acct-1", "accountName": "Tenant One"},
        "metadata": {"ip": "127.0.0.1"}
    })
    e2 = _post_event(client, {
        "time": "2025-08-10T12:05:00Z",
        "logType": "System",
        "reportingService": "22222222-2222-2222-2222-222222222222",
        "logLevel": "warning",
        "activityType": "cache-warmup",
        "identityType": "Application",
        "action": "Execute",
        "message": "Cache warmup completed",
        "user": {"identityUuid": "svc-1"},
        "account": {"accountId": "acct-1", "accountName": "Tenant One"}
    })
    e3 = _post_event(client, {
        "time": "2025-08-10T12:10:00Z",
        "logType": "Management",
        "reportingService": "33333333-3333-3333-3333-333333333333",
        "logLevel": "error",
        "activityType": "record-edit",
        "identityType": "User",
        "action": "Update",
        "message": "Failed to update record",
        "user": {"identityUuid": "user-2", "userEmail": "u2@example.com"},
        "account": {"accountId": "acct-2", "accountName": "Tenant Two"},
        "errorCode": "E42"
    })

    # 2) Age two of them far beyond retention (set to a very old date) in a committed txn
    #    to guarantee they fall under the cutoff and are visible to another connection.
    with engine.begin() as conn:
        res = conn.execute(
            text("""
                UPDATE audit_events
                SET ingested_at = TIMESTAMP '2000-01-01 00:00:00+00'
                WHERE event_id IN (:e1, :e2)
            """),
            {"e1": e1, "e2": e2},
        )
        # Sanity check: ensure we actually aged 2 rows
        assert (res.rowcount or 0) == 2

        # Extra sanity check: confirm both rows are older than cutoff
        cnt = conn.execute(
            text("""
                SELECT COUNT(*) FROM audit_events
                WHERE event_id IN (:e1, :e2)
                  AND ingested_at < (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 years'
            """),
            {"e1": e1, "e2": e2},
        ).scalar_one()
        assert cnt == 2

    # 3) Run one deletion batch directly (no need to wait for the background loop)
    deleted = retention_service._delete_one_batch(limit=1000)  # internal method, OK for tests
    assert deleted == 2

    # 4) First, assert at the DB level that the two old rows are gone.
    with engine.begin() as conn:
        cnt_after = conn.execute(
            text("""
                SELECT COUNT(*) FROM audit_events
                WHERE event_id IN (:e1, :e2)
            """),
            {"e1": e1, "e2": e2},
        ).scalar_one()
        assert cnt_after == 0, "Rows still present in DB after deletion"

    # 5) Then verify API behavior (allow a tiny delay for any caching/pooling edge cases).
    time.sleep(0.05)  # tiny delay to avoid stale reads from pools/caches
    r1 = client.get(f"/events/{e1}")
    r2 = client.get(f"/events/{e2}")
    r3 = client.get(f"/events/{e3}")
    assert r1.status_code == 404
    assert r2.status_code == 404
    assert r3.status_code == 200

    # 5) Cleanup the remaining fresh event to keep DB tidy for other tests
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM audit_events WHERE event_id = :eid"), {"eid": e3})
