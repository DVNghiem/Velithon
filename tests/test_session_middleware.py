"""
Tests for session middleware implementation.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.middleware.session import (
    MemorySessionInterface,
    Session,
    SessionMiddleware,
    SessionProtocol,
    SignedCookieSessionInterface,
    get_session,
)
from velithon.requests import Request
from velithon.responses import JSONResponse


class TestSession:
    """Test cases for Session class."""
    
    def test_session_initialization(self):
        """Test session initialization."""
        # Empty session
        session = Session()
        assert dict(session) == {}
        assert session.modified is False
        assert session.is_new is True
        
        # Session with data
        session = Session({"user_id": 123})
        assert dict(session) == {"user_id": 123}
        assert session.modified is False
        assert session.is_new is False
    
    def test_session_modification_tracking(self):
        """Test that session tracks modifications."""
        session = Session({"user_id": 123})
        assert session.modified is False
        
        # Test __setitem__
        session["name"] = "John"
        assert session.modified is True
        
        session._modified = False
        
        # Test __delitem__
        del session["user_id"]
        assert session.modified is True
        
        session._modified = False
        
        # Test clear
        session.clear()
        assert session.modified is True
        
        session._modified = False
        session["test"] = "value"
        
        # Test pop
        session.pop("test")
        assert session.modified is True
        
        session._modified = False
        session.update({"new": "data"})
        assert session.modified is True
        
        session._modified = False
        
        # Test setdefault with existing key
        session.setdefault("new", "other")
        assert session.modified is False
        
        # Test setdefault with new key
        session.setdefault("newer", "value")
        assert session.modified is True


class TestMemorySessionInterface:
    """Test cases for MemorySessionInterface."""
    
    @pytest.fixture
    def memory_interface(self):
        return MemorySessionInterface(max_age=3600)
    
    @pytest.mark.asyncio
    async def test_load_empty_session(self, memory_interface):
        """Test loading non-existent session."""
        result = await memory_interface.load_session(None)
        assert result == {}
        
        result = await memory_interface.load_session("nonexistent")
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, memory_interface):
        """Test saving and loading session data."""
        session_id = memory_interface.generate_session_id()
        session_data = {"user_id": 123, "name": "John"}
        
        await memory_interface.save_session(session_id, session_data)
        loaded_data = await memory_interface.load_session(session_id)
        
        assert loaded_data == session_data
    
    @pytest.mark.asyncio
    async def test_delete_session(self, memory_interface):
        """Test deleting session data."""
        session_id = memory_interface.generate_session_id()
        session_data = {"user_id": 123}
        
        await memory_interface.save_session(session_id, session_data)
        await memory_interface.delete_session(session_id)
        
        loaded_data = await memory_interface.load_session(session_id)
        assert loaded_data == {}
    
    @pytest.mark.asyncio
    async def test_session_expiration(self, memory_interface):
        """Test that sessions expire after max_age."""
        # Create interface with very short expiration
        short_interface = MemorySessionInterface(max_age=0)
        
        session_id = short_interface.generate_session_id()
        session_data = {"user_id": 123}
        
        await short_interface.save_session(session_id, session_data)
        
        # Wait a bit to ensure expiration
        await asyncio.sleep(0.1)
        
        loaded_data = await short_interface.load_session(session_id)
        assert loaded_data == {}
    
    def test_generate_session_id(self, memory_interface):
        """Test session ID generation."""
        session_id = memory_interface.generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        
        # IDs should be unique
        session_id2 = memory_interface.generate_session_id()
        assert session_id != session_id2


class TestSignedCookieSessionInterface:
    """Test cases for SignedCookieSessionInterface."""
    
    @pytest.fixture
    def cookie_interface(self):
        return SignedCookieSessionInterface("test-secret-key", max_age=3600)
    
    def test_initialization_requires_secret(self):
        """Test that initialization requires a secret key."""
        with pytest.raises(ValueError):
            SignedCookieSessionInterface("")
        
        with pytest.raises(ValueError):
            SignedCookieSessionInterface(None)
    
    def test_sign_and_unsign_data(self, cookie_interface):
        """Test data signing and verification."""
        data = "test-data"
        signed = cookie_interface._sign_data(data)
        
        assert signed != data
        assert "." in signed
        
        unsigned = cookie_interface._unsign_data(signed)
        assert unsigned == data
    
    def test_unsign_invalid_data(self, cookie_interface):
        """Test unsigning invalid data."""
        assert cookie_interface._unsign_data("invalid") is None
        assert cookie_interface._unsign_data("invalid.signature") is None
        assert cookie_interface._unsign_data("") is None
    
    def test_encode_and_decode_session(self, cookie_interface):
        """Test session encoding and decoding."""
        session_data = {"user_id": 123, "name": "John"}
        
        encoded = cookie_interface._encode_session(session_data)
        assert isinstance(encoded, str)
        
        decoded = cookie_interface._decode_session(encoded)
        assert decoded == session_data
    
    def test_decode_invalid_session(self, cookie_interface):
        """Test decoding invalid session data."""
        assert cookie_interface._decode_session("invalid") == {}
        assert cookie_interface._decode_session("") == {}
    
    def test_decode_expired_session(self, cookie_interface):
        """Test decoding expired session."""
        # Create interface with very short expiration
        short_interface = SignedCookieSessionInterface("test-secret", max_age=0)
        
        session_data = {"user_id": 123}
        encoded = short_interface._encode_session(session_data)
        
        # Decode should return empty dict for expired session
        decoded = short_interface._decode_session(encoded)
        assert decoded == {}
    
    @pytest.mark.asyncio
    async def test_load_session_with_cookie_data(self, cookie_interface):
        """Test loading session from cookie data."""
        session_data = {"user_id": 123}
        encoded = cookie_interface._encode_session(session_data)
        
        loaded = await cookie_interface.load_session(encoded)
        assert loaded == session_data
        
        # Test with None
        loaded = await cookie_interface.load_session(None)
        assert loaded == {}


class TestSessionProtocol:
    """Test cases for SessionProtocol."""
    
    @pytest.fixture
    def mock_protocol(self):
        protocol = MagicMock()
        protocol.response_bytes = MagicMock()
        protocol.response_start = AsyncMock()
        return protocol
    
    @pytest.fixture
    def mock_middleware(self):
        middleware = MagicMock()
        middleware._set_session_cookie = MagicMock()
        return middleware
    
    @pytest.fixture
    def session_protocol(self, mock_protocol, mock_middleware):
        session = Session({"user_id": 123})
        return SessionProtocol(mock_protocol, session, mock_middleware)
    
    def test_getattr_delegation(self, session_protocol, mock_protocol):
        """Test that unknown attributes are delegated to wrapped protocol."""
        mock_protocol.custom_method = MagicMock(return_value="test")
        
        result = session_protocol.custom_method()
        
        assert result == "test"
        mock_protocol.custom_method.assert_called_once()
    
    def test_response_bytes_sets_session_cookie(self, session_protocol, mock_protocol, mock_middleware):
        """Test that response_bytes sets session cookie when session is modified."""
        session_protocol.session._modified = True
        
        headers = [("content-type", "application/json")]
        session_protocol.response_bytes(200, headers, b'{"test": "data"}')
        
        mock_middleware._set_session_cookie.assert_called_once()
        mock_protocol.response_bytes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_response_start_sets_session_cookie(self, session_protocol, mock_protocol, mock_middleware):
        """Test that response_start sets session cookie when session is modified."""
        session_protocol.session._modified = True
        
        headers = [("content-type", "application/json")]
        await session_protocol.response_start(200, headers)
        
        mock_middleware._set_session_cookie.assert_called_once()
        mock_protocol.response_start.assert_called_once()
    
    def test_response_sent_only_once(self, session_protocol, mock_protocol, mock_middleware):
        """Test that session cookie is only set once per response."""
        session_protocol.session._modified = True
        
        headers = [("content-type", "application/json")]
        
        # Call response_bytes twice
        session_protocol.response_bytes(200, headers, b'{"test": "data"}')
        session_protocol.response_bytes(200, headers, b'{"test": "data2"}')
        
        # Should only set cookie once
        assert mock_middleware._set_session_cookie.call_count == 1


class TestSessionMiddleware:
    """Test cases for SessionMiddleware."""
    
    @pytest.fixture
    def mock_app(self):
        app = AsyncMock()
        return app
    
    @pytest.fixture
    def mock_scope(self):
        scope = MagicMock()
        scope.proto = "http"
        scope.headers = {"cookie": "velithon_session=test_session_id"}
        return scope
    
    @pytest.fixture
    def mock_protocol(self):
        return MagicMock()
    
    @pytest.fixture
    def session_middleware(self, mock_app):
        return SessionMiddleware(mock_app, secret_key="test-secret-key")
    
    @pytest.mark.asyncio
    async def test_non_http_requests_passthrough(self, session_middleware, mock_app, mock_protocol):
        """Test that non-HTTP requests pass through without session processing."""
        scope = MagicMock()
        scope.proto = "websocket"
        
        await session_middleware(scope, mock_protocol)
        
        mock_app.assert_called_once_with(scope, mock_protocol)
    
    @pytest.mark.asyncio
    async def test_session_loading_and_scope_attachment(self, session_middleware, mock_app, mock_scope, mock_protocol):
        """Test that session is loaded and attached to scope."""
        await session_middleware(mock_scope, mock_protocol)
        
        # Check that session was attached to scope
        assert hasattr(mock_scope, '_session')
        assert isinstance(mock_scope._session, Session)
        
        # Check that app was called with wrapped protocol
        mock_app.assert_called_once()
        call_args = mock_app.call_args
        assert call_args[0][0] == mock_scope
        # The protocol should be wrapped
        wrapped_protocol = call_args[0][1]
        assert wrapped_protocol != mock_protocol
        assert hasattr(wrapped_protocol, 'protocol')
    
    def test_initialization_with_memory_interface(self, mock_app):
        """Test initialization with memory session interface."""
        middleware = SessionMiddleware(mock_app)
        assert isinstance(middleware.session_interface, MemorySessionInterface)
    
    def test_initialization_with_cookie_interface(self, mock_app):
        """Test initialization with cookie session interface."""
        middleware = SessionMiddleware(mock_app, secret_key="test-key")
        assert isinstance(middleware.session_interface, SignedCookieSessionInterface)
    
    def test_initialization_with_custom_interface(self, mock_app):
        """Test initialization with custom session interface."""
        custom_interface = MemorySessionInterface()
        middleware = SessionMiddleware(mock_app, session_interface=custom_interface)
        assert middleware.session_interface == custom_interface
    
    def test_initialization_with_custom_cookie_params(self, mock_app):
        """Test initialization with custom cookie parameters."""
        cookie_params = {
            "path": "/api",
            "domain": "example.com",
            "secure": True,
            "httponly": False,
            "samesite": "strict"
        }
        middleware = SessionMiddleware(mock_app, cookie_params=cookie_params, secret_key="test")
        assert middleware.cookie_params == cookie_params
    
    def test_set_session_cookie_with_signed_cookie_interface(self, mock_app):
        """Test setting session cookie with signed cookie interface."""
        middleware = SessionMiddleware(mock_app, secret_key="test-key")
        
        from velithon.responses import Response
        response = Response()
        response.raw_headers = []
        
        session = Session({"user_id": 123})
        session._modified = True
        
        middleware._set_session_cookie(response, session)
        
        # Check that set-cookie header was added
        cookie_headers = [h for h in response.raw_headers if h[0] == "set-cookie"]
        assert len(cookie_headers) == 1
        assert "velithon_session=" in cookie_headers[0][1]


class TestGetSession:
    """Test cases for get_session helper function."""
    
    def test_get_session_with_session_attached(self):
        """Test getting session when it's attached to request scope."""
        scope = MagicMock()
        scope.proto = "http"
        protocol = MagicMock()
        request = Request(scope, protocol)
        
        session = Session({"user_id": 123})
        scope._session = session
        
        result = get_session(request)
        assert result == session
    
    def test_get_session_without_session_attached(self):
        """Test getting session when it's not attached to request scope."""
        scope = MagicMock()
        scope.proto = "http"
        # Explicitly say there's no _session attribute
        del scope._session  # This will raise AttributeError when accessed
        protocol = MagicMock()
        
        # Mock the hasattr function to return False
        with pytest.MonkeyPatch().context() as m:
            m.setattr('builtins.hasattr', lambda obj, attr: False if attr == '_session' else hasattr(obj, attr))
            request = Request(scope, protocol)
            result = get_session(request)
            assert isinstance(result, Session)
            assert dict(result) == {}


@pytest.mark.asyncio
async def test_session_middleware_integration():
    """Integration test for session middleware."""

    # Create a simple app that uses sessions
    async def app(scope, protocol):
        request = Request(scope, protocol)
        session = request.session

        # Get current count from session
        count = session.get("count", 0)
        count += 1
        session["count"] = count

        response = JSONResponse({"count": count})
        await response(scope, protocol)

    # Create middleware
    middleware = SessionMiddleware(app, secret_key="test-secret-key")

    # Create mock scope and protocol
    scope = MagicMock()
    scope.proto = "http"
    scope.headers = {}

    # Create a mock protocol that matches the expected interface
    protocol = MagicMock()
    captured_headers = []

    def capture_response_bytes(status, headers, body):
        captured_headers.extend(headers)
        return None  # Just capture and return None

    protocol.response_bytes.side_effect = capture_response_bytes

    # First request - should create new session
    await middleware(scope, protocol)
    
    # Verify session was created and count is 1
    assert hasattr(scope, '_session')
    assert scope._session["count"] == 1
    
    # Verify response was sent
    protocol.response_bytes.assert_called_once()
    
    # Verify that a session cookie was set
    cookie_headers = [h for h in captured_headers if h[0] == "set-cookie"]
    assert len(cookie_headers) > 0
    assert "velithon_session=" in cookie_headers[0][1]


if __name__ == "__main__":
    pytest.main([__file__])
