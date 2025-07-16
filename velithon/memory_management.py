"""Advanced garbage collection and memory optimization for Velithon framework.

This module provides comprehensive memory management optimizations including:
- Intelligent garbage collection tuning
- Memory pools for frequently allocated objects
- Weak reference management for caches
- Object lifecycle optimization
- Memory monitoring and cleanup strategies
"""

import gc
import sys
import threading
import time
import weakref
from collections import deque
from typing import Any, Callable, Generic, Optional, TypeVar, Union
from collections.abc import Iterator
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class GarbageCollectionOptimizer:
    """Optimizes garbage collection for web server workloads."""

    def __init__(self):
        """Initialize the garbage collection optimizer."""
        self._original_thresholds = gc.get_threshold()
        self._optimization_enabled = False
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._lock = threading.Lock()

    def enable_optimizations(self) -> None:
        """Enable garbage collection optimizations for web workloads."""
        with self._lock:
            if self._optimization_enabled:
                return

            # Optimize GC thresholds for web server workloads
            # Web servers typically have many short-lived objects (requests, responses)
            # and some long-lived objects (caches, connections)

            # Increase generation 0 threshold to reduce frequent collections
            # of short-lived request objects
            gen0_threshold = 2000  # Default is 700

            # Keep generation 1 threshold reasonable for middleware objects
            gen1_threshold = 15  # Default is 10

            # Reduce generation 2 threshold for better long-term memory management
            gen2_threshold = 5  # Default is 10

            gc.set_threshold(gen0_threshold, gen1_threshold, gen2_threshold)

            # Disable automatic garbage collection during request processing
            # We'll trigger it manually at appropriate times
            gc.disable()

            self._optimization_enabled = True
            logger.info(
                f'GC optimization enabled. Thresholds: {gen0_threshold}, '
                f'{gen1_threshold}, {gen2_threshold}'
            )

    def disable_optimizations(self) -> None:
        """Restore original garbage collection settings."""
        with self._lock:
            if not self._optimization_enabled:
                return

            gc.set_threshold(*self._original_thresholds)
            gc.enable()
            self._optimization_enabled = False
            logger.info('GC optimization disabled, restored original settings')

    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called during garbage collection."""
        with self._lock:
            self._cleanup_callbacks.append(callback)

    def manual_collection(self, generation: int = 2) -> dict[str, int]:
        """Perform manual garbage collection with statistics."""
        start_time = time.perf_counter()

        # Call cleanup callbacks before collection
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f'Cleanup callback failed: {e}')

        # Perform collection
        collected = gc.collect(generation)

        collection_time = time.perf_counter() - start_time

        stats = {
            'collected_objects': collected,
            'collection_time_ms': collection_time * 1000,
            'generation': generation,
            'objects_remaining': len(gc.get_objects()),
        }

        if collected > 100:  # Only log significant collections
            logger.debug(
                f'GC collected {collected} objects in {collection_time*1000:.2f}ms '
                f'(gen {generation})'
            )

        return stats

    def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory and GC statistics."""
        return {
            'gc_enabled': gc.isenabled(),
            'gc_thresholds': gc.get_threshold(),
            'gc_counts': gc.get_count(),
            'gc_stats': gc.get_stats(),
            'total_objects': len(gc.get_objects()),
            'optimization_enabled': self._optimization_enabled,
        }

    def periodic_cleanup(self, interval_seconds: float = 30.0) -> None:
        """Start a background thread for periodic garbage collection."""

        def cleanup_worker():
            while self._optimization_enabled:
                time.sleep(interval_seconds)
                if self._optimization_enabled:
                    self.manual_collection(0)  # Clean generation 0 regularly

                    # Occasionally clean higher generations
                    if time.time() % 300 < interval_seconds:  # Every 5 minutes
                        self.manual_collection(2)

        if self._optimization_enabled:
            thread = threading.Thread(target=cleanup_worker, daemon=True)
            thread.start()


class ObjectPool(Generic[T]):
    """Thread-safe object pool to reduce allocations and GC pressure."""

    def __init__(
        self,
        factory: Callable[[], T],
        reset_func: Optional[Callable[[T], None]] = None,
        max_size: int = 100,
    ):
        """Initialize object pool with factory and optional reset function."""
        self._factory = factory
        self._reset_func = reset_func
        self._max_size = max_size
        self._pool: deque[T] = deque()
        self._lock = threading.Lock()
        self._created_count = 0
        self._reused_count = 0

    def acquire(self) -> T:
        """Acquire an object from the pool."""
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                self._reused_count += 1
                return obj

            obj = self._factory()
            self._created_count += 1
            return obj

    def release(self, obj: T) -> None:
        """Return an object to the pool."""
        if self._reset_func:
            try:
                self._reset_func(obj)
            except Exception as e:
                logger.warning(f'Object reset failed: {e}')
                return  # Don't return broken objects to pool

        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(obj)

    def clear(self) -> None:
        """Clear the pool."""
        with self._lock:
            self._pool.clear()

    def get_stats(self) -> dict[str, int]:
        """Get pool statistics."""
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'max_size': self._max_size,
                'created_count': self._created_count,
                'reused_count': self._reused_count,
                'reuse_ratio': (
                    self._reused_count / (self._created_count + self._reused_count)
                    if (self._created_count + self._reused_count) > 0
                    else 0.0
                ),
            }


class WeakRefCache(Generic[K, V]):
    """Cache using weak references to prevent memory leaks."""

    def __init__(self, max_size: int = 1000):
        """Initialize weak reference cache with maximum size."""
        self._cache: weakref.WeakValueDictionary[K, V] = weakref.WeakValueDictionary()
        self._access_order: deque[K] = deque()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: K) -> Optional[V]:
        """Get value from cache."""
        with self._lock:
            try:
                value = self._cache[key]
                # Move to end (most recently accessed)
                try:
                    self._access_order.remove(key)
                except ValueError:
                    pass  # Key not in access order
                self._access_order.append(key)
                self._hits += 1
                return value
            except KeyError:
                self._misses += 1
                return None

    def put(self, key: K, value: V) -> None:
        """Put value in cache."""
        with self._lock:
            # Check if we need to evict
            if len(self._cache) >= self._max_size:
                self._evict_lru()

            self._cache[key] = value
            self._access_order.append(key)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        while self._access_order:
            oldest_key = self._access_order.popleft()
            if oldest_key in self._cache:
                del self._cache[oldest_key]
                break

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_ratio = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_ratio': hit_ratio,
            }


class MemoryMonitor:
    """Monitor memory usage and trigger cleanup when needed."""

    def __init__(self, threshold_mb: float = 100.0):
        """Initialize memory monitor with threshold in megabytes."""
        self._threshold_bytes = threshold_mb * 1024 * 1024
        self._last_check = 0.0
        self._check_interval = 10.0  # Check every 10 seconds
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._lock = threading.Lock()

    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when memory usage is high."""
        with self._lock:
            self._cleanup_callbacks.append(callback)

    def check_memory_usage(self) -> bool:
        """Check if memory usage exceeds threshold and trigger cleanup if needed."""
        current_time = time.time()

        # Rate limit memory checks
        if current_time - self._last_check < self._check_interval:
            return False

        self._last_check = current_time

        try:
            import psutil

            process = psutil.Process()
            memory_usage = process.memory_info().rss

            if memory_usage > self._threshold_bytes:
                logger.warning(
                    f'Memory usage ({memory_usage / 1024 / 1024:.1f} MB) '
                    f'exceeds threshold ({self._threshold_bytes / 1024 / 1024:.1f} MB)'
                )

                # Trigger cleanup callbacks
                for callback in self._cleanup_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.warning(f'Memory cleanup callback failed: {e}')

                return True

        except ImportError:
            # psutil not available, fall back to basic GC stats
            obj_count = len(gc.get_objects())
            if obj_count > 50000:  # Arbitrary threshold
                logger.warning(f'High object count: {obj_count}')
                return True

        return False


class MemoryOptimizer:
    """Main memory optimization coordinator."""

    def __init__(self):
        """Initialize memory optimizer with all components."""
        self.gc_optimizer = GarbageCollectionOptimizer()
        self.memory_monitor = MemoryMonitor()
        self._object_pools: dict[str, ObjectPool] = {}
        self._weak_caches: dict[str, WeakRefCache] = {}
        self._enabled = False

        # Register cleanup callbacks
        self.gc_optimizer.register_cleanup_callback(self._cleanup_pools)
        self.memory_monitor.register_cleanup_callback(self._emergency_cleanup)

    def enable(self) -> None:
        """Enable all memory optimizations."""
        if self._enabled:
            return

        self.gc_optimizer.enable_optimizations()
        self.gc_optimizer.periodic_cleanup()
        self._enabled = True
        logger.info('Memory optimizations enabled')

    def disable(self) -> None:
        """Disable memory optimizations."""
        if not self._enabled:
            return

        self.gc_optimizer.disable_optimizations()
        self._cleanup_pools()
        self._enabled = False
        logger.info('Memory optimizations disabled')

    def create_object_pool(
        self,
        name: str,
        factory: Callable[[], T],
        reset_func: Optional[Callable[[T], None]] = None,
        max_size: int = 100,
    ) -> ObjectPool[T]:
        """Create a named object pool."""
        pool = ObjectPool(factory, reset_func, max_size)
        self._object_pools[name] = pool
        return pool

    def get_object_pool(self, name: str) -> Optional[ObjectPool]:
        """Get an object pool by name."""
        return self._object_pools.get(name)

    def create_weak_cache(self, name: str, max_size: int = 1000) -> WeakRefCache:
        """Create a named weak reference cache."""
        cache = WeakRefCache(max_size=max_size)
        self._weak_caches[name] = cache
        return cache

    def get_weak_cache(self, name: str) -> Optional[WeakRefCache]:
        """Get a weak reference cache by name."""
        return self._weak_caches.get(name)

    def _cleanup_pools(self) -> None:
        """Clean up object pools."""
        for pool in self._object_pools.values():
            pool.clear()

    def _emergency_cleanup(self) -> None:
        """Emergency cleanup when memory usage is high."""
        # Clear weak caches
        for cache in self._weak_caches.values():
            cache.clear()

        # Clear object pools
        self._cleanup_pools()

        # Force garbage collection
        self.gc_optimizer.manual_collection(2)

    def get_comprehensive_stats(self) -> dict[str, Any]:
        """Get comprehensive memory and optimization statistics."""
        stats = {
            'gc_stats': self.gc_optimizer.get_memory_stats(),
            'enabled': self._enabled,
            'object_pools': {
                name: pool.get_stats() for name, pool in self._object_pools.items()
            },
            'weak_caches': {
                name: cache.get_stats() for name, cache in self._weak_caches.items()
            },
        }

        # Add system memory info if available
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            stats['system_memory'] = {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
            }
        except ImportError:
            pass

        return stats

    def manual_cleanup(self) -> dict[str, Any]:
        """Perform manual cleanup and return statistics."""
        start_time = time.perf_counter()

        # Cleanup pools and caches
        self._cleanup_pools()
        for cache in self._weak_caches.values():
            cache.clear()

        # Perform garbage collection
        gc_stats = self.gc_optimizer.manual_collection(2)

        cleanup_time = time.perf_counter() - start_time

        return {
            'cleanup_time_ms': cleanup_time * 1000,
            'gc_stats': gc_stats,
        }


# Global memory optimizer instance
_memory_optimizer = MemoryOptimizer()


def get_memory_optimizer() -> MemoryOptimizer:
    """Get the global memory optimizer instance."""
    return _memory_optimizer


def enable_memory_optimizations() -> None:
    """Enable memory optimizations globally."""
    _memory_optimizer.enable()


def disable_memory_optimizations() -> None:
    """Disable memory optimizations globally."""
    _memory_optimizer.disable()


def get_memory_stats() -> dict[str, Any]:
    """Get comprehensive memory statistics."""
    return _memory_optimizer.get_comprehensive_stats()


def manual_memory_cleanup() -> dict[str, Any]:
    """Perform manual memory cleanup."""
    return _memory_optimizer.manual_cleanup()


# Context manager for request-scoped memory optimization
class RequestMemoryContext:
    """Context manager for request-scoped memory optimizations."""

    def __init__(self, enable_monitoring: bool = True):
        """Initialize request memory context."""
        self.enable_monitoring = enable_monitoring
        self._start_objects = 0

    def __enter__(self):
        """Enter the context manager."""
        if self.enable_monitoring:
            self._start_objects = len(gc.get_objects())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and perform cleanup if needed."""
        if self.enable_monitoring:
            # Check if we should trigger cleanup
            current_objects = len(gc.get_objects())
            if current_objects - self._start_objects > 1000:  # Threshold
                _memory_optimizer.gc_optimizer.manual_collection(0)


# Decorators for automatic memory management
def with_memory_optimization(func: Callable) -> Callable:
    """Add memory optimization to a function."""
    if hasattr(func, '__wrapped__'):
        return func  # Already wrapped

    def wrapper(*args, **kwargs):
        with RequestMemoryContext():
            return func(*args, **kwargs)

    wrapper.__wrapped__ = func
    return wrapper


def with_object_pool(pool_name: str):
    """Use an object pool for function results."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            pool = _memory_optimizer.get_object_pool(pool_name)
            if pool:
                # This is a simplified example - actual implementation
                # would need to handle object lifecycle properly
                result = func(*args, **kwargs)
                return result
            return func(*args, **kwargs)

        return wrapper

    return decorator
