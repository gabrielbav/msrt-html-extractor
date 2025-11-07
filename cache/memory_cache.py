"""In-memory cache implementation."""

from typing import Any, Optional, Dict, Set
from collections import OrderedDict
from cache.cache_manager import CacheManager
from exceptions import CacheError


class MemoryCache(CacheManager):
    """In-memory cache with namespace support and size limits."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of items per namespace
        """
        self.max_size = max_size
        self._caches: Dict[str, OrderedDict] = {}
        
        # Standard namespaces
        self._caches["files"] = OrderedDict()
        self._caches["metrics"] = OrderedDict()
        self._caches["attributes"] = OrderedDict()
        self._caches["facts"] = OrderedDict()
        self._caches["functions"] = OrderedDict()
        self._caches["tables"] = OrderedDict()
        self._caches["default"] = OrderedDict()
    
    def _get_cache(self, namespace: str) -> OrderedDict:
        """
        Get or create cache for namespace.
        
        Args:
            namespace: Cache namespace
            
        Returns:
            OrderedDict for the namespace
        """
        if namespace not in self._caches:
            self._caches[namespace] = OrderedDict()
        return self._caches[namespace]
    
    def _enforce_size_limit(self, namespace: str) -> None:
        """
        Enforce size limit for namespace (LRU eviction).
        
        Args:
            namespace: Cache namespace
        """
        cache = self._get_cache(namespace)
        while len(cache) > self.max_size:
            # Remove oldest item (first in OrderedDict)
            cache.popitem(last=False)
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            Cached value or None
        """
        try:
            cache = self._get_cache(namespace)
            if key in cache:
                # Move to end (mark as recently used)
                cache.move_to_end(key)
                return cache[key]
            return None
        except Exception as e:
            raise CacheError(f"Failed to get from cache: {e}", "get", key)
    
    def set(self, key: str, value: Any, namespace: str = "default") -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace
        """
        try:
            cache = self._get_cache(namespace)
            cache[key] = value
            cache.move_to_end(key)  # Mark as most recently used
            self._enforce_size_limit(namespace)
        except Exception as e:
            raise CacheError(f"Failed to set in cache: {e}", "set", key)
    
    def has(self, key: str, namespace: str = "default") -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            True if exists
        """
        cache = self._get_cache(namespace)
        return key in cache
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            True if deleted
        """
        try:
            cache = self._get_cache(namespace)
            if key in cache:
                del cache[key]
                return True
            return False
        except Exception as e:
            raise CacheError(f"Failed to delete from cache: {e}", "delete", key)
    
    def clear(self, namespace: Optional[str] = None) -> None:
        """
        Clear cache.
        
        Args:
            namespace: Specific namespace or None for all
        """
        try:
            if namespace is None:
                for cache in self._caches.values():
                    cache.clear()
            elif namespace in self._caches:
                self._caches[namespace].clear()
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}", "clear", None)
    
    def get_keys(self, namespace: Optional[str] = None) -> Set[str]:
        """
        Get all keys in cache.
        
        Args:
            namespace: Specific namespace or None for all
            
        Returns:
            Set of cache keys
        """
        if namespace is None:
            all_keys = set()
            for cache in self._caches.values():
                all_keys.update(cache.keys())
            return all_keys
        
        cache = self._get_cache(namespace)
        return set(cache.keys())
    
    def get_size(self, namespace: Optional[str] = None) -> int:
        """
        Get number of items in cache.
        
        Args:
            namespace: Specific namespace or None for total
            
        Returns:
            Number of items
        """
        if namespace is None:
            return sum(len(cache) for cache in self._caches.values())
        
        cache = self._get_cache(namespace)
        return len(cache)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with stats per namespace
        """
        return {
            namespace: len(cache)
            for namespace, cache in self._caches.items()
        }

