from collections import OrderedDict
from threading import RLock
from typing import Optional, Any, Dict
import time

class LRUCacheImpl:
    """
    Thread-safe LRU cache with optional per-entry TTL.
    Values are stored as shallow copies (dict) to avoid accidental mutation.
    """
    def __init__(self, capacity: int = 10_000):
        self.capacity = max(1, capacity)
        self._data: "OrderedDict[str, tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at and expires_at < now:
                # Expired: evict and miss
                self._data.pop(key, None)
                return None
            # Move to MRU
            self._data.pop(key)
            self._data[key] = (expires_at, dict(value))
            return dict(value)

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else 0.0
        with self._lock:
            if key in self._data:
                self._data.pop(key)
            elif len(self._data) >= self.capacity:
                self._data.popitem(last=False)  # Evict LRU
            self._data[key] = (expires_at, dict(value))

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)
