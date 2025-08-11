# app/config.py
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "audit_logs")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Cache configuration:
#   CACHE_BACKEND: "none" | "memory" | "redis"
#   CACHE_CAPACITY: max number of items (memory backend only)
#   CACHE_TTL_SECONDS: per-entry TTL; 0 means no expiration
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "memory").lower()
CACHE_CAPACITY = int(os.getenv("CACHE_CAPACITY", "10000"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "0"))  # 0 = no TTL

RETENTION_INTERVAL_SECONDS = int(os.getenv("RETENTION_INTERVAL_SECONDS", "5"))  
RETENTION_YEARS = int(os.getenv("RETENTION_YEARS", "3"))

# Redis (for future flip)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_CHANNEL = os.getenv("STREAM_CHANNEL", "audit-events")
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "15"))
