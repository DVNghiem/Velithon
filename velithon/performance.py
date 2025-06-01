import json
import threading
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
    """Ultra optimized JSON encoder with multiple backend support."""

    def __init__(self):
        # Direct functions for maximum performance - avoid multiple dispatch overhead
        if HAS_ORJSON:
            self._encode = self._encode_orjson
        elif HAS_UJSON:
            self._encode = self._encode_ujson
        else:
            self._encode = self._encode_stdlib
            
        # Cache for small, common responses
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._MAX_CACHE_SIZE = 1000
        
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
                    self._cache_hits += 1
                    return cached
                self._cache_misses += 1
                result = self._encode(obj)
                
                # Limit cache size to prevent memory growth
                if len(self._cache) < self._MAX_CACHE_SIZE:
                    self._cache[cache_key] = result
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
                        self._cache_hits += 1
                        return cached
                        
                    self._cache_misses += 1
                    result = self._encode(obj)
                    
                    # Limit cache size
                    if len(self._cache) < self._MAX_CACHE_SIZE:
                        self._cache[cache_key] = result
                    return result
            except Exception:
                # Fall through to normal encoding on any error
                pass
                
        # Normal encoding path for complex objects
        return self._encode(obj)


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


class MiddlewareOptimizer:
    """Optimize middleware stack for better performance."""

    # Use a larger cache size for better hit rate on busy servers
    @staticmethod
    @lru_cache(maxsize=5000)
    def cached_middleware_chain(middleware_tuple: tuple) -> Callable:
        """Cache compiled middleware chains for maximum performance."""
        
        # Pre-build the entire middleware chain at once instead of iteratively
        def optimized_chain(handler):
            # Use direct call for small chains (common case)
            if len(middleware_tuple) <= 3:
                # Unroll the loop for better performance
                if len(middleware_tuple) == 1:
                    return middleware_tuple[0](handler)
                elif len(middleware_tuple) == 2:
                    return middleware_tuple[0](middleware_tuple[1](handler))
                elif len(middleware_tuple) == 3:
                    return middleware_tuple[0](middleware_tuple[1](middleware_tuple[2](handler)))
            
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
            middleware_name = middleware.__class__.__name__.lower() if hasattr(middleware, '__class__') else str(middleware)
            
            if 'security' in middleware_name or 'auth' in middleware_name:
                high_priority.append(middleware)
            elif 'log' in middleware_name or 'compression' in middleware_name or 'cache' in middleware_name:
                low_priority.append(middleware)
            else:
                normal_priority.append(middleware)
        
        # Return optimized middleware stack with priority ordering
        return high_priority + normal_priority + low_priority


# Global optimized instances
_json_encoder = FastJSONEncoder()
_response_cache = ResponseCache()
_middleware_optimizer = MiddlewareOptimizer()


def get_json_encoder() -> FastJSONEncoder:
    """Get the global optimized JSON encoder."""
    return _json_encoder


def get_response_cache() -> ResponseCache:
    """Get the global response cache."""
    return _response_cache


def get_middleware_optimizer() -> MiddlewareOptimizer:
    """Get the global middleware optimizer."""
    return _middleware_optimizer
