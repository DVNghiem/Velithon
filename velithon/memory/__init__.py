"""Memory-optimized response caching and management."""

from __future__ import annotations

import gc
import threading
from typing import Any

from velithon._velithon import (
    StringInterner,
    MemoryAwareLRUCache,
    MemoryStats
)

class MemoryOptimizedResponseCache:
    """High-performance response cache with memory optimization."""
    
    def __init__(
        self,
        max_entries: int = 1000,
        max_memory_mb: int = 100,
        enable_string_interning: bool = True,
        gc_threshold: int = 100,
    ) -> None:
        """Initialize memory-optimized response cache."""
        self._cache = MemoryAwareLRUCache(max_entries, max_memory_mb)
        self._string_interner = StringInterner() if enable_string_interning else None
        self._gc_threshold = gc_threshold
        self._request_count = 0
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Any | None:
        """Get cached response."""
        with self._lock:
            # Intern the key string if enabled
            if self._string_interner:
                key = self._string_interner.intern(key)
            
            return self._cache.get(key)
    
    def put(self, key: str, value: Any) -> bool:
        """Cache a response value."""
        with self._lock:
            try:
                # Intern the key string if enabled
                if self._string_interner:
                    key = self._string_interner.intern(key)
                
                self._cache.put(key, value)
                
                # Periodic cleanup
                self._request_count += 1
                if self._request_count % self._gc_threshold == 0:
                    self._cleanup()
                
                return True
            except Exception:
                return False
    
    def _cleanup(self) -> None:
        """Perform cleanup operations."""
        # Cleanup string interner
        if self._string_interner:
            cleaned = self._string_interner.cleanup()
            if cleaned > 100:  # Only force GC if significant cleanup
                gc.collect()
    
    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {}
        
        # Cache stats
        cache_stats = self._cache.get_stats()
        stats.update({f"cache_{k}": v for k, v in cache_stats.items()})
        
        # String interner stats
        if self._string_interner:
            interner_stats = self._string_interner.get_stats()
            stats.update({f"interner_{k}": v for k, v in interner_stats.items()})
        
        # System stats
        stats["request_count"] = self._request_count
        stats["gc_threshold"] = self._gc_threshold
        
        return stats
    
    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
            if self._string_interner:
                # Force cleanup of string interner
                self._string_interner.cleanup()
            self._request_count = 0


class MemoryAwareRequestHandler:
    """Request handler with memory optimization."""
    
    def __init__(
        self,
        enable_response_caching: bool = True,
        cache_max_entries: int = 1000,
        cache_max_memory_mb: int = 100,
    ) -> None:
        """Initialize memory-aware request handler."""
        self._response_cache = None
        
        if enable_response_caching:
            self._response_cache = MemoryOptimizedResponseCache(
                max_entries=cache_max_entries,
                max_memory_mb=cache_max_memory_mb,
            )
    
    def get_cached_response(self, cache_key: str) -> Any | None:
        """Get a cached response."""
        if self._response_cache:
            return self._response_cache.get(cache_key)
        return None
    
    def cache_response(self, cache_key: str, response: Any) -> bool:
        """Cache a response."""
        if self._response_cache:
            return self._response_cache.put(cache_key, response)
        return False
    
    def allocate_memory(self, size: int) -> int | None:
        """Allocate memory from the pool."""
        try:
            return self._memory_pool.allocate(size)
        except Exception:
            return None
    
    def deallocate_memory(self, ptr: int, size: int) -> bool:
        """Deallocate memory back to the pool."""
        try:
            self._memory_pool.deallocate(ptr, size)
            return True
        except Exception:
            return False
    
    def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {}
        
        # Memory pool stats
        pool_stats = self._memory_pool.get_stats()
        stats.update({f"pool_{k}": v for k, v in pool_stats.items()})
        
        # Pool info
        pool_info = self._memory_pool.get_pool_info()
        stats.update({f"pool_info_{k}": v for k, v in pool_info.items()})
        
        # Response cache stats
        if self._response_cache:
            cache_stats = self._response_cache.get_stats()
            stats.update(cache_stats)
        
        return stats
    
    def cleanup(self) -> dict[str, int]:
        """Perform cleanup and return statistics."""
        cleanup_stats = {}
        
        # Clear memory pools
        try:
            self._memory_pool.clear()
            cleanup_stats["memory_pools_cleared"] = 1
        except Exception:
            cleanup_stats["memory_pools_cleared"] = 0
        
        # Clear response cache
        if self._response_cache:
            try:
                self._response_cache.clear()
                cleanup_stats["response_cache_cleared"] = 1
            except Exception:
                cleanup_stats["response_cache_cleared"] = 0
        
        # Force garbage collection
        try:
            collected = gc.collect()
            cleanup_stats["gc_objects_collected"] = collected
        except Exception:
            cleanup_stats["gc_objects_collected"] = 0
        
        return cleanup_stats


# Global memory-aware handler instance
_global_handler: MemoryAwareRequestHandler | None = None
_handler_lock = threading.Lock()

def get_global_memory_handler() -> MemoryAwareRequestHandler:
    """Get or create the global memory handler."""
    global _global_handler
    
    if _global_handler is None:
        with _handler_lock:
            if _global_handler is None:
                _global_handler = MemoryAwareRequestHandler()
    
    return _global_handler

def configure_global_memory_handler(
    memory_pool_size: int = 1024,
    enable_response_caching: bool = True,
    cache_max_entries: int = 1000,
    cache_max_memory_mb: int = 100,
) -> None:
    """Configure the global memory handler."""
    global _global_handler
    
    with _handler_lock:
        _global_handler = MemoryAwareRequestHandler(
            memory_pool_size=memory_pool_size,
            enable_response_caching=enable_response_caching,
            cache_max_entries=cache_max_entries,
            cache_max_memory_mb=cache_max_memory_mb,
        )

def get_memory_stats() -> dict[str, Any]:
    """Get global memory statistics."""
    handler = get_global_memory_handler()
    return handler.get_memory_stats()

def cleanup_memory() -> dict[str, int]:
    """Perform global memory cleanup."""
    handler = get_global_memory_handler()
    return handler.cleanup()
