# app/services/events_service.py

from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.audit_event import AuditEvent
from app.services.cache_factory import get_cache
from app.config import CACHE_TTL_SECONDS

CACHE_PREFIX = "event:"

def _cache_key(event_id: UUID) -> str:
    return f"{CACHE_PREFIX}{str(event_id)}"

def cache_put_event(event_id: UUID, event_json: Dict[str, Any]) -> None:
    """
    Write-through helper to cache a freshly created or fetched event.
    """
    get_cache().set(_cache_key(event_id), event_json, ttl_seconds=CACHE_TTL_SECONDS or None)

def cache_delete_event(event_id: UUID) -> None:
    """
    Invalidate a specific event from cache (used by retention).
    """
    get_cache().delete(_cache_key(event_id))

def get_event_by_id(db: Session, event_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Read-through: try cache, fallback to DB, then populate cache.
    Returns the exact enriched JSON expected by the API.
    """
    cached = get_cache().get(_cache_key(event_id))
    if cached is not None:
        return cached

    table_name = getattr(AuditEvent, "__tablename__", "events")
    sql = f"""
        SELECT jsonb_strip_nulls(
            jsonb_build_object(
                'eventId', event_id::text,
                'ingestedAt', to_char(ingested_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
                'time', time,
                'logType', log_type,
                'reportingService', reporting_service::text,
                'logLevel', log_level,
                'activityType', activity_type,
                'identityType', identity_type,
                'user', "user",
                'action', action,
                'message', message,
                'ipAddress', ip_address,
                'errorCode', error_code,
                'metadata', metadata_,
                'account', account
            )
        ) AS event_json
        FROM {table_name}
        WHERE event_id = :id
        LIMIT 1
    """
    row = db.execute(text(sql), {"id": str(event_id)}).mappings().first()
    if row is None:
        return None

    event_json = dict(row["event_json"])
    cache_put_event(event_id, event_json)
    return event_json
