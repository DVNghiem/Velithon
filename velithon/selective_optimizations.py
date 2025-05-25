
import time
import threading
from typing import Any, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

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


class SelectiveOptimizer:
    """Apply optimizations selectively based on performance profiling."""
    
    def __init__(self):
        self.optimization_stats = {}
        self.enabled_optimizations = set()
        self.profiling_mode = False
        self._lock = threading.Lock()
    
    def profile_optimization(self, name: str, optimized_func: Callable, baseline_func: Callable):
        """Profile an optimization to determine if it should be enabled."""
        if not self.profiling_mode:
            return optimized_func if name in self.enabled_optimizations else baseline_func
        
        # Run micro-benchmark
        iterations = 1000
        
        # Baseline timing
        start = time.perf_counter()
        for _ in range(iterations):
            baseline_func()
        baseline_time = time.perf_counter() - start
        
        # Optimized timing
        start = time.perf_counter()
        for _ in range(iterations):
            optimized_func()
        optimized_time = time.perf_counter() - start
        
        # Determine if optimization is beneficial
        speedup = baseline_time / optimized_time if optimized_time > 0 else 0
        
        with self._lock:
            self.optimization_stats[name] = {
                'speedup': speedup,
                'baseline_time': baseline_time,
                'optimized_time': optimized_time,
                'beneficial': speedup > 1.1  # Only enable if >10% improvement
            }
            
            if speedup > 1.1:
                self.enabled_optimizations.add(name)
            else:
                self.enabled_optimizations.discard(name)
        
        return optimized_func if speedup > 1.1 else baseline_func
    
    def is_enabled(self, optimization_name: str) -> bool:
        """Check if an optimization is enabled."""
        return optimization_name in self.enabled_optimizations


class LightweightJSONEncoder:
    """Lightweight JSON encoder with minimal overhead."""
    
    def __init__(self):
        self.encoder = self._get_best_encoder()
    
    def _get_best_encoder(self):
        """Get the best available JSON encoder."""
        if HAS_ORJSON:
            return lambda obj: orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS)
        elif HAS_UJSON:
            return ujson.dumps
        else:
            import json
            return json.dumps
    
    def encode(self, obj: Any) -> bytes:
        """Encode object to JSON bytes."""
        result = self.encoder(obj)
        return result if isinstance(result, bytes) else result.encode('utf-8')


class MinimalCache:
    """Minimal cache with very low overhead."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = {}
        self.access_count = 0
    
    def get(self, key: str) -> Optional[bytes]:
        """Get value from cache."""
        return self.cache.get(key)
    
    def put(self, key: str, value: bytes):
        """Put value in cache with minimal overhead."""
        if len(self.cache) >= self.max_size:
            # Simple eviction: clear cache when full
            self.cache.clear()
        self.cache[key] = value
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()


class ConditionalOptimizations:
    """Conditional optimizations that can be enabled/disabled."""
    
    def __init__(self):
        self.optimizer = SelectiveOptimizer()
        self.json_encoder = LightweightJSONEncoder()
        self.response_cache = MinimalCache(max_size=50)  # Smaller cache
        self.thread_pool = None
        
        # Enable only proven optimizations by default
        self.optimizer.enabled_optimizations.update({
            'json_encoding',  # This showed clear benefit
        })
    
    def optimized_json_encode(self, obj: Any) -> bytes:
        """Conditionally optimized JSON encoding."""
        if self.optimizer.is_enabled('json_encoding'):
            return self.json_encoder.encode(obj)
        else:
            # Fallback to orjson directly
            if HAS_ORJSON:
                return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS)
            else:
                import json
                return json.dumps(obj).encode('utf-8')
    
    def optimized_response_cache(self, key: str, generator: Callable[[], bytes]) -> bytes:
        """Conditionally use response caching."""
        if not self.optimizer.is_enabled('response_caching'):
            return generator()
        
        cached = self.response_cache.get(key)
        if cached is not None:
            return cached
        
        result = generator()
        self.response_cache.put(key, result)
        return result
    
    def get_thread_pool(self) -> Optional[ThreadPoolExecutor]:
        """Get optimized thread pool if beneficial."""
        if not self.optimizer.is_enabled('thread_pool'):
            return None
        
        if self.thread_pool is None:
            import os
            max_workers = min(8, (os.cpu_count() or 1) + 2)  # Conservative sizing
            self.thread_pool = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="velithon"
            )
        return self.thread_pool
    
    def enable_profiling(self):
        """Enable profiling mode to test optimizations."""
        self.optimizer.profiling_mode = True
    
    def disable_profiling(self):
        """Disable profiling mode."""
        self.optimizer.profiling_mode = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        return {
            'enabled_optimizations': list(self.optimizer.enabled_optimizations),
            'optimization_stats': self.optimizer.optimization_stats,
            'cache_size': len(self.response_cache.cache)
        }


# Global instance
_conditional_optimizations = ConditionalOptimizations()


def get_conditional_optimizations() -> ConditionalOptimizations:
    """Get the global conditional optimizations instance."""
    return _conditional_optimizations


def optimized_json_response(content: Any) -> bytes:
    """Create optimized JSON response with minimal overhead."""
    return _conditional_optimizations.optimized_json_encode(content)


def cached_response(cache_key: str, generator: Callable[[], bytes]) -> bytes:
    """Conditionally cached response generation."""
    return _conditional_optimizations.optimized_response_cache(cache_key, generator)


def enable_optimization_profiling():
    """Enable optimization profiling to test benefits."""
    _conditional_optimizations.enable_profiling()


def disable_optimization_profiling():
    """Disable optimization profiling."""
    _conditional_optimizations.disable_profiling()


def get_optimization_stats() -> Dict[str, Any]:
    """Get current optimization statistics."""
    return _conditional_optimizations.get_stats()
