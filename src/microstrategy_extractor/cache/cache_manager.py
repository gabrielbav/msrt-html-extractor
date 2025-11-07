"""Abstract cache manager interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Set


class CacheManager(ABC):
    """Abstract base class for cache implementations."""
    
    @abstractmethod
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace for isolation
            
        Returns:
            Cached value or None if not found
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, namespace: str = "default") -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace for isolation
        """
        pass
    
    @abstractmethod
    def has(self, key: str, namespace: str = "default") -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            True if key exists
        """
        pass
    
    @abstractmethod
    def delete(self, key: str, namespace: str = "default") -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            True if key was deleted, False if not found
        """
        pass
    
    @abstractmethod
    def clear(self, namespace: Optional[str] = None) -> None:
        """
        Clear cache.
        
        Args:
            namespace: Specific namespace to clear, or None to clear all
        """
        pass
    
    @abstractmethod
    def get_keys(self, namespace: Optional[str] = None) -> Set[str]:
        """
        Get all keys in cache.
        
        Args:
            namespace: Specific namespace, or None for all
            
        Returns:
            Set of cache keys
        """
        pass
    
    @abstractmethod
    def get_size(self, namespace: Optional[str] = None) -> int:
        """
        Get number of items in cache.
        
        Args:
            namespace: Specific namespace, or None for total
            
        Returns:
            Number of cached items
        """
        pass
    
    def get_or_compute(self, key: str, compute_fn: callable, 
                      namespace: str = "default") -> Any:
        """
        Get value from cache or compute and cache it.
        
        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            namespace: Cache namespace
            
        Returns:
            Cached or computed value
        """
        value = self.get(key, namespace)
        if value is None:
            value = compute_fn()
            if value is not None:
                self.set(key, value, namespace)
        return value

