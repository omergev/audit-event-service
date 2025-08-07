# routers/events.py


from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
import json
from jsonschema import Draft7Validator, FormatChecker

from app.models.audit_event import AuditEvent
from app.schemas.audit_event import AuditEventCreate
from app.database import get_db 

import os

router = APIRouter()

# Load and prepare schema once at import time
schema_path = os.path.join(os.path.dirname(__file__), '../../audit_log_schema.json')
with open(schema_path, 'r', encoding='utf-8') as f:
    audit_event_schema = json.load(f)

# Prepare the JSON schema validator and attach format checker
json_validator = Draft7Validator(audit_event_schema, format_checker=FormatChecker())

@router.post("/events")
async def create_event(request: Request, db: Session = Depends(get_db)):
    """
    Accepts a new audit event payload,
    validates it using the JSON schema,
    enriches it with eventId and ingestedAt,
    and stores it immutably in the database.
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

    # Step 6: Return enriched payload
    return {
        "eventId": str(event.event_id),
        "ingestedAt": event.ingested_at.isoformat(),
        **payload
    }
