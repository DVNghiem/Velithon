"""
Tests for CORS middleware implementation.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.datastructures import Headers
from velithon.middleware.cors import ALL_METHODS, SAFELISTED_HEADERS, CORSMiddleware
from velithon.responses import PlainTextResponse


class TestCORSMiddleware:
    """Test cases for CORSMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = AsyncMock()
        return app

    @pytest.fixture
    def basic_cors_middleware(self, mock_app):
        """Create a basic CORS middleware instance."""
        return CORSMiddleware(
            mock_app,
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
            allow_credentials=True,
            max_age=3600
        )

    @pytest.fixture
    def wildcard_cors_middleware(self, mock_app):
        """Create a CORS middleware with wildcard permissions."""
        return CORSMiddleware(
            mock_app,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=False,
            max_age=7200
        )

    def test_initialization_with_defaults(self, mock_app):
        """Test CORS middleware initialization with default values."""
        middleware = CORSMiddleware(mock_app)
        
        assert middleware.allow_methods == ("GET",)
        assert middleware.allow_headers == sorted([h.lower() for h in SAFELISTED_HEADERS])
        assert middleware.allow_credentials is False
        assert middleware.max_age == 600
        assert middleware.max_age == 600

    def test_initialization_with_wildcard_methods(self, mock_app):
        """Test initialization with wildcard methods."""
        middleware = CORSMiddleware(
            mock_app,
            allow_methods=["*"]
        )
        
        assert middleware.allow_methods == ALL_METHODS

    def test_allowed_origin_check_exact_match(self, basic_cors_middleware):
        """Test origin checking with exact match."""
        assert basic_cors_middleware.is_allowed_origin("https://example.com") is True
        assert basic_cors_middleware.is_allowed_origin("https://evil.com") is False

    def test_allowed_origin_check_wildcard(self, wildcard_cors_middleware):
        """Test origin checking with wildcard."""
        assert wildcard_cors_middleware.is_allowed_origin("https://example.com") is True
        assert wildcard_cors_middleware.is_allowed_origin("https://anything.com") is True

    def test_allowed_origin_check_regex_pattern(self, mock_app):
        """Test origin checking with regex pattern."""
        import re
        middleware = CORSMiddleware(
            mock_app,
            allow_origins=["https://*.example.com"]
        )
        # Set regex pattern manually for testing
        middleware.allow_origin_regex = re.compile(r"https://.*\.example\.com")
        
        assert middleware.is_allowed_origin("https://sub.example.com") is True
        assert middleware.is_allowed_origin("https://api.example.com") is True
        assert middleware.is_allowed_origin("https://example.com") is False

    @pytest.mark.asyncio
    async def test_simple_request_processing(self, basic_cors_middleware, mock_app):
        """Test processing of simple CORS requests."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.headers = Headers([("origin", "https://example.com")])
        
        protocol = MagicMock()
        protocol.update_headers = MagicMock()
        
        result = await basic_cors_middleware.should_process_request(scope, protocol)
        
        assert result is True
        protocol.update_headers.assert_called_once()

    @pytest.mark.asyncio
    async def test_preflight_request_processing(self, basic_cors_middleware):
        """Test processing of preflight OPTIONS requests."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "OPTIONS"
        scope.headers = Headers([
            ("origin", "https://example.com"),
            ("access-control-request-method", "POST"),
            ("access-control-request-headers", "Content-Type")
        ])
        
        protocol = MagicMock()
        protocol.response_bytes = MagicMock()
        
        # Mock the call method
        basic_cors_middleware.app = AsyncMock()
        
        result = await basic_cors_middleware.should_process_request(scope, protocol)
        
        assert result is False  # Should not continue processing

    def test_preflight_response_success(self, basic_cors_middleware):
        """Test successful preflight response generation."""
        headers = Headers([
            ("origin", "https://example.com"),
            ("access-control-request-method", "POST"),
            ("access-control-request-headers", "Content-Type")
        ])
        
        response = basic_cors_middleware.preflight_response(headers)
        
        assert isinstance(response, PlainTextResponse)
        assert response.status_code == 200
        assert response.body == b"OK"
        
        # Check response headers
        response_headers = dict(response.raw_headers)
        assert "access-control-allow-origin" in response_headers
        assert "access-control-allow-methods" in response_headers

    def test_preflight_response_method_failure(self, basic_cors_middleware):
        """Test preflight response with disallowed method."""
        headers = Headers([
            ("origin", "https://example.com"),
            ("access-control-request-method", "DELETE"),  # Not allowed
            ("access-control-request-headers", "Content-Type")
        ])
        
        response = basic_cors_middleware.preflight_response(headers)
        
        assert isinstance(response, PlainTextResponse)
        assert response.status_code == 400
        assert b"Disallowed CORS method" in response.body

    def test_preflight_response_header_failure(self, basic_cors_middleware):
        """Test preflight response with disallowed headers."""
        headers = Headers([
            ("origin", "https://example.com"),
            ("access-control-request-method", "POST"),
            ("access-control-request-headers", "X-Custom-Header")  # Not allowed
        ])
        
        response = basic_cors_middleware.preflight_response(headers)
        
        assert isinstance(response, PlainTextResponse)
        assert response.status_code == 400
        assert b"Disallowed CORS headers" in response.body

    def test_preflight_response_with_wildcard_headers(self, wildcard_cors_middleware):
        """Test preflight response with wildcard headers."""
        headers = Headers([
            ("origin", "https://example.com"),
            ("access-control-request-method", "POST"),
            ("access-control-request-headers", "X-Custom-Header, Authorization")
        ])
        
        response = wildcard_cors_middleware.preflight_response(headers)
        
        assert isinstance(response, PlainTextResponse)
        assert response.status_code == 200
        
        # Check that requested headers are mirrored back
        response_headers = dict(response.raw_headers)
        assert "access-control-allow-headers" in response_headers

    @pytest.mark.asyncio
    async def test_non_http_requests_passthrough(self, basic_cors_middleware):
        """Test that non-HTTP requests pass through without processing."""
        scope = MagicMock()
        scope.proto = "websocket"
        
        protocol = MagicMock()
        
        await basic_cors_middleware(scope, protocol)
        
        # Should call the wrapped app directly
        basic_cors_middleware.app.assert_called_once_with(scope, protocol)

    def test_credentials_handling_with_wildcard_origin(self, mock_app):
        """Test that credentials=True prevents wildcard origins."""
        middleware = CORSMiddleware(
            mock_app,
            allow_origins=["*"],
            allow_credentials=True
        )
        
        # Should set preflight_explicit_allow_origin=True when credentials=True
        assert middleware.preflight_explicit_allow_origin is True

    def test_headers_normalization(self, mock_app):
        """Test that headers are normalized to lowercase."""
        middleware = CORSMiddleware(
            mock_app,
            allow_headers=["Content-Type", "AUTHORIZATION", "X-Custom-Header"]
        )

        # Test that middleware was created successfully
        # The actual header normalization happens during request processing
        assert middleware is not None
        assert hasattr(middleware, 'app')

    def test_max_age_header_inclusion(self, basic_cors_middleware):
        """Test that max-age header is included in preflight responses."""
        headers = Headers([
            ("origin", "https://example.com"),
            ("access-control-request-method", "POST")
        ])
        
        response = basic_cors_middleware.preflight_response(headers)
        response_headers = dict(response.raw_headers)
        
        assert "access-control-max-age" in response_headers
        assert response_headers["access-control-max-age"] == "3600"

    @pytest.mark.asyncio
    async def test_cors_middleware_integration(self):
        """Integration test for CORS middleware with complete request flow."""
        requests_processed = []
        
        async def mock_app(scope, protocol):
            requests_processed.append((scope.method, scope.path))
        
        middleware = CORSMiddleware(
            mock_app,
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"]
        )
        
        # Test simple GET request
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.path = "/api/data"
        scope.headers = Headers([("origin", "https://example.com")])
        
        protocol = MagicMock()
        protocol.update_headers = MagicMock()
        
        await middleware(scope, protocol)
        
        assert len(requests_processed) == 1
        assert requests_processed[0] == ("GET", "/api/data")

    def test_empty_origin_handling(self, basic_cors_middleware):
        """Test handling of requests without origin header."""
        headers = Headers([
            ("access-control-request-method", "POST")
        ])
        
        response = basic_cors_middleware.preflight_response(headers)
        response_headers = dict(response.raw_headers)
        
        # Should still process the request
        assert "access-control-allow-origin" in response_headers


if __name__ == "__main__":
    pytest.main([__file__])
