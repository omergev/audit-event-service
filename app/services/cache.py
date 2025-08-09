from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

class Cache(ABC):
    """Minimal cache interface to enable swapping backends (memory, Redis, none) without changing callers."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...
