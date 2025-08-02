"""
Tests for Velithon authentication middleware.
"""

from unittest.mock import AsyncMock

import pytest

from velithon.middleware.auth import AuthenticationMiddleware, SecurityMiddleware
from velithon.security import AuthenticationError, AuthorizationError


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

    def get(self, key, default=''):
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
        proto='http',
        method='GET',
        path='/',
        headers=None,
        query_string=b'',
        server=None,
        scheme='http',
        client=None,
        authority=None,
    ):
        self.proto = proto
        self.method = method
        self.path = path
        self.headers = MockHeaders(headers or [])
        self.query_string = query_string
        self.server = server or ('localhost', 8000)
        self.scheme = scheme
        self.rsgi_version = '2.0'
        self.http_version = '1.1'
        self.client = client or ('127.0.0.1', 0)
        self.authority = authority or 'localhost:8000'


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
        scope = MockRSGIScope(proto='http', method='GET', path='/test', headers=[])

        protocol = AsyncMock()

        # Call middleware
        await auth_middleware(scope, protocol)

        # Verify the original app was called
        mock_app.assert_called_once_with(scope, protocol)

    @pytest.mark.asyncio
    async def test_authentication_middleware_handles_auth_error(self, mock_app):
        """Test that authentication middleware handles authentication errors."""
        # Make the app raise an authentication error
        mock_app.side_effect = AuthenticationError('Invalid token')

        middleware = AuthenticationMiddleware(mock_app)

        scope = MockRSGIScope(proto='http', method='GET', path='/protected', headers=[])

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
        mock_app.side_effect = AuthorizationError('Access denied')

        middleware = AuthenticationMiddleware(mock_app)

        scope = MockRSGIScope(proto='http', method='GET', path='/admin', headers=[])

        protocol = AsyncMock()

        # Call middleware
        await middleware(scope, protocol)

        # Check that protocol.response_bytes was called with 403 status
        protocol.response_bytes.assert_called_once()
        args = protocol.response_bytes.call_args[0]
        status = args[0]
        assert status == 403


if __name__ == '__main__':
    pytest.main([__file__])
