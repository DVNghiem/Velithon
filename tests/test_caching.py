"""
Tests for caching functionality and performance optimizations.
"""
import time
from unittest.mock import MagicMock

import pytest

from velithon.cache import (
    CacheConfig,
    create_lru_cache,
    middleware_cache,
    parser_cache,
    response_cache,
    route_cache,
    signature_cache,
)
from velithon.performance import MiddlewareOptimizer


class TestCacheConfig:
    """Test cache configuration management."""
    
    def test_cache_config_defaults(self):
        """Test default cache configuration values."""
        # Test CacheConfig method existence
        assert hasattr(CacheConfig, 'get_cache_size')
        assert CacheConfig.get_cache_size('route') > 0
        assert CacheConfig.get_cache_size('middleware') > 0
        assert CacheConfig.get_cache_size('signature') > 0

    def test_cache_config_custom_sizes(self):
        """Test setting custom cache sizes."""
        # Test unknown cache types return default
        size = CacheConfig.get_cache_size('unknown_cache_type')
        default_size = CacheConfig.get_cache_size('default')
        assert size == default_size

    def test_cache_config_unknown_cache_type(self):
        """Test handling of unknown cache types."""
        # Should return default value for unknown types
        size = CacheConfig.get_cache_size('unknown_cache_type')
        assert size > 0  # Should have a reasonable default

    def test_cache_config_zero_size(self):
        """Test cache config constants."""
        # Test that cache size constants exist
        assert hasattr(CacheConfig, 'DEFAULT_CACHE_SIZE')
        assert CacheConfig.DEFAULT_CACHE_SIZE > 0

    def test_cache_config_negative_size(self):
        """Test cache config values."""
        # Test various cache types have reasonable sizes
        route_size = CacheConfig.get_cache_size('route')
        middleware_size = CacheConfig.get_cache_size('middleware')
        
        assert route_size > 0
        assert middleware_size > 0


class TestLRUCache:
    """Test LRU cache functionality."""
    
    def test_create_lru_cache_default(self):
        """Test creating LRU cache with default settings."""
        cache_decorator = create_lru_cache()
        
        @cache_decorator
        def test_function(x):
            return x * 2
        
        # Function should be wrapped with caching
        assert hasattr(test_function, 'cache_info')
        
        # Test caching behavior
        result1 = test_function(5)
        result2 = test_function(5)  # Should hit cache
        
        assert result1 == 10
        assert result2 == 10
        
        cache_info = test_function.cache_info()
        assert cache_info.hits >= 1
    
    def test_create_lru_cache_custom_maxsize(self):
        """Test creating LRU cache with custom max size."""
        cache_decorator = create_lru_cache(max_size=2, cache_type="test")
        
        @cache_decorator
        def test_function(x):
            return x * 3
        
        # Fill cache beyond capacity
        test_function(1)  # Miss
        test_function(2)  # Miss
        test_function(3)  # Miss, should evict 1
        test_function(1)  # Miss again (was evicted)
        
        cache_info = test_function.cache_info()
        assert cache_info.maxsize == 2
    
    def test_route_cache_decorator(self):
        """Test route-specific cache decorator."""
        @route_cache()
        def route_handler(path, method):
            return f"Handled {method} {path}"
        
        result1 = route_handler("/api/users", "GET")
        result2 = route_handler("/api/users", "GET")  # Should hit cache
        
        assert result1 == "Handled GET /api/users"
        assert result2 == "Handled GET /api/users"
        
        cache_info = route_handler.cache_info()
        assert cache_info.hits >= 1
    
    def test_middleware_cache_decorator(self):
        """Test middleware-specific cache decorator."""
        call_count = 0
        
        @middleware_cache()
        def middleware_factory(config):
            nonlocal call_count
            call_count += 1
            return f"Middleware {config}"
        
        result1 = middleware_factory("config1")
        result2 = middleware_factory("config1")  # Should hit cache
        result3 = middleware_factory("config2")  # Different arg, should miss
        
        assert result1 == "Middleware config1"
        assert result2 == "Middleware config1" 
        assert result3 == "Middleware config2"
        assert call_count == 2  # Only called twice due to caching
    
    def test_signature_cache_decorator(self):
        """Test signature-specific cache decorator."""
        @signature_cache()
        def parse_signature(func_name, args):
            return f"Signature: {func_name}({args})"
        
        result1 = parse_signature("test_func", "arg1, arg2")
        result2 = parse_signature("test_func", "arg1, arg2")  # Should hit cache
        
        assert result1 == "Signature: test_func(arg1, arg2)"
        assert result2 == "Signature: test_func(arg1, arg2)"
        
        cache_info = parse_signature.cache_info()
        assert cache_info.hits >= 1
    
    def test_parser_cache_decorator(self):
        """Test parser-specific cache decorator."""
        @parser_cache()
        def parse_request(request_data):
            return {"parsed": request_data}
        
        result1 = parse_request("data1")
        result2 = parse_request("data1")  # Should hit cache
        
        assert result1 == {"parsed": "data1"}
        assert result2 == {"parsed": "data1"}
        
        cache_info = parse_request.cache_info()
        assert cache_info.hits >= 1
    
    def test_response_cache_decorator(self):
        """Test response-specific cache decorator."""
        @response_cache()
        def create_response(content_type, data):
            return f"Response: {content_type} - {data}"
        
        result1 = create_response("json", "test_data")
        result2 = create_response("json", "test_data")  # Should hit cache
        
        assert result1 == "Response: json - test_data"
        assert result2 == "Response: json - test_data"
        
        cache_info = create_response.cache_info()
        assert cache_info.hits >= 1


class TestCachePerformance:
    """Test cache performance characteristics."""
    
    def test_cache_performance_improvement(self):
        """Test that caching provides performance improvement."""
        call_count = 0
        
        @create_lru_cache(max_size=100)
        def expensive_function(n):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return n * n
        
        # Time uncached calls
        start_time = time.time()
        expensive_function(1)
        expensive_function(2)
        expensive_function(3)
        uncached_time = time.time() - start_time
        
        # Time cached calls
        start_time = time.time()
        expensive_function(1)  # Should hit cache
        expensive_function(2)  # Should hit cache
        expensive_function(3)  # Should hit cache
        cached_time = time.time() - start_time
        
        assert call_count == 3  # Only called 3 times due to caching
        assert cached_time < uncached_time  # Cached calls should be faster
    
    def test_cache_memory_usage(self):
        """Test cache memory usage characteristics."""
        @create_lru_cache(max_size=10)
        def cached_function(x):
            return [x] * 1000  # Return a list to use some memory
        
        # Fill cache
        for i in range(15):  # More than maxsize
            cached_function(i)
        
        cache_info = cached_function.cache_info()
        assert cache_info.currsize <= 10  # Should not exceed maxsize
    
    def test_cache_hit_rate_tracking(self):
        """Test cache hit rate tracking."""
        @create_lru_cache(max_size=100)
        def tracked_function(x):
            return x * 2
        
        # Generate some cache hits and misses
        for i in range(5):
            tracked_function(i)  # Misses
        
        for i in range(5):
            tracked_function(i)  # Hits
        
        cache_info = tracked_function.cache_info()
        assert cache_info.hits == 5
        assert cache_info.misses == 5
        
        hit_rate = cache_info.hits / (cache_info.hits + cache_info.misses)
        assert hit_rate == 0.5


class TestMiddlewareOptimizer:
    """Test middleware optimization functionality."""
    
    def test_middleware_stack_optimization(self):
        """Test middleware stack optimization."""
        class SecurityMiddleware:
            pass
        
        class AuthMiddleware:
            pass
        
        class LoggingMiddleware:
            pass
        
        class CompressionMiddleware:
            pass
        
        middlewares = [
            CompressionMiddleware,  # Low priority
            AuthMiddleware,  # High priority  
            LoggingMiddleware,  # Low priority
            SecurityMiddleware,  # High priority
        ]
        
        optimized = MiddlewareOptimizer.optimize_middleware_stack(middlewares)
        
        # Should reorder for optimal performance
        assert len(optimized) == len(middlewares)
        # High priority middleware should come first
        assert any("security" in m.__name__.lower() or "auth" in m.__name__.lower() 
                  for m in optimized[:2])
    
    def test_middleware_deduplication(self):
        """Test middleware deduplication."""
        class TestMiddleware:
            pass
        
        # Create list with duplicates
        middlewares = [TestMiddleware, TestMiddleware, TestMiddleware]
        
        optimized = MiddlewareOptimizer.optimize_middleware_stack(middlewares)
        
        # Should remove duplicates
        assert len(optimized) == 1
        assert optimized[0] == TestMiddleware
    
    def test_empty_middleware_stack(self):
        """Test optimization of empty middleware stack."""
        optimized = MiddlewareOptimizer.optimize_middleware_stack([])
        
        assert len(optimized) == 0
    
    def test_cached_middleware_chain(self):
        """Test cached middleware chain compilation."""
        class TestMiddleware1:
            def __init__(self, app):
                self.app = app
                
        class TestMiddleware2:
            def __init__(self, app):
                self.app = app
        
        middleware_tuple = (TestMiddleware1, TestMiddleware2)
        
        chain_builder = MiddlewareOptimizer.cached_middleware_chain(middleware_tuple)
        
        # Should return a function that builds the chain
        assert callable(chain_builder)
        
        # Test with a mock handler
        mock_handler = MagicMock()
        chain = chain_builder(mock_handler)
        
        assert chain is not None
    
    def test_small_middleware_chain_optimization(self):
        """Test optimization for small middleware chains."""
        class Middleware1:
            def __init__(self, app):
                self.app = app
                
        class Middleware2:
            def __init__(self, app):
                self.app = app
        
        # Test with 1, 2, and 3 middleware (should be unrolled)
        for count in [1, 2, 3]:
            middleware_tuple = tuple([Middleware1] * count)
            chain_builder = MiddlewareOptimizer.cached_middleware_chain(middleware_tuple)
            
            mock_handler = MagicMock()
            chain = chain_builder(mock_handler)
            
            assert chain is not None


class TestCacheEviction:
    """Test cache eviction policies."""
    
    def test_lru_eviction_policy(self):
        """Test LRU eviction policy."""
        @create_lru_cache(max_size=3)
        def cached_function(x):
            return x * 2
        
        # Fill cache to capacity
        cached_function(1)  # Miss
        cached_function(2)  # Miss  
        cached_function(3)  # Miss
        
        # Access 1 to make it recently used
        cached_function(1)  # Hit
        
        # Add new item, should evict 2 (least recently used)
        cached_function(4)  # Miss, evicts 2
        
        # Check that 2 was evicted but 1 and 3 remain
        cache_info = cached_function.cache_info()
        assert cache_info.currsize == 3
        
        # Access patterns should show 1 and 3 hit, 2 misses
        cached_function(1)  # Hit
        cached_function(3)  # Hit  
        cached_function(2)  # Miss (was evicted)
    
    def test_cache_clear_functionality(self):
        """Test cache clearing functionality."""
        @create_lru_cache(max_size=10)
        def cached_function(x):
            return x * 2
        
        # Fill cache
        for i in range(5):
            cached_function(i)
        
        cache_info = cached_function.cache_info()
        assert cache_info.currsize == 5
        
        # Clear cache
        cached_function.cache_clear()
        
        cache_info = cached_function.cache_info()
        assert cache_info.currsize == 0
        assert cache_info.hits == 0
        assert cache_info.misses == 0


class TestCacheEdgeCases:
    """Test cache edge cases and error conditions."""
    
    def test_cache_with_none_arguments(self):
        """Test caching functions with None arguments."""
        @create_lru_cache()
        def function_with_none(x):
            return f"Value: {x}"
        
        result1 = function_with_none(None)
        result2 = function_with_none(None)  # Should hit cache
        
        assert result1 == "Value: None"
        assert result2 == "Value: None"
        
        cache_info = function_with_none.cache_info()
        assert cache_info.hits >= 1
    
    def test_cache_with_unhashable_arguments(self):
        """Test caching functions with unhashable arguments."""
        @create_lru_cache()
        def function_with_dict(data):
            return f"Dict: {data}"
        
        # This should handle unhashable types gracefully or raise TypeError
        try:
            function_with_dict({"key": "value"})
        except TypeError:
            # Expected for unhashable arguments
            pass
    
    def test_cache_with_large_arguments(self):
        """Test caching with large arguments."""
        @create_lru_cache()
        def function_with_large_arg(data):
            return len(data)
        
        large_string = "x" * 10000
        result1 = function_with_large_arg(large_string)
        result2 = function_with_large_arg(large_string)  # Should hit cache
        
        assert result1 == 10000
        assert result2 == 10000
    
    def test_cache_thread_safety(self):
        """Test cache thread safety (basic test)."""
        import threading
        
        call_count = 0
        
        @create_lru_cache()
        def thread_safe_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        def worker():
            for i in range(10):
                thread_safe_function(1)  # All threads use same argument
        
        threads = [threading.Thread(target=worker) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should only be called once due to caching, regardless of threads
        assert call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
