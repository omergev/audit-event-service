# tests/test_post_events.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4
from datetime import datetime, timezone

client = TestClient(app)

# Example valid event
valid_event = {
    "time": datetime.now(timezone.utc).isoformat(),
    "logType": "Login",
    "reportingService": str(uuid4()),
    "logLevel": "informational",
    "activityType": "UserLogin",
    "identityType": "User",
    "user": {
        "identityUuid": str(uuid4()),
        "userEmail": "test@example.com",
        "userFullName": "John Doe"
    },
    "action": "Access",
    "message": "User logged in successfully",
    "ipAddress": "192.168.0.1",
    "errorCode": "AUTH_001",
    "metadata": {"sessionId": "abc123"},
    "account": {
        "accountId": "acc001",
        "accountName": "Test Account"
    }
}

def test_post_event_success():
    # Ensure valid payload passes schema and returns enriched fields
    response = client.post("/events", json=valid_event)
    assert response.status_code == 200
    data = response.json()
    assert "eventId" in data and isinstance(data["eventId"], str)
    assert "ingestedAt" in data and isinstance(data["ingestedAt"], str)
    assert data["logType"] == valid_event["logType"]

def test_post_event_missing_required_field():
    # Remove a required field to trigger schema validation error
    broken_event = dict(valid_event)
    del broken_event["logType"]
    response = client.post("/events", json=broken_event)
    assert response.status_code == 400
    assert "validationErrors" in response.json()

def test_post_event_invalid_ip():
    # Provide an invalid IP to trigger schema validation error
    broken_event = dict(valid_event)
    broken_event["ipAddress"] = "invalid-ip"
    response = client.post("/events", json=broken_event)
    assert response.status_code == 400
    assert "validationErrors" in response.json()
