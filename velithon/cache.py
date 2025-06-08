import logging
from functools import lru_cache
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)


# Cache size constants - centralized configuration
class CacheConfig:
    """Centralized cache size configuration for the framework."""

    # Main cache sizes
    DEFAULT_CACHE_SIZE = 1000
    LARGE_CACHE_SIZE = 5000
    MEDIUM_CACHE_SIZE = 1024
    SMALL_CACHE_SIZE = 256
    TINY_CACHE_SIZE = 128
    RESPONSE_CACHE_SIZE = 100

    # Cache eviction policies
    DEFAULT_EVICTION_RATIO = 0.2  # Remove 20% when cache is full

    @classmethod
    def get_cache_size(cls, cache_type: str) -> int:
        """Get appropriate cache size for different cache types."""
        size_map = {
            "route": cls.DEFAULT_CACHE_SIZE,
            "middleware": cls.LARGE_CACHE_SIZE,
            "signature": cls.SMALL_CACHE_SIZE,
            "method_lookup": cls.TINY_CACHE_SIZE,
            "parser": cls.MEDIUM_CACHE_SIZE,
            "response": cls.RESPONSE_CACHE_SIZE,
            "message": cls.DEFAULT_CACHE_SIZE,
            "default": cls.DEFAULT_CACHE_SIZE,
        }
        return size_map.get(cache_type, cls.DEFAULT_CACHE_SIZE)


K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """
    A simple LRU cache implementation with consistent eviction policy.

    This provides a unified cache interface across the framework with
    standardized size limits and eviction behavior.
    """

    def __init__(
        self, max_size: int, eviction_ratio: float = CacheConfig.DEFAULT_EVICTION_RATIO
    ):
        self.max_size = max_size
        self.eviction_ratio = eviction_ratio
        self.cache: Dict[K, V] = {}
        self.access_order: list[K] = []
        self.hits = 0
        self.misses = 0

    def get(self, key: K) -> Optional[V]:
        """Get value from cache, updating access order."""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            self.hits += 1
            return self.cache[key]

        self.misses += 1
        return None

    def put(self, key: K, value: V) -> None:
        """Put value in cache, evicting old entries if necessary."""
        if key in self.cache:
            # Update existing entry
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
            return

        # Check if we need to evict
        if len(self.cache) >= self.max_size:
            self._evict()

        self.cache[key] = value
        self.access_order.append(key)

    def _evict(self) -> None:
        """Evict least recently used entries."""
        num_to_evict = max(1, int(self.max_size * self.eviction_ratio))

        for _ in range(num_to_evict):
            if self.access_order:
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_order.clear()

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "load_factor": len(self.cache) / self.max_size,
        }


def create_lru_cache(
    max_size: Optional[int] = None, cache_type: str = "default"
) -> Callable:
    """
    Create a standardized LRU cache decorator with consistent sizing.

    Args:
        max_size: Override for cache size, uses standard sizes if None
        cache_type: Type of cache for automatic size selection

    Returns:
        LRU cache decorator with standard configuration
    """
    if max_size is None:
        max_size = CacheConfig.get_cache_size(cache_type)

    return lru_cache(maxsize=max_size)


class CacheManager:
    """
    Global cache manager for framework-wide cache coordination.

    Provides centralized cache statistics, cleanup, and management.
    """

    def __init__(self):
        self._caches: Dict[str, LRUCache] = {}
        self._lru_caches: Dict[str, Any] = {}  # Track lru_cache instances

    def register_cache(self, name: str, cache: LRUCache) -> None:
        """Register a cache instance for management."""
        self._caches[name] = cache
        logger.debug(f"Registered cache: {name} (max_size: {cache.max_size})")

    def register_lru_cache(self, name: str, cache_func: Any) -> None:
        """Register an lru_cache function for management."""
        self._lru_caches[name] = cache_func
        logger.debug(f"Registered LRU cache function: {name}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics for all registered caches."""
        stats = {}

        # Custom LRU caches
        for name, cache in self._caches.items():
            stats[name] = cache.stats()

        # Standard lru_cache functions
        for name, cache_func in self._lru_caches.items():
            if hasattr(cache_func, "cache_info"):
                info = cache_func.cache_info()
                stats[name] = {
                    "hits": info.hits,
                    "misses": info.misses,
                    "current_size": info.currsize,
                    "max_size": info.maxsize,
                    "hit_rate": info.hits / (info.hits + info.misses)
                    if (info.hits + info.misses) > 0
                    else 0,
                }

        return stats

    def clear_all_caches(self) -> None:
        """Clear all registered caches."""
        cleared_count = 0

        # Clear custom caches
        for name, cache in self._caches.items():
            cache.clear()
            cleared_count += 1
            logger.debug(f"Cleared cache: {name}")

        # Clear lru_cache functions
        for name, cache_func in self._lru_caches.items():
            if hasattr(cache_func, "cache_clear"):
                cache_func.cache_clear()
                cleared_count += 1
                logger.debug(f"Cleared LRU cache: {name}")

        logger.info(f"Cleared {cleared_count} caches")

    def get_total_memory_usage(self) -> Dict[str, int]:
        """Estimate total memory usage of all caches."""
        # This is a rough estimate - actual memory usage will vary
        usage = {}
        total_entries = 0

        for name, cache in self._caches.items():
            entries = len(cache.cache)
            usage[name] = entries
            total_entries += entries

        for name, cache_func in self._lru_caches.items():
            if hasattr(cache_func, "cache_info"):
                entries = cache_func.cache_info().currsize
                usage[name] = entries
                total_entries += entries

        usage["total_entries"] = total_entries
        return usage


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions for common cache types
def route_cache(maxsize: Optional[int] = None) -> Callable:
    """Create a route-specific cache."""
    return create_lru_cache(maxsize, "route")


def middleware_cache(maxsize: Optional[int] = None) -> Callable:
    """Create a middleware-specific cache."""
    return create_lru_cache(maxsize, "middleware")


def signature_cache(maxsize: Optional[int] = None) -> Callable:
    """Create a signature-specific cache."""
    return create_lru_cache(maxsize, "signature")


def parser_cache(maxsize: Optional[int] = None) -> Callable:
    """Create a parser-specific cache."""
    return create_lru_cache(maxsize, "parser")


def response_cache(maxsize: Optional[int] = None) -> Callable:
    """Create a response-specific cache."""
    return create_lru_cache(maxsize, "response")


# Standard cache size constants for backward compatibility
DEFAULT_CACHE_SIZE = CacheConfig.DEFAULT_CACHE_SIZE
LARGE_CACHE_SIZE = CacheConfig.LARGE_CACHE_SIZE
MEDIUM_CACHE_SIZE = CacheConfig.MEDIUM_CACHE_SIZE
SMALL_CACHE_SIZE = CacheConfig.SMALL_CACHE_SIZE
TINY_CACHE_SIZE = CacheConfig.TINY_CACHE_SIZE
RESPONSE_CACHE_SIZE = CacheConfig.RESPONSE_CACHE_SIZE
