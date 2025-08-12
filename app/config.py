# app/config.py
import os

DATABASE_URL = os.getenv("DATABASE_URL") or ("postgresql+psycopg://postgres:postgres@localhost:5432/audit_logs")

# Cache configuration:
#   CACHE_BACKEND: "none" | "memory" | "redis"
#   CACHE_CAPACITY: max number of items (memory backend only)
#   CACHE_TTL_SECONDS: per-entry TTL; 0 means no expiration
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "memory").lower()
CACHE_CAPACITY = int(os.getenv("CACHE_CAPACITY", "10000"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "0"))  # 0 = no TTL

# Read once at process start; change via environment variables.
RETENTION_INTERVAL_SECONDS = int(os.getenv("RETENTION_INTERVAL_SECONDS", "86400")) # default 24 hours
RETENTION_YEARS = int(os.getenv("RETENTION_YEARS", "3")) 
RETENTION_DELETE_LIMIT = int(os.getenv("RETENTION_DELETE_LIMIT", "1000"))  # per-cycle batch size

# Redis (for future flip)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_CHANNEL = os.getenv("STREAM_CHANNEL", "audit-events")
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "15"))
