# routers/events.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from models.audit_event import AuditEvent
from schemas.audit_event import AuditEventCreate
from app.database import get_db  # Update the import path to match your project structure

router = APIRouter()


@router.post("/events")
def create_event(payload: AuditEventCreate, db: Session = Depends(get_db)):
    """
    Accepts a new audit event payload, validates it, enriches it with internal fields,
    and stores it immutably in the database.
    """

    # Generate new UUIDv4 for the event
    event_id = uuid4()

    # Get current UTC timestamp for ingestion
    ingested_at = datetime.utcnow()

    # Convert the Pydantic model to a dictionary
    data = payload.dict()

    # Unpack and pass all fields, plus enrichments, to the AuditEvent SQLAlchemy model
    event = AuditEvent(
        event_id=event_id,
        ingested_at=ingested_at,
        time=data.get("time"),
        log_type=data["logType"],
        reporting_service=data["reportingService"],
        log_level=data["logLevel"],
        activity_type=data["activityType"],
        identity_type=data["identityType"],
        user=data["user"],
        action=data["action"],
        message=data["message"],
        ip_address=str(data["ipAddress"]) if data.get("ipAddress") else None,
        error_code=data.get("errorCode"),
        metadata=data.get("metadata"),
        account=data["account"]
    )

    # Save the event to the database
    db.add(event)
    db.commit()

    # Optional: refresh to load generated fields (if needed)
    db.refresh(event)

    # Return full event as response
    return {
        "eventId": str(event.event_id),
        "ingestedAt": event.ingested_at.isoformat(),
        **data
    }
