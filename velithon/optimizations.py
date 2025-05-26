import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Callable, Dict, Optional

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

try:
    import ujson

    HAS_UJSON = True
except ImportError:
    HAS_UJSON = False


class FastJSONEncoder:
    """Optimized JSON encoder with multiple backend support."""

    def __init__(self):
        self.encoder = self._select_best_encoder()

    def _select_best_encoder(self) -> Callable[[Any], bytes]:
        """Select the fastest available JSON encoder."""
        if HAS_ORJSON:
            return lambda obj: orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY)
        elif HAS_UJSON:
            return lambda obj: ujson.dumps(obj).encode("utf-8")
        else:
            return lambda obj: json.dumps(obj, separators=(",", ":")).encode("utf-8")

    def encode(self, obj: Any) -> bytes:
        """Encode object to JSON bytes."""
        return self.encoder(obj)


class ObjectPool:
    """Memory-efficient object pool for frequently used objects."""

    def __init__(self, factory: Callable, max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self.pool = []
        self.lock = threading.Lock()

    def get(self):
        """Get an object from the pool or create a new one."""
        with self.lock:
            if self.pool:
                return self.pool.pop()
        return self.factory()

    def put(self, obj):
        """Return an object to the pool."""
        with self.lock:
            if len(self.pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, "reset"):
                    obj.reset()
                self.pool.append(obj)


class ResponseCache:
    """LRU cache for response objects to reduce allocations."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order = []
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached response."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        """Cache a response."""
        with self.lock:
            if key in self.cache:
                self.access_order.remove(key)
            elif len(self.cache) >= self.max_size:
                # Remove least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]

            self.cache[key] = value
            self.access_order.append(key)


class AsyncOptimizer:
    """Async optimization utilities for better concurrency."""

    @staticmethod
    async def gather_with_limit(tasks, limit: int = 100):
        """Execute tasks with concurrency limit."""
        semaphore = asyncio.Semaphore(limit)

        async def limited_task(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*[limited_task(task) for task in tasks])

    @staticmethod
    def create_optimized_executor(
        max_workers: Optional[int] = None,
    ) -> ThreadPoolExecutor:
        """Create an optimized thread pool executor."""
        if max_workers is None:
            import os

            max_workers = min(32, (os.cpu_count() or 1) + 4)

        return ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="velithon"
        )


class MiddlewareOptimizer:
    """Optimize middleware stack for better performance."""

    @staticmethod
    @lru_cache(maxsize=1000)
    def cached_middleware_chain(middleware_tuple: tuple) -> Callable:
        """Cache compiled middleware chains."""

        def middleware_chain(handler):
            for middleware in reversed(middleware_tuple):
                handler = middleware(handler)
            return handler

        return middleware_chain

    @staticmethod
    def optimize_middleware_stack(middlewares: list) -> list:
        """Optimize middleware stack by removing redundant operations."""
        # Remove duplicate middlewares
        seen = set()
        optimized = []
        for middleware in middlewares:
            middleware_id = id(middleware)  # Use class ID to identify middleware
            if middleware_id not in seen:
                seen.add(middleware_id)
                optimized.append(middleware)

        return optimized


class ConnectionPool:
    """Connection pooling for better resource management."""

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.connections = []
        self.active_connections = 0
        self.lock = threading.Lock()

    def get_connection(self):
        """Get a connection from the pool."""
        with self.lock:
            if self.connections:
                self.active_connections += 1
                return self.connections.pop()
            elif self.active_connections < self.max_connections:
                self.active_connections += 1
                return self._create_connection()
        return None

    def return_connection(self, connection):
        """Return a connection to the pool."""
        with self.lock:
            if len(self.connections) < self.max_connections // 2:
                self.connections.append(connection)
            self.active_connections -= 1

    def _create_connection(self):
        """Create a new connection (override in subclasses)."""
        return object()  # Placeholder


class RequestOptimizer:
    """Optimize request handling and parsing."""

    @staticmethod
    @lru_cache(maxsize=2000)
    def cached_header_parse(headers_str: str) -> dict:
        """Cache parsed headers."""
        headers = {}
        for line in headers_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        return headers

    @staticmethod
    @lru_cache(maxsize=1000)
    def cached_content_type_parse(content_type: str) -> tuple:
        """Cache content type parsing."""
        if ";" in content_type:
            media_type, params = content_type.split(";", 1)
            return media_type.strip(), params.strip()
        return content_type.strip(), ""


# Global optimized instances
_json_encoder = FastJSONEncoder()
_response_cache = ResponseCache()
_async_optimizer = AsyncOptimizer()
_middleware_optimizer = MiddlewareOptimizer()
_request_optimizer = RequestOptimizer()

# Object pools for common objects
_dict_pool = ObjectPool(dict, max_size=200)
_list_pool = ObjectPool(list, max_size=200)


def get_json_encoder() -> FastJSONEncoder:
    """Get the global optimized JSON encoder."""
    return _json_encoder


def get_response_cache() -> ResponseCache:
    """Get the global response cache."""
    return _response_cache


def get_async_optimizer() -> AsyncOptimizer:
    """Get the global async optimizer."""
    return _async_optimizer


def get_middleware_optimizer() -> MiddlewareOptimizer:
    """Get the global middleware optimizer."""
    return _middleware_optimizer


def get_request_optimizer() -> RequestOptimizer:
    """Get the global request optimizer."""
    return _request_optimizer


def get_dict_from_pool() -> dict:
    """Get a dictionary from the object pool."""
    return _dict_pool.get()


def return_dict_to_pool(d: dict):
    """Return a dictionary to the object pool."""
    d.clear()
    _dict_pool.put(d)


def get_list_from_pool() -> list:
    """Get a list from the object pool."""
    return _list_pool.get()


def return_list_to_pool(lst: list):
    """Return a list to the object pool."""
    lst.clear()
    _list_pool.put(lst)


class PerformanceProfiler:
    """Simple performance profiler for identifying bottlenecks."""

    def __init__(self):
        self.timings = {}
        self.call_counts = {}

    def time_function(self, func_name: str):
        """Decorator to time function execution."""

        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    execution_time = end_time - start_time

                    if func_name not in self.timings:
                        self.timings[func_name] = []
                        self.call_counts[func_name] = 0

                    self.timings[func_name].append(execution_time)
                    self.call_counts[func_name] += 1

            return wrapper

        return decorator

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        for func_name, times in self.timings.items():
            stats[func_name] = {
                "mean": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "calls": self.call_counts[func_name],
                "total": sum(times),
            }
        return stats


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    return _profiler
