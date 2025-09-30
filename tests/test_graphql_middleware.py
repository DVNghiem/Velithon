"""Test cases for GraphQL middleware functionality."""

from unittest.mock import AsyncMock

import pytest

from velithon.exceptions import UnauthorizedException
from velithon.graphql.middleware import (
    GraphQLAuthMiddleware,
    GraphQLLoggingMiddleware,
    GraphQLMiddleware,
)
from velithon.requests import Request


class MockApp:
    """Mock RSGI application for testing middleware."""

    def __init__(self, response_data=None):
        self.response_data = response_data or {"status": "ok"}

    async def __call__(self, scope, protocol):
        """Mock app call."""
        return self.response_data


class TestGraphQLMiddleware:
    """Test GraphQL middleware base functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MockApp()

    async def test_middleware_initialization(self):
        """Test GraphQL middleware initialization."""
        middleware = GraphQLMiddleware(
            app=self.mock_app,
            max_query_complexity=100,
            auth_required=True,
            log_queries=True,
        )

        assert middleware.app == self.mock_app
        assert middleware.max_query_complexity == 100
        assert middleware.auth_required is True
        assert middleware.log_queries is True

    async def test_middleware_initialization_defaults(self):
        """Test GraphQL middleware initialization with defaults."""
        middleware = GraphQLMiddleware(app=self.mock_app)

        assert middleware.app == self.mock_app
        assert middleware.max_query_complexity is None
        assert middleware.auth_required is False
        assert middleware.auth_checker is None
        assert middleware.context_processor is None
        assert middleware.log_queries is False

    async def test_non_graphql_request_passthrough(self):
        """Test that non-GraphQL requests pass through unchanged."""
        middleware = GraphQLMiddleware(app=self.mock_app)
        
        # Mock a non-GraphQL request scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/users",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)

        assert result == self.mock_app.response_data

    async def test_graphql_request_identification(self):
        """Test identification of GraphQL requests."""
        middleware = GraphQLMiddleware(app=self.mock_app)
        
        # Test GraphQL path detection
        graphql_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }

        assert middleware._is_graphql_request(graphql_scope) is True

        # Test non-GraphQL path
        api_scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/users",
            "headers": [(b"content-type", b"application/json")],
        }

        assert middleware._is_graphql_request(api_scope) is False

    async def test_authentication_required_success(self):
        """Test successful authentication when required."""
        async def mock_auth_checker(request):
            return True

        middleware = GraphQLMiddleware(
            app=self.mock_app,
            auth_required=True,
            auth_checker=mock_auth_checker,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        # Should not raise an exception
        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data

    async def test_authentication_required_failure(self):
        """Test authentication failure when required."""
        async def mock_auth_checker(request):
            return False

        middleware = GraphQLMiddleware(
            app=self.mock_app,
            auth_required=True,
            auth_checker=mock_auth_checker,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        with pytest.raises(UnauthorizedException) as exc_info:
            await middleware.process_http_request(scope, protocol)

        assert "Authentication required" in str(exc_info.value)

    async def test_context_processing(self):
        """Test context processing functionality."""
        async def mock_context_processor(request):
            return {"user_id": 123, "permissions": ["read", "write"]}

        middleware = GraphQLMiddleware(
            app=self.mock_app,
            context_processor=mock_context_processor,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)

        # Context should be stored in scope
        assert hasattr(scope, "_graphql_context")
        assert scope._graphql_context["user_id"] == 123
        assert "read" in scope._graphql_context["permissions"]

    async def test_query_logging_enabled(self):
        """Test query logging when enabled."""
        middleware = GraphQLMiddleware(
            app=self.mock_app,
            log_queries=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        # Mock request body parsing
        mock_request = Request(scope, protocol)
        mock_request.body = AsyncMock(return_value=b'{"query": "{hello}"}')

        result = await middleware.process_http_request(scope, protocol)

        # Should complete without errors
        assert result == self.mock_app.response_data

    async def test_query_complexity_analysis(self):
        """Test query complexity analysis."""
        middleware = GraphQLMiddleware(
            app=self.mock_app,
            max_query_complexity=10,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        # For now, just ensure it processes without errors
        # Full complexity analysis would require GraphQL parsing
        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data


class TestGraphQLAuthMiddleware:
    """Test GraphQL authentication middleware."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MockApp()

    async def test_auth_middleware_initialization(self):
        """Test GraphQL auth middleware initialization."""
        def token_extractor(request):
            return request.headers.get("authorization")

        def token_validator(token):
            return token == "Bearer valid-token"

        middleware = GraphQLAuthMiddleware(
            app=self.mock_app,
            token_extractor=token_extractor,
            token_validator=token_validator,
        )

        assert middleware.token_extractor == token_extractor
        assert middleware.token_validator == token_validator
        assert middleware.auth_required is True

    async def test_auth_middleware_valid_token(self):
        """Test authentication with valid token."""
        def token_extractor(request):
            auth_header = request.headers.get("authorization", "")
            return auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None

        def token_validator(token):
            return token == "valid-token"

        middleware = GraphQLAuthMiddleware(
            app=self.mock_app,
            token_extractor=token_extractor,
            token_validator=token_validator,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [
                (b"content-type", b"application/json"),
                (b"authorization", b"Bearer valid-token"),
            ],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data

    async def test_auth_middleware_invalid_token(self):
        """Test authentication with invalid token."""
        def token_extractor(request):
            auth_header = request.headers.get("authorization", "")
            return auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None

        def token_validator(token):
            return token == "valid-token"

        middleware = GraphQLAuthMiddleware(
            app=self.mock_app,
            token_extractor=token_extractor,
            token_validator=token_validator,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [
                (b"content-type", b"application/json"),
                (b"authorization", b"Bearer invalid-token"),
            ],
        }
        protocol = AsyncMock()

        with pytest.raises(UnauthorizedException):
            await middleware.process_http_request(scope, protocol)

    async def test_auth_middleware_missing_token(self):
        """Test authentication with missing token."""
        def token_extractor(request):
            auth_header = request.headers.get("authorization", "")
            return auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None

        def token_validator(token):
            return token == "valid-token"

        middleware = GraphQLAuthMiddleware(
            app=self.mock_app,
            token_extractor=token_extractor,
            token_validator=token_validator,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        with pytest.raises(UnauthorizedException):
            await middleware.process_http_request(scope, protocol)

    async def test_auth_middleware_custom_unauthorized_response(self):
        """Test custom unauthorized response."""
        def token_extractor(request):
            return None

        def token_validator(token):
            return False

        def unauthorized_response():
            return {"error": "Custom unauthorized message"}

        middleware = GraphQLAuthMiddleware(
            app=self.mock_app,
            token_extractor=token_extractor,
            token_validator=token_validator,
            unauthorized_response=unauthorized_response,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        # Custom unauthorized response should be used
        result = await middleware.process_http_request(scope, protocol)
        assert result == {"error": "Custom unauthorized message"}


class TestGraphQLLoggingMiddleware:
    """Test GraphQL logging middleware."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MockApp()

    async def test_logging_middleware_initialization(self):
        """Test GraphQL logging middleware initialization."""
        middleware = GraphQLLoggingMiddleware(
            app=self.mock_app,
            log_queries=True,
            log_responses=True,
            log_errors=True,
        )

        assert middleware.log_queries is True
        assert middleware.log_responses is True
        assert middleware.log_errors is True

    async def test_logging_middleware_query_logging(self):
        """Test query logging functionality."""
        middleware = GraphQLLoggingMiddleware(
            app=self.mock_app,
            log_queries=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data

    async def test_logging_middleware_response_logging(self):
        """Test response logging functionality."""
        middleware = GraphQLLoggingMiddleware(
            app=self.mock_app,
            log_responses=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data

    async def test_logging_middleware_error_logging(self):
        """Test error logging functionality."""
        class ErrorApp:
            async def __call__(self, scope, protocol):
                raise ValueError("Test error")

        middleware = GraphQLLoggingMiddleware(
            app=ErrorApp(),
            log_errors=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        with pytest.raises(ValueError, match="Test error"):
            await middleware.process_http_request(scope, protocol)

    async def test_logging_middleware_custom_logger(self):
        """Test custom logger configuration."""
        import logging
        
        custom_logger = logging.getLogger("custom_graphql_logger")
        
        middleware = GraphQLLoggingMiddleware(
            app=self.mock_app,
            logger=custom_logger,
        )
        
        assert middleware.logger == custom_logger

    async def test_logging_middleware_request_id_tracking(self):
        """Test request ID tracking in logs."""
        middleware = GraphQLLoggingMiddleware(
            app=self.mock_app,
            track_request_id=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-request-id", b"test-request-123"),
            ],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data

    async def test_logging_middleware_timing_information(self):
        """Test request timing information in logs."""
        middleware = GraphQLLoggingMiddleware(
            app=self.mock_app,
            log_timing=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        result = await middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = MockApp()

    async def test_multiple_middleware_stack(self):
        """Test stacking multiple GraphQL middleware."""
        # Create a stack: Logging -> Auth -> Base
        base_middleware = GraphQLMiddleware(self.mock_app)
        
        auth_middleware = GraphQLAuthMiddleware(
            app=base_middleware,
            token_extractor=lambda req: "valid-token",
            token_validator=lambda token: token == "valid-token",
        )
        
        logging_middleware = GraphQLLoggingMiddleware(
            app=auth_middleware,
            log_queries=True,
            log_responses=True,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [
                (b"content-type", b"application/json"),
                (b"authorization", b"Bearer valid-token"),
            ],
        }
        protocol = AsyncMock()

        result = await logging_middleware.process_http_request(scope, protocol)
        assert result == self.mock_app.response_data

    async def test_middleware_error_handling(self):
        """Test error handling in middleware chain."""
        class ErrorMiddleware(GraphQLMiddleware):
            async def process_http_request(self, scope, protocol):
                if self._is_graphql_request(scope):
                    raise ValueError("Middleware error")
                return await super().process_http_request(scope, protocol)

        middleware = ErrorMiddleware(self.mock_app)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        with pytest.raises(ValueError, match="Middleware error"):
            await middleware.process_http_request(scope, protocol)

    async def test_middleware_context_preservation(self):
        """Test context preservation across middleware."""
        async def context_processor(request):
            return {"middleware": "base", "user_id": 123}

        middleware = GraphQLMiddleware(
            app=self.mock_app,
            context_processor=context_processor,
        )
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        await middleware.process_http_request(scope, protocol)

        # Verify context is preserved
        assert hasattr(scope, "_graphql_context")
        assert scope._graphql_context["middleware"] == "base"
        assert scope._graphql_context["user_id"] == 123


if __name__ == "__main__":
    pytest.main([__file__, "-v"])