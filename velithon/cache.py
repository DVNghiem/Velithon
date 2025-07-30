"""Simplified caching utilities for Velithon framework.

This module provides simplified caching functionality with minimal overhead
and reduced complexity compared to the previous implementation.
"""

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


# Simplified cache size constants
class CacheConfig:
    """Simplified cache size configuration."""

    DEFAULT_CACHE_SIZE = 512  # Reduced from 1000
    LARGE_CACHE_SIZE = 1024  # Reduced from 5000
    SMALL_CACHE_SIZE = 128  # Reduced from 256
    RESPONSE_CACHE_SIZE = 50  # Reduced from 100

    @classmethod
    def get_cache_size(cls, cache_type: str) -> int:
        """Get appropriate cache size for different cache types."""
        size_map = {
            'route': cls.DEFAULT_CACHE_SIZE,
            'middleware': cls.LARGE_CACHE_SIZE,
            'signature': cls.SMALL_CACHE_SIZE,
            'response': cls.RESPONSE_CACHE_SIZE,
            'default': cls.DEFAULT_CACHE_SIZE,
        }
        return size_map.get(cache_type, cls.DEFAULT_CACHE_SIZE)


def create_lru_cache(
    max_size: int | None = None, cache_type: str = 'default'
) -> Callable:
    """Create a standardized LRU cache decorator with simplified sizing.

    Args:
        max_size: Override for cache size, uses standard sizes if None
        cache_type: Type of cache for automatic size selection

    Returns:
        LRU cache decorator with standard configuration

    """
    if max_size is None:
        max_size = CacheConfig.get_cache_size(cache_type)

    return lru_cache(maxsize=max_size)


class SimpleCacheManager:
    """Simplified cache manager with minimal overhead."""

    def __init__(self):
        """Initialize the simplified cache manager."""
        self._lru_caches: dict[str, Any] = {}

    def register_lru_cache(self, name: str, cache_func: Any) -> None:
        """Register an lru_cache function for management."""
        self._lru_caches[name] = cache_func
        logger.debug(f'Registered LRU cache function: {name}')

    def clear_all_caches(self) -> None:
        """Clear all registered caches."""
        cleared_count = 0

        for name, cache_func in self._lru_caches.items():
            if hasattr(cache_func, 'cache_clear'):
                cache_func.cache_clear()
                cleared_count += 1
                logger.debug(f'Cleared LRU cache: {name}')

        logger.info(f'Cleared {cleared_count} caches')


# Global cache manager instance
cache_manager = SimpleCacheManager()


# Convenience functions for common cache types
def route_cache(maxsize: int | None = None) -> Callable:
    """Create a route-specific cache."""
    return create_lru_cache(maxsize, 'route')


def middleware_cache(maxsize: int | None = None) -> Callable:
    """Create a middleware-specific cache."""
    return create_lru_cache(maxsize, 'middleware')


def signature_cache(maxsize: int | None = None) -> Callable:
    """Create a signature-specific cache."""
    return create_lru_cache(maxsize, 'signature')


def parser_cache(maxsize: int | None = None) -> Callable:
    """Create a parser-specific cache."""
    return create_lru_cache(maxsize, 'signature')  # Use signature size


def response_cache(maxsize: int | None = None) -> Callable:
    """Create a response-specific cache."""
    return create_lru_cache(maxsize, 'response')
