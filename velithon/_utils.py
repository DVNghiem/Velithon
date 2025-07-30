import asyncio
import concurrent.futures
import functools
import os
import random
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterable
from typing import Any, TypeVar

from ._velithon import ResponseCache
from .cache import cache_manager
from .memory_management import (
    enable_memory_optimizations,
    get_memory_context,
    manual_memory_cleanup,
)

try:
    import orjson
except ImportError as exc:
    raise ImportError(
        'orjson is required for Velithon. Install it with: pip install orjson'
    ) from exc


T = TypeVar('T')

_thread_pool = None
_pool_lock = threading.Lock()


def set_thread_pool() -> None:
    """Set up optimized thread pool for Velithon's performance requirements."""
    global _thread_pool
    with _pool_lock:
        if _thread_pool is None:
            # Optimized thread count: I/O bound (higher), CPU bound (lower)
            cpu_count = os.cpu_count() or 1

            # Performance-optimized worker count based on workload type
            # For web applications, I/O bound operations are more common
            max_workers = min(64, cpu_count * 8)  # Increased multiplier for I/O tasks

            # Enhanced thread pool with performance optimizations
            _thread_pool = concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix='velithon_optimized',
                initializer=_warm_up_thread,  # Pre-warm threads
            )


def _warm_up_thread():
    """Warm up worker threads to reduce cold start latency."""
    # Pre-allocate some common objects to reduce first-call overhead
    import json
    import marshal
    import pickle
    import threading
    import time

    # Warm up common operations
    json.dumps({'warm_up': True})
    time.perf_counter()  # Initialize time measurement

    # Pre-initialize thread-local storage if needed
    _ = threading.current_thread().name  # Access thread name

    # Warm up Python's import system in thread context
    try:
        pickle.dumps(1)
        marshal.dumps(1)
    except Exception:
        pass  # Ignore warm-up errors


def is_async_callable(obj: Any) -> bool:
    if isinstance(obj, functools.partial):
        obj = obj.func
    return (
        asyncio.iscoroutinefunction(obj)
        or (
            callable(obj)
            and asyncio.iscoroutinefunction(
                obj.__call__ if callable(obj) else None
            )
        )
    )


async def run_in_threadpool(func: Callable, *args, **kwargs) -> Any:
    """Thread pool execution with enhanced performance features.

    Args:
        func: The function to execute in the thread pool
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function execution

    """
    global _thread_pool
    if _thread_pool is None:
        set_thread_pool()

    loop = asyncio.get_running_loop()

    # Fast path for simple functions without arguments
    if not args and not kwargs:
        return await loop.run_in_executor(_thread_pool, func)

    # Memory-efficient parameter passing for large kwargs
    if len(kwargs) > 10 or any(
        hasattr(v, '__len__') and len(v) > 1000
        for v in kwargs.values()
        if hasattr(v, '__len__')
    ):
        # For large parameter sets, use partial to avoid lambda closure overhead
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(_thread_pool, partial_func)

    # Standard path with lambda (most common case)
    # Use more efficient lambda creation for small parameter sets
    if args and kwargs:
        return await loop.run_in_executor(_thread_pool, lambda: func(*args, **kwargs))
    elif args:
        return await loop.run_in_executor(_thread_pool, lambda: func(*args))
    else:  # kwargs only
        return await loop.run_in_executor(_thread_pool, lambda: func(**kwargs))


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
    """Ultra-fast request ID generator optimized for high-throughput scenarios."""

    def __init__(self):
        # Pre-compute prefix once to avoid repeated random calls
        self._prefix = str(random.randint(100, 999))
        # Use atomic counter for thread safety without locks
        import threading

        self._counter = threading.local()
        # Pre-allocate timestamp cache to reduce time.time() calls
        self._last_timestamp = 0
        self._timestamp_cache_duration = 0.001  # 1ms cache duration
        self._last_cache_time = 0.0

    def generate(self) -> str:
        """Generate a unique request ID with minimal overhead."""
        # Use thread-local counter to avoid locks
        if not hasattr(self._counter, 'value'):
            self._counter.value = 0
            # Add thread ID to ensure uniqueness across threads
            self._counter.thread_offset = threading.get_ident() % 1000

        # Cache timestamp for 1ms to reduce system calls
        current_time = time.perf_counter()
        if current_time - self._last_cache_time > self._timestamp_cache_duration:
            self._last_timestamp = int(time.time() * 1000)
            self._last_cache_time = current_time

        # Increment counter (no modulo needed for better performance)
        self._counter.value += 1

        # Use faster string concatenation for hot path
        # Format: prefix-timestamp-threadoffset-counter
        return (
            f'{self._prefix}-{self._last_timestamp}-'
            f'{self._counter.thread_offset}-{self._counter.value}'
        )


class FastJSONEncoder:
    """Simplified JSON encoder using only orjson."""

    def __init__(self):
        # Use orjson with optimized settings
        self._encode_func = lambda obj: orjson.dumps(
            obj, option=orjson.OPT_SERIALIZE_NUMPY
        )
        self._backend = 'orjson'

        # Simple cache for very common small responses only
        self._simple_cache: dict[str, bytes] = {}

    def encode(self, obj: Any) -> bytes:
        """Encode object to JSON bytes using orjson with minimal caching."""
        # Only cache very simple, small string responses
        if isinstance(obj, str) and len(obj) <= 50:
            cached = self._simple_cache.get(obj)
            if cached is not None:
                return cached

            result = self._encode_func(obj)
            # Only cache if result is small and cache isn't too large
            if len(result) <= 100 and len(self._simple_cache) < 50:
                self._simple_cache[obj] = result
            return result

        # Direct orjson encoding for all other cases
        return self._encode_func(obj)


class SimpleMiddlewareOptimizer:
    """Simplified middleware stack optimization."""

    @staticmethod
    def optimize_middleware_stack(middlewares: list) -> list:
        """Remove duplicates from the middleware stack."""
        if not middlewares:
            return []

        # Remove duplicates while preserving order
        seen = set()
        optimized = []

        for middleware in middlewares:
            middleware_id = id(middleware)
            if middleware_id not in seen:
                seen.add(middleware_id)
                optimized.append(middleware)

        return optimized


# Global simplified instances
_json_encoder = FastJSONEncoder()
_response_cache = ResponseCache()
_middleware_optimizer = SimpleMiddlewareOptimizer()


def get_json_encoder() -> FastJSONEncoder:
    """Get the global simplified JSON encoder."""
    return _json_encoder


def get_response_cache() -> ResponseCache:
    """Get the global response cache."""
    return _response_cache


def get_middleware_optimizer() -> SimpleMiddlewareOptimizer:
    """Get the global simplified middleware optimizer."""
    return _middleware_optimizer

def clear_all_caches() -> None:
    """Clear all framework caches."""
    # Clear JSON encoder cache
    _json_encoder._simple_cache.clear()

    # Clear cache manager caches
    try:
        cache_manager.clear_all_caches()
    except Exception:
        pass  # Ignore cache manager errors


def initialize_memory_management() -> None:
    """Initialize basic memory management for the Velithon framework."""
    # Use lightweight mode for better performance
    try:
        enable_memory_optimizations(lightweight=True)
    except Exception:
        pass  # Ignore if memory optimizations are not available

def cleanup_framework_memory():
    """Perform basic framework memory cleanup."""
    # Clear framework caches
    clear_all_caches()

    # Clear thread pool if needed
    global _thread_pool
    if _thread_pool:
        _thread_pool.shutdown(wait=False)
        _thread_pool = None

    # Basic memory cleanup if available
    try:
        manual_memory_cleanup()
    except Exception:
        pass  # Ignore if memory management is not available

def optimized_json_encode(obj: Any) -> bytes:
    """Simplified JSON encoding."""
    return get_json_encoder().encode(obj)


def request_memory_context():
    """Get a simple memory context for request processing."""
    try:
        return get_memory_context(enable_monitoring=False)
    except Exception:
        # Return a no-op context if memory management is not available
        return NoOpContext()


class NoOpContext:
    """No-op context manager for when memory management is not available."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
