"""Tests for rate limiting middleware."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from velithon.datastructures import Headers, Protocol, Scope
from velithon.middleware.rate_limit import (
    RateLimitMiddleware,
    get_endpoint_key,
    get_ip_key,
    get_user_key,
)
from velithon.middleware.rate_limit_algorithms import (
    FixedWindowAlgorithm,
    SimpleTokenBucketAlgorithm,
    SlidingWindowAlgorithm,
)
from velithon.middleware.rate_limit_storage import (
    InMemoryRateLimitStorage,
    RedisRateLimitStorage,
)
from velithon.requests import Request


class TestRateLimitStorage:
    """Tests for storage backends."""

    @pytest.mark.asyncio
    async def test_in_memory_storage(self):
        """Test in-memory storage operations."""
        storage = InMemoryRateLimitStorage()
        key = "test_key"
        window = 1

        # Test increment
        count, ttl = await storage.increment(key, window)
        assert count == 1
        assert 0 < ttl <= window

        # Test increment again
        count, ttl = await storage.increment(key, window)
        assert count == 2

        # Test get
        assert await storage.get(key) == 2

        # Test reset
        await storage.reset(key)
        assert await storage.get(key) == 0

        # Test expiration
        await storage.increment(key, window)
        await asyncio.sleep(1.1)
        assert await storage.get(key) == 0
        
        await storage.close()

    @pytest.mark.asyncio
    async def test_redis_storage_mock(self):
        """Test Redis storage with mocked redis client."""
        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis
            
            # Setup pipeline mock
            mock_pipeline = MagicMock()
            mock_redis.pipeline.return_value = mock_pipeline
            mock_pipeline.execute = AsyncMock(return_value=[1, 60])
            
            storage = RedisRateLimitStorage("redis://localhost")
            
            # Test increment
            count, ttl = await storage.increment("key", 60)
            assert count == 1
            assert ttl == 60
            
            # Verify redis calls
            mock_redis.pipeline.assert_called()
            mock_pipeline.incr.assert_called_with("ratelimit:key")
            mock_pipeline.ttl.assert_called_with("ratelimit:key")
            
            # Test get
            mock_redis.get.return_value = "5"
            assert await storage.get("key") == 5
            
            # Test reset
            await storage.reset("key")
            mock_redis.delete.assert_called_with("ratelimit:key")


class TestRateLimitAlgorithms:
    """Tests for rate limiting algorithms."""

    @pytest.mark.asyncio
    async def test_fixed_window(self):
        """Test fixed window algorithm."""
        storage = InMemoryRateLimitStorage()
        algo = FixedWindowAlgorithm()
        key = "fixed"
        limit = 2
        window = 60

        # First request
        allowed, info = await algo.is_allowed(storage, key, limit, window)
        assert allowed is True
        assert info["remaining"] == 1

        # Second request
        allowed, info = await algo.is_allowed(storage, key, limit, window)
        assert allowed is True
        assert info["remaining"] == 0

        # Third request (blocked)
        allowed, info = await algo.is_allowed(storage, key, limit, window)
        assert allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] is not None
        
        await storage.close()

    @pytest.mark.asyncio
    async def test_token_bucket(self):
        """Test token bucket algorithm."""
        storage = InMemoryRateLimitStorage()
        algo = SimpleTokenBucketAlgorithm()
        key = "bucket"
        limit = 10
        window = 60

        # Should allow burst up to limit + 20%
        # But for simple test, just check basic allowance
        allowed, info = await algo.is_allowed(storage, key, limit, window)
        assert allowed is True
        
        await storage.close()


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    @pytest.fixture
    def app(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_middleware_allow(self, app):
        """Test middleware allowing requests."""
        middleware = RateLimitMiddleware(app, limit=10, window=60)
        
        scope = MagicMock()
        scope.proto = "http"
        scope.headers = Headers()
        scope.path = "/"
        # Mock client address for get_ip_key
        scope.client = ("127.0.0.1", 12345)
        
        protocol = MagicMock()
        protocol.update_headers = MagicMock()

        # Process request
        should_continue = await middleware.should_process_request(scope, protocol)
        
        assert should_continue is True
        protocol.update_headers.assert_called()
        
        # Check headers
        headers = dict(protocol.update_headers.call_args[0][0])
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers

    @pytest.mark.asyncio
    async def test_middleware_block(self, app):
        """Test middleware blocking requests."""
        # Limit 1 request
        middleware = RateLimitMiddleware(app, limit=1, window=60)
        
        scope = MagicMock()
        scope.proto = "http"
        scope.headers = Headers()
        scope.path = "/"
        scope.client = ("127.0.0.1", 12345)
        
        protocol = MagicMock()
        protocol.update_headers = MagicMock()
        
        # First request allowed
        assert await middleware.should_process_request(scope, protocol) is True
        
        # Second request blocked
        # We need to mock response callable since middleware calls it
        with patch("velithon.middleware.rate_limit.JSONResponse") as mock_response:
            mock_resp_instance = AsyncMock()
            mock_response.return_value = mock_resp_instance
            
            should_continue = await middleware.should_process_request(scope, protocol)
            
            assert should_continue is False
            mock_resp_instance.assert_called_with(scope, protocol)
            
            # Check 429 status
            call_kwargs = mock_response.call_args[1]
            assert call_kwargs["status_code"] == 429

    def test_key_extractors(self):
        """Test key extraction functions."""
        # Test IP extractor
        request = MagicMock()
        request.headers = Headers()
        request.scope.client = ("1.2.3.4", 123)
        assert get_ip_key(request) == "1.2.3.4"
        
        # Test X-Forwarded-For
        request.headers = Headers([("x-forwarded-for", "10.0.0.1, 1.2.3.4")])
        assert get_ip_key(request) == "10.0.0.1"
        
        # Test User extractor
        request.state.user = MagicMock()
        request.state.user.id = "user123"
        assert get_user_key(request) == "user:user123"
        
        # Test Endpoint extractor
        request.scope.path = "/api/test"
        request.headers = Headers()
        request.scope.client = ("1.2.3.4", 123)
        assert get_endpoint_key(request) == "1.2.3.4:/api/test"
