# app/routers/events.py

import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
import json
from jsonschema import Draft7Validator, FormatChecker

from app.models.audit_event import AuditEvent
from app.schemas.audit_event import AuditEventCreate, AuditEventRead
from app.services.events_service import list_events as svc_list_events
from app.database import get_db 
from app.services.events_service import cache_put_event, get_event_by_id as svc_get_event_by_id
from app.services.stream_bus import get_stream_bus


# Use a fixed prefix so routes live under /events
router = APIRouter(prefix="/events", tags=["events"])

# Load and prepare schema once at import time
schema_path = Path(__file__).resolve().parents[2] / "audit_log_schema.json"
with schema_path.open("r", encoding="utf-8") as f:
    audit_event_schema = json.load(f)

# Prepare the JSON schema validator and attach format checker
json_validator = Draft7Validator(audit_event_schema, format_checker=FormatChecker())

@router.post("")
async def create_event(request: Request, db: Session = Depends(get_db)):
    """
    POST /events
    Validates the incoming audit event against the JSON schema, enriches it
    with eventId (UUID v4) and ingestedAt (UTC, ISO8601 'Z'), persists to the DB,
    and returns the immutable enriched JSON object.

    Status codes:
      - 200: Valid, persisted, returns the enriched event
      - 400: JSON schema validation failed (validationErrors list)
      - 422: Invalid request body (e.g., not JSON) handled by FastAPI

    Design notes:
      - Validation runs BEFORE DB I/O to avoid unnecessary round-trips.
      - We return the exact immutable shape used across the API contract.
      - eventId is always UUID v4; ingestedAt uses ISO8601 with 'Z' for UTC.
    """

    # Step 1: Parse raw JSON body
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    
    # Step 2: Validate using JSON Schema
    # "If invalid, responds with 400 Bad Request and a JSON list of validation errors."
    validation_errors = sorted(json_validator.iter_errors(payload), key=lambda e: e.path)
    if validation_errors:
        return JSONResponse(
            status_code=400,
            content={"validationErrors": [e.message for e in validation_errors]},
        )
    
    # Step 3: Convert to Pydantic model (still useful for typing/consistency)
    event_data = AuditEventCreate(**payload)

    # Step 4: Enrich with internal fields
    event_id = uuid4() # Generate new UUIDv4 for the event
    ingested_at = datetime.now(timezone.utc) # Current UTC time for when the event is ingested

    event = AuditEvent(
        event_id=event_id,
        ingested_at=ingested_at,
        time=event_data.time,
        log_type=event_data.logType,
        reporting_service=event_data.reportingService,
        log_level=event_data.logLevel,
        activity_type=event_data.activityType,
        identity_type=event_data.identityType,
        user=event_data.user.model_dump(),
        action=event_data.action,
        message=event_data.message,
        ip_address=str(event_data.ipAddress) if event_data.ipAddress else None,
        error_code=event_data.errorCode,
        metadata_=event_data.metadata,
        account=event_data.account.model_dump(),
    )

    # Step 5: Save to database
    db.add(event)
    db.commit()
    db.refresh(event)  # Load auto-generated fields (not neccesary now but good for extanding more fields)

    # Ensure ingestedAt is emitted in UTC ISO8601 with 'Z'
    ing = event.ingested_at
    if ing.tzinfo is None:
        ing = ing.replace(tzinfo=timezone.utc)
    else:
        ing = ing.astimezone(timezone.utc)
    ingested_at_iso = ing.isoformat(timespec="microseconds").replace("+00:00", "Z")

    # Step 6: Prepare the response
    response = {
        "eventId": str(event.event_id),
        "ingestedAt": ingested_at_iso,
        **payload
    }
    cache_put_event(event.event_id, response)

    # Step 7: Publish to stream bus (if configured)
    try:
        bus = get_stream_bus()
        await bus.publish(response)  # publish only after successful commit
        logging.getLogger(__name__).debug("published to stream_bus: %s", response.get("eventId"))
    except Exception as ex:
        logging.getLogger(__name__).exception("Failed to publish event to stream: %s", ex)
    
    return response


@router.get("/{event_id}")
def get_event_by_id(event_id: UUID4, db: Session = Depends(get_db)):
    """
    GET /events/{eventId}
    Returns the exact immutable event JSON previously stored via POST /events.

    Path params:
      - eventId: UUID v4 (validated by Pydantic's UUID4)

    Status codes:
      - 200: Found
      - 404: Not found
      - 422: eventId is not a UUID v4

    Design notes:
      - Read-through cache: O(1) average for repeated reads.
      - DB assembles the JSON to keep the API contract stable and minimize Python marshalling.
    """
    event = svc_get_event_by_id(db, event_id)
    if event is None:
        # Not found -> return 404 with a clear message
        raise HTTPException(status_code=404, detail="Event not found")

    return event

@router.get("", response_model=List[AuditEventRead])
def list_all_events(db: Session = Depends(get_db)):
    """
    GET /events
    Returns all stored audit events in the order they were ingested.
    Notes:
    - Business-logic free: delegates to service layer.
    - Events are immutable and returned as stored/enriched.
    - Timestamps are serialized to UTC with 'Z' by DTO.
    """
    return svc_list_events(db)