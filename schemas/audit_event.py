# schemas/audit_event.py

from pydantic import BaseModel, Field, EmailStr, constr, IPvAnyAddress
from typing import Optional, Dict, Any, Literal
from uuid import UUID
from datetime import datetime


# Nested schema for the 'user' field
class UserInfo(BaseModel):
    identityUuid: str = Field(required=True, description="Unique identifier for the user.")
    userEmail: Optional[EmailStr] = Field(None, description="Email of the user.")
    userFullName: Optional[str] = Field(None, description="Full name of the user.")


# Nested schema for the 'account' field
class AccountInfo(BaseModel):
    accountId: str = Field(required=True, description="Identifier for the tenant.")
    accountName: str = Field(required=True, description="Name of the tenant.")


# Main schema for creating an audit event
class AuditEventCreate(BaseModel):
    time: Optional[datetime] = Field(None, description="The date and time the activity captured in UTC")

    logType: Literal["Login", "System", "Management"] = Field(required=True, description="Type of the log.")
    reportingService: UUID = Field(required=True, description="UUID of the service that reported the log")
    logLevel: Literal["informational", "warning", "error"] = Field(required=True, description="Original log level of the log event")

    activityType: constr(max_length=50) = Field(required=True, description="Short name describing the actual activity that was captured") # pyright: ignore[reportInvalidTypeForm]
    identityType: Literal["User", "Application", "API Key"] = Field(required=True, description="Type of entity performing the action")

    user: UserInfo = Field(required=True, description="User information.")
    action: Literal[
        "Access", "Approve", "Create", "Update", "Delete",
        "Deny", "Execute", "Notify", "Revoke", "Export"
    ] = Field(required=True, description="The specific action performed")

    message: constr(max_length=512) = Field(required=True, description="Full message including specific details such as failure reason") # pyright: ignore[reportInvalidTypeForm]

    ipAddress: Optional[IPvAnyAddress] = Field(None, description="IP address from where the action originated")
    errorCode: Optional[constr(max_length=128)] = Field(None, description="Internal code representing a specific error type") # pyright: ignore[reportInvalidTypeForm]
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional contextual information related to the event")

    account: AccountInfo = Field(required=True, description="The account/tenant that this activity is related to")
