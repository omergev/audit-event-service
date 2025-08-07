# models/audit_event.py

import uuid
from sqlalchemy import Column, String, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    # Primary key for the event, generated on ingestion (Primary Key count as nullable=True)
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Timestamp when the event was ingested into the system
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Optional original timestamp when the event occurred (according to the source system)
    time = Column(DateTime, nullable=True)

    # Type of the log (Login, System, Management)
    log_type = Column(Enum("Login", "System", "Management", name="logtype_enum"), nullable=False)

    # UUID of the service that reported this event
    reporting_service = Column(UUID(as_uuid=True), nullable=False)

    # Log level (informational, warning, error)
    log_level = Column(Enum("informational", "warning", "error", name="loglevel_enum"), nullable=False)

    # Activity type name (short description of the action performed)
    activity_type = Column(String(50), nullable=False)

    # The identity type (User, Application, API Key)
    identity_type = Column(Enum("User", "Application", "API Key", name="identitytype_enum"), nullable=False)

    # User details as a JSON object (must include identityUuid)
    user = Column(JSON, nullable=False)

    # The action performed (Access, Approve, Create, Update, Delete, etc.)
    action = Column(Enum(
        "Access", "Approve", "Create", "Update", "Delete", "Deny",
        "Execute", "Notify", "Revoke", "Export", name="action_enum"
    ), nullable=False)

    # Human-readable message describing the event
    message = Column(String(512), nullable=False)

    # Optional IP address (IPv4 or IPv6)
    ip_address = Column(String, nullable=True)

    # Optional internal error code
    error_code = Column(String(128), nullable=True)

    # Optional flexible metadata (stored as JSONB)
    metadata_ = Column(JSONB, nullable=True)

    # Account details as a JSON object (must include accountId, accountName)
    account = Column(JSON, nullable=False)
