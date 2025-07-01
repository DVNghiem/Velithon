"""
Tests for Velithon authentication middleware.
"""
import pytest
from unittest.mock import AsyncMock, Mock

from velithon.middleware.auth import AuthenticationMiddleware, SecurityMiddleware
from velithon.security import AuthenticationError, AuthorizationError
from velithon.responses import JSONResponse


class MockHeaders:
    """Mock headers object that behaves like a dictionary."""
    def __init__(self, headers_list=None):
        # Convert list of tuples to dictionary
        self._headers = {}
        if headers_list:
            for key, value in headers_list:
                if isinstance(key, bytes):
                    key = key.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                self._headers[key.lower()] = value

    def get(self, key, default=""):
        return self._headers.get(key.lower(), default)

    def __getitem__(self, key):
        return self._headers[key.lower()]

    def __setitem__(self, key, value):
        self._headers[key.lower()] = value

    def __contains__(self, key):
        return key.lower() in self._headers

    def items(self):
        return self._headers.items()

    def keys(self):
        return self._headers.keys()

    def values(self):
        return self._headers.values()


class MockRSGIScope:
    """Mock RSGI scope for testing."""
    def __init__(
        self,
        proto="http",
        method="GET",
        path="/",
        headers=None,
        query_string=b"",
        server=None,
        scheme="http",
        client=None,
        authority=None
    ):
        self.proto = proto
        self.method = method
        self.path = path
        self.headers = MockHeaders(headers or [])
        self.query_string = query_string
        self.server = server or ("localhost", 8000)
        self.scheme = scheme
        self.rsgi_version = "2.0"
        self.http_version = "1.1"
        self.client = client or ("127.0.0.1", 0)
        self.authority = authority or "localhost:8000"


class TestAuthenticationMiddleware:
    """Test authentication middleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock RSGI app."""
        app = AsyncMock()
        app.return_value = None
        return app
    
    @pytest.fixture
    def auth_middleware(self, mock_app):
        """Create authentication middleware."""
        return AuthenticationMiddleware(mock_app)
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_success(self, auth_middleware, mock_app):
        """Test authentication middleware with successful request."""
        scope = MockRSGIScope(
            proto="http",
            method="GET",
            path="/test",
            headers=[]
        )
        
        protocol = AsyncMock()
        
        # Call middleware
        await auth_middleware(scope, protocol)
        
        # Verify the original app was called
        mock_app.assert_called_once_with(scope, protocol)

    @pytest.mark.asyncio
    async def test_authentication_middleware_handles_auth_error(self, mock_app):
        """Test that authentication middleware handles authentication errors."""
        # Make the app raise an authentication error
        mock_app.side_effect = AuthenticationError("Invalid token")

        middleware = AuthenticationMiddleware(mock_app)

        scope = MockRSGIScope(
            proto="http",
            method="GET",
            path="/protected",
            headers=[]
        )

        protocol = AsyncMock()
        
        # Call middleware
        await middleware(scope, protocol)

        # Check that protocol.response_bytes was called with 401 status
        protocol.response_bytes.assert_called_once()
        args = protocol.response_bytes.call_args[0]
        status = args[0]
        assert status == 401
    
    @pytest.mark.asyncio
    async def test_authentication_middleware_handles_auth_z_error(self, mock_app):
        """Test that authentication middleware handles authorization errors."""
        # Make the app raise an authorization error
        mock_app.side_effect = AuthorizationError("Access denied")
        
        middleware = AuthenticationMiddleware(mock_app)
        
        scope = MockRSGIScope(
            proto="http",
            method="GET",
            path="/admin",
            headers=[]
        )
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call middleware
        await middleware(scope, protocol)
        
        # Check that a 403 response was sent
        assert len(messages) >= 2
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 403


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock RSGI app that returns a response."""
        async def app(scope, protocol):
            # Simulate a successful response
            await protocol.send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"application/json"]
                ]
            })
            await protocol.send({
                "type": "http.response.body",
                "body": b'{"message": "test"}',
                "more_body": False
            })
        
        return app
    
    @pytest.fixture
    def security_middleware(self, mock_app):
        """Create security middleware."""
        return SecurityMiddleware(mock_app)
    
    @pytest.mark.asyncio
    async def test_security_middleware_adds_headers(self, security_middleware):
        """Test that security middleware adds security headers."""
        scope = MockRSGIScope(
            proto="http",
            method="GET",
            path="/test",
            headers=[]
        )
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call middleware
        await security_middleware(scope, protocol)
        
        # Check that security headers were added
        assert len(messages) >= 2
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        
        headers = dict(start_message["headers"])
        
        # Check for security headers
        expected_headers = [
            b"x-content-type-options",
            b"x-frame-options", 
            b"x-xss-protection"
        ]
        
        for header in expected_headers:
            assert header in headers
    
    @pytest.mark.asyncio
    async def test_security_middleware_preserves_existing_headers(self, mock_app):
        """Test that security middleware preserves existing headers."""
        # Create middleware
        middleware = SecurityMiddleware(mock_app)
        
        scope = MockRSGIScope(
            proto="http",
            method="GET",
            path="/test",
            headers=[]
        )
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call middleware
        await middleware(scope, protocol)
        
        # Check that both original and security headers are present
        assert len(messages) >= 2
        start_message = messages[0]
        headers = dict(start_message["headers"])
        
        # Original header should be preserved
        assert b"content-type" in headers
        assert headers[b"content-type"] == b"application/json"
        
        # Security headers should be added
        assert b"x-content-type-options" in headers


if __name__ == "__main__":
    pytest.main([__file__])
