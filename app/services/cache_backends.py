from typing import Optional, Any, Dict
from .cache import Cache
from .lru_cache import LRUCacheImpl

class InProcessLRUCache(Cache):
    """In-process LRU cache backend."""
    def __init__(self, capacity: int):
        self._lru = LRUCacheImpl(capacity=capacity)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._lru.get(key)

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        self._lru.set(key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        self._lru.delete(key)
