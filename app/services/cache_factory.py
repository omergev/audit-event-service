from typing import Optional
from .cache import Cache
from .cache_backends import InProcessLRUCache
from app.config import CACHE_BACKEND, CACHE_CAPACITY

_cache_singleton: Optional[Cache] = None

def get_cache() -> Cache:
    """
    Return a process-wide cache instance according to configuration.
    Currently supports "memory". "redis" can be added later without changing callers.
    """
    global _cache_singleton
    if _cache_singleton is not None:
        return _cache_singleton

    if CACHE_BACKEND == "none":
        _cache_singleton = _NoCache()
    elif CACHE_BACKEND == "memory":
        _cache_singleton = InProcessLRUCache(capacity=CACHE_CAPACITY)
    elif CACHE_BACKEND == "redis":
        # Placeholder: will be implemented when enabling Redis
        _cache_singleton = _NoCache()
    else:
        _cache_singleton = InProcessLRUCache(capacity=CACHE_CAPACITY)

    return _cache_singleton


class _NoCache(Cache):
    """No-op cache used when caching is disabled or backend is not configured."""
    def get(self, key: str):
        return None
    def set(self, key: str, value, ttl_seconds=None):
        pass
    def delete(self, key: str):
        pass
