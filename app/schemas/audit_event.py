# app/schemas/audit_event.py

from pydantic import BaseModel, Field, EmailStr, constr, IPvAnyAddress, field_serializer
from typing import Optional, Dict, Any, Literal
from uuid import UUID
from datetime import datetime, timezone


# Nested schema for the 'user' field
class UserInfo(BaseModel):
    identityUuid: str = Field(..., description="Unique identifier for the user.")
    userEmail: Optional[EmailStr] = Field(None, description="Email of the user.")
    userFullName: Optional[str] = Field(None, description="Full name of the user.")


# Nested schema for the 'account' field
class AccountInfo(BaseModel):
    accountId: str = Field(..., description="Identifier for the tenant.")
    accountName: str = Field(..., description="Name of the tenant.")


# Main schema for creating an audit event
class AuditEventCreate(BaseModel):
    time: Optional[datetime] = Field(None, description="The date and time the activity captured in UTC")

    logType: Literal["Login", "System", "Management"] = Field(..., description="Type of the log.")
    reportingService: UUID = Field(..., description="UUID of the service that reported the log")
    logLevel: Literal["informational", "warning", "error"] = Field(..., description="Original log level of the log event")

    activityType: constr(max_length=50) = Field(..., description="Short name describing the actual activity that was captured") # pyright: ignore[reportInvalidTypeForm]
    identityType: Literal["User", "Application", "API Key"] = Field(..., description="Type of entity performing the action")

    user: UserInfo = Field(..., description="User information.")
    action: Literal[
        "Access", "Approve", "Create", "Update", "Delete",
        "Deny", "Execute", "Notify", "Revoke", "Export"
    ] = Field(..., description="The specific action performed")

    message: constr(max_length=512) = Field(..., description="Full message including specific details such as failure reason") # pyright: ignore[reportInvalidTypeForm]

    ipAddress: Optional[IPvAnyAddress] = Field(None, description="IP address from where the action originated")
    errorCode: Optional[constr(max_length=128)] = Field(None, description="Internal code representing a specific error type") # pyright: ignore[reportInvalidTypeForm]
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional contextual information related to the event")

    account: AccountInfo = Field(..., description="The account/tenant that this activity is related to")

class AuditEventRead(BaseModel):
    """
    DTO for reading an audit event from the API.
    Notes:
    - Mirrors the enriched shape returned by POST/GET endpoints.
    - Uses UTC 'Z' formatting for timestamps.
    - Keeps extra fields if ever added (immutability at the API contract level).
    """
    eventId: str
    ingestedAt: datetime

    # Optional original occurrence time (as provided by the source system)
    time: Optional[datetime] = None

    # Core schema (same as create)
    logType: Literal["Login", "System", "Management"]
    reportingService: UUID
    logLevel: Literal["informational", "warning", "error"]
    activityType: constr(max_length=50)  # type: ignore[reportInvalidTypeForm]
    identityType: Literal["User", "Application", "API Key"]
    user: UserInfo
    action: Literal[
        "Access", "Approve", "Create", "Update", "Delete",
        "Deny", "Execute", "Notify", "Revoke", "Export"
    ]
    message: constr(max_length=512)  # type: ignore[reportInvalidTypeForm]
    ipAddress: Optional[str] = None
    errorCode: Optional[constr(max_length=128)] = None  # type: ignore[reportInvalidTypeForm]
    metadata: Optional[Dict[str, Any]] = None
    account: AccountInfo

    # Allow future-proofing without breaking clients:
    model_config = {"extra": "allow"}

    @field_serializer("ingestedAt")
    def _ser_ingested_at(self, v: datetime) -> str:
        # Ensure UTC and 'Z' suffix
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        v = v.astimezone(timezone.utc)
        # milliseconds are typically enough; can keep microseconds if desired
        iso = v.isoformat(timespec="milliseconds")
        return iso.replace("+00:00", "Z")

    @field_serializer("time")
    def _ser_time(self, v: Optional[datetime]) -> Optional[str]:
        # Same UTC 'Z' policy for the optional 'time' field
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        v = v.astimezone(timezone.utc)
        iso = v.isoformat(timespec="milliseconds")
        return iso.replace("+00:00", "Z")