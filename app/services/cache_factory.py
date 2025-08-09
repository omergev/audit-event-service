from typing import Any, Dict, Optional
from .cache import Cache
from .cache_backends import InProcessLRUCache
from app.config import CACHE_BACKEND, CACHE_CAPACITY

_cache_singleton: Optional[Cache] = None

def get_cache() -> Cache:
    """
    Returns a process-wide cache instance based on configuration:
      - "none"   -> no-op backend (always misses)
      - "memory" -> in-process LRU (fastest for single instance)
      - "redis"  -> shared cache (to be enabled later)

    Rationale:
      - Keeps application logic unaware of the underlying cache technology.
      - Allows flipping backends via environment variables.
    """
    global _cache_singleton
    if _cache_singleton is not None:
        return _cache_singleton

    if CACHE_BACKEND == "memory":
        _cache_singleton = InProcessLRUCache(capacity=CACHE_CAPACITY)
    elif CACHE_BACKEND == "none":
        _cache_singleton = _NoCache()
    elif CACHE_BACKEND == "redis":
        # when added: _cache_singleton = RedisCache(REDIS_URL)
        _cache_singleton = _NoCache()
    else:
        _cache_singleton = InProcessLRUCache(capacity=CACHE_CAPACITY)

    return _cache_singleton


class _NoCache(Cache):
    """No-op cache used when caching is disabled or backend is not configured."""
    def get(self, key: str): return None
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int | None = None): pass
    def delete(self, key: str): pass

