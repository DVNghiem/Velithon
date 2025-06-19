import asyncio
import concurrent.futures
import functools
import json
import os
import random
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any, TypeVar

from ._velithon import ResponseCache
from .cache import CacheConfig, LRUCache, cache_manager, middleware_cache

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

try:
    import ujson  # type: ignore

    HAS_UJSON = True
except ImportError:
    HAS_UJSON = False


T = TypeVar('T')

# OPTIMIZED: Better configured thread pool with optimal sizing
_thread_pool = None
_pool_lock = threading.Lock()


def set_thread_pool() -> None:
    global _thread_pool
    with _pool_lock:
        if _thread_pool is None:
            # Optimized thread count: I/O bound (higher), CPU bound (lower)
            cpu_count = os.cpu_count() or 1
            # For web applications, I/O bound operations are more common
            max_workers = min(64, cpu_count * 8)  # Increased multiplier for I/O tasks
            _thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix='velithon_optimized',
                initializer=_warm_up_thread,  # Pre-warm threads
            )


def _warm_up_thread():
    """Warm up worker threads to reduce cold start latency."""
    # Pre-allocate some common objects to reduce first-call overhead
    import json
    import time

    json.dumps({'warm_up': True})
    time.perf_counter()  # Initialize time measurement


def is_async_callable(obj: Any) -> bool:
    if isinstance(obj, functools.partial):
        obj = obj.func
    return asyncio.iscoroutinefunction(obj) or (
        callable(obj) and asyncio.iscoroutinefunction(getattr(obj, '__call__', None))
    )


async def run_in_threadpool(func: Callable, *args, **kwargs) -> Any:
    global _thread_pool
    if _thread_pool is None:
        set_thread_pool()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_thread_pool, lambda: func(*args, **kwargs))


async def iterate_in_threadpool(iterator: Iterable[T]) -> AsyncIterator[T]:
    as_iterator = iter(iterator)

    def next_item() -> tuple[bool, T | None]:
        try:
            return True, next(as_iterator)
        except StopIteration:
            return False, None

    while True:
        has_next, item = await asyncio.to_thread(next_item)
        if not has_next:
            break
        yield item


class RequestIDGenerator:
    """Efficient request ID generator with much less overhead than UUID."""

    def __init__(self):
        self._prefix = f'{random.randint(100, 999)}'
        self._counter = 0
        self._lock = threading.Lock()

    def generate(self) -> str:
        """Generate a unique request ID with format: prefix-timestamp-counter."""
        timestamp = int(time.time() * 1000)  # Timestamp in milliseconds

        with self._lock:
            self._counter = (self._counter + 1) % 100000
            request_id = f'{self._prefix}-{timestamp}-{self._counter:05d}'

        return request_id


class FastJSONEncoder:
    """Ultra optimized JSON encoder with multiple backend support."""

    def __init__(self):
        # Direct functions for maximum performance - avoid multiple dispatch overhead
        if HAS_ORJSON:
            self._encode = self._encode_orjson
        elif HAS_UJSON:
            self._encode = self._encode_ujson
        else:
            self._encode = self._encode_stdlib

        # Cache for small, common responses using centralized cache
        self._cache = LRUCache[Any, bytes](CacheConfig.get_cache_size('response'))
        cache_manager.register_cache('json_encoder', self._cache)

    def _encode_orjson(self, obj: Any) -> bytes:
        """Encode with orjson (fastest)."""
        try:
            return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY)
        except TypeError:
            # Fall back to standard JSON for types orjson can't handle
            return json.dumps(obj, separators=(',', ':')).encode('utf-8')

    def _encode_ujson(self, obj: Any) -> bytes:
        """Encode with ujson (faster than stdlib)."""
        try:
            return ujson.dumps(obj).encode('utf-8')
        except TypeError:
            # Fall back to standard JSON for types ujson can't handle
            return json.dumps(obj, separators=(',', ':')).encode('utf-8')

    def _encode_stdlib(self, obj: Any) -> bytes:
        """Encode with standard library json (always works but slower)."""
        return json.dumps(obj, separators=(',', ':')).encode('utf-8')

    def _create_dict_cache_key(self, obj: dict[str, Any]) -> str:
        """Create a collision-resistant cache key for dictionaries."""
        # Use a deterministic serialization approach that prevents collisions
        # by properly escaping separators and using length prefixes
        items = []
        for k, v in sorted(obj.items()):
            # Escape any special characters in keys and values
            key_str = (
                str(k).replace('\\', '\\\\').replace('|', '\\|').replace(':', '\\:')
            )
            val_str = (
                str(v).replace('\\', '\\\\').replace('|', '\\|').replace(':', '\\:')
            )
            # Use length-prefixed format to prevent ambiguity
            items.append(f'{len(key_str)}:{key_str}={len(val_str)}:{val_str}')

        return '|'.join(items)

    def encode(self, obj: Any) -> bytes:
        """Encode object to JSON bytes with caching for common values."""
        # Only cache simple types that are serializable and hashable
        if isinstance(obj, str | int | bool | float | type(None)):
            try:
                cached = self._cache.get(obj)
                if cached is not None:
                    return cached

                result = self._encode(obj)
                # Only cache small objects to prevent memory bloat
                if len(result) <= 256:  # 256 bytes limit
                    self._cache.put(obj, result)
                return result
            except (TypeError, OverflowError):
                # Fall through to normal encoding on any error
                pass

        # For small dicts, try to use cache with collision-resistant key
        if isinstance(obj, dict) and len(obj) <= 5:
            try:
                # Only cache if dict keys are all strings
                if all(isinstance(k, str) for k in obj.keys()):
                    # Create a collision-resistant cache key
                    cache_key = self._create_dict_cache_key(obj)

                    cached = self._cache.get(cache_key)
                    if cached is not None:
                        return cached

                    result = self._encode(obj)
                    # Only cache small results
                    if len(result) <= 512:  # 512 bytes limit for dicts
                        self._cache.put(cache_key, result)
                    return result
            except (TypeError, OverflowError):
                # Fall through to normal encoding on any error
                pass

        # Normal encoding path for complex objects
        return self._encode(obj)


class MiddlewareOptimizer:
    """Optimize middleware stack for better performance."""

    # Use centralized cache configuration for middleware chains
    @staticmethod
    @middleware_cache()
    def cached_middleware_chain(middleware_tuple: tuple) -> Callable:
        """Cache compiled middleware chains for maximum performance."""

        # Pre-build the entire middleware chain at once instead of iteratively
        def optimized_chain(handler: Callable) -> Callable:
            # Use direct call for small chains (common case)
            if len(middleware_tuple) <= 3:
                # Unroll the loop for better performance
                if len(middleware_tuple) == 1:
                    return middleware_tuple[0](handler)
                elif len(middleware_tuple) == 2:
                    return middleware_tuple[0](middleware_tuple[1](handler))
                elif len(middleware_tuple) == 3:
                    return middleware_tuple[0](
                        middleware_tuple[1](middleware_tuple[2](handler))
                    )

            # Fall back to loop for longer chains
            wrapped = handler
            for middleware in reversed(middleware_tuple):
                wrapped = middleware(wrapped)
            return wrapped

        return optimized_chain

    @staticmethod
    def optimize_middleware_stack(middlewares: list) -> list:
        """Optimize middleware stack by removing redundant operations and ordering for performance."""
        if not middlewares:
            return []

        # Categorize middlewares by priority (some are more expensive than others)
        high_priority = []
        normal_priority = []
        low_priority = []

        # Use set for faster duplicate detection
        seen = set()

        for middleware in middlewares:
            middleware_id = id(middleware)  # Use object ID for faster comparison

            if middleware_id in seen:
                continue  # Skip duplicates

            seen.add(middleware_id)

            # Optimize middleware categorization with faster string checks
            middleware_name = getattr(
                middleware, '__class__', type(middleware)
            ).__name__.lower()

            # Use startswith/endswith for faster string matching
            if any(
                pattern in middleware_name for pattern in ('security', 'auth', 'cors')
            ):
                high_priority.append(middleware)
            elif any(
                pattern in middleware_name
                for pattern in ('log', 'compression', 'cache')
            ):
                low_priority.append(middleware)
            else:
                normal_priority.append(middleware)

        # Return optimized middleware stack with priority ordering
        return high_priority + normal_priority + low_priority


# Global optimized instances
_json_encoder = FastJSONEncoder()
_response_cache = ResponseCache()
_middleware_optimizer = MiddlewareOptimizer()

# Register the middleware cache for management
cache_manager.register_lru_cache(
    'middleware_chain', _middleware_optimizer.cached_middleware_chain
)


def get_json_encoder() -> FastJSONEncoder:
    """Get the global optimized JSON encoder."""
    return _json_encoder


def get_response_cache() -> ResponseCache:
    """Get the global response cache."""
    return _response_cache


def get_middleware_optimizer() -> MiddlewareOptimizer:
    """Get the global middleware optimizer."""
    return _middleware_optimizer


def get_cache_stats() -> dict:
    """Get comprehensive cache statistics from the cache manager."""
    return cache_manager.get_cache_stats()


def clear_all_caches() -> None:
    """Clear all performance-related caches."""
    cache_manager.clear_all_caches()
    _json_encoder._cache.clear()
    _response_cache = ResponseCache()  # Reset response cache
