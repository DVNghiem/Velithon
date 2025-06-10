import json
from typing import Any, Callable

from ._velithon import ResponseCache
from .cache import CacheConfig, LRUCache, cache_manager, middleware_cache

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
        self._cache = LRUCache[Any, bytes](CacheConfig.get_cache_size("response"))
        cache_manager.register_cache("json_encoder", self._cache)

    def _encode_orjson(self, obj: Any) -> bytes:
        """Encode with orjson (fastest)."""
        try:
            return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY)
        except TypeError:
            # Fall back to standard JSON for types orjson can't handle
            return json.dumps(obj, separators=(",", ":")).encode("utf-8")

    def _encode_ujson(self, obj: Any) -> bytes:
        """Encode with ujson (faster than stdlib)."""
        try:
            return ujson.dumps(obj).encode("utf-8")
        except TypeError:
            # Fall back to standard JSON for types ujson can't handle
            return json.dumps(obj, separators=(",", ":")).encode("utf-8")

    def _encode_stdlib(self, obj: Any) -> bytes:
        """Encode with standard library json (always works but slower)."""
        return json.dumps(obj, separators=(",", ":")).encode("utf-8")

    def encode(self, obj: Any) -> bytes:
        """Encode object to JSON bytes with caching for common values."""
        # Only cache simple types that are serializable and hashable
        if isinstance(obj, (str, int, bool, float, type(None))):
            try:
                cache_key = obj
                cached = self._cache.get(cache_key)
                if cached is not None:
                    return cached

                result = self._encode(obj)
                self._cache.put(cache_key, result)
                return result
            except Exception:
                # Fall through to normal encoding on any error
                pass

        # For small dicts, try to use cache with string key
        if isinstance(obj, dict) and len(obj) <= 5:
            try:
                # Only cache if dict keys are all strings
                if all(isinstance(k, str) for k in obj.keys()):
                    # Create a stable string representation for the dict
                    items = sorted((str(k), str(v)) for k, v in obj.items())
                    cache_key = "|".join(f"{k}:{v}" for k, v in items)

                    cached = self._cache.get(cache_key)
                    if cached is not None:
                        return cached

                    result = self._encode(obj)
                    self._cache.put(cache_key, result)
                    return result
            except Exception:
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
        def optimized_chain(handler) -> Callable:
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

        # Remove duplicates while categorizing
        seen = set()

        for middleware in middlewares:
            middleware_id = id(middleware)  # Use object ID for faster comparison

            if middleware_id in seen:
                continue  # Skip duplicates

            seen.add(middleware_id)

            # Categorize by middleware type
            # High priority: Critical security middleware that must run first
            # Low priority: Expensive middleware that should run last
            middleware_name = (
                middleware.__class__.__name__.lower()
                if hasattr(middleware, "__class__")
                else str(middleware)
            )

            if "security" in middleware_name or "auth" in middleware_name:
                high_priority.append(middleware)
            elif (
                "log" in middleware_name
                or "compression" in middleware_name
                or "cache" in middleware_name
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
    "middleware_chain", _middleware_optimizer.cached_middleware_chain
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
