"""
Integration tests for Velithon authentication system.

These tests verify that the authentication system works correctly
when integrated with a full Velithon application.
"""
import pytest
from typing import Annotated
import asyncio
from unittest.mock import AsyncMock, patch

from velithon import Velithon
from velithon.security import (
    HTTPBearer, HTTPBasic, APIKeyHeader, OAuth2PasswordBearer,
    JWTHandler, User, UserInDB, AuthenticationError, AuthorizationError,
    get_current_user, authenticate_user, require_permission,
    get_password_hash
)
from velithon.responses import JSONResponse
from velithon.requests import Request


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



class TestAuthenticationIntegration:
    """Test authentication integration with Velithon app."""
    
    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler for testing."""
        return JWTHandler(secret_key="test-secret-key-123")
    
    @pytest.fixture
    def app_with_auth(self, jwt_handler):
        """Create a Velithon app with authentication enabled."""
        app = Velithon(
            title="Test Auth App",
            include_security_middleware=True
        )
        
        # Mock user database
        test_users = {
            "admin": UserInDB(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Admin User",
                disabled=False,
                roles=["admin"],
                permissions=["read", "write", "delete", "admin"]
            ),
            "user": UserInDB(
                username="user",
                email="user@example.com",
                hashed_password=get_password_hash("user123"),
                full_name="Regular User",
                disabled=False,
                roles=["user"],
                permissions=["read", "write"]
            )
        }
        
        # Authentication dependencies
        bearer_scheme = HTTPBearer()
        
        async def get_current_user_dependency(request: Request) -> User:
            """Get current user from JWT token."""
            try:
                credentials = await bearer_scheme(request)
                payload = jwt_handler.decode_token(credentials.credentials)
                username = payload.get("sub")
                
                if not username or username not in test_users:
                    raise AuthenticationError("Invalid token")
                
                user_db = test_users[username]
                return User(
                    username=user_db.username,
                    email=user_db.email,
                    full_name=user_db.full_name,
                    disabled=user_db.disabled,
                    roles=user_db.roles,
                    permissions=user_db.permissions
                )
            except Exception as exc:
                raise AuthenticationError("Authentication failed") from exc
        
        # Routes
        @app.get("/")
        async def public_endpoint():
            """Public endpoint - no authentication required."""
            return JSONResponse({"message": "Public access", "public": True})
        
        @app.post("/login")
        async def login(username: str, password: str):
            """Login endpoint that returns JWT token."""
            if username in test_users:
                user_db = test_users[username]
                if password and password in ["admin123", "user123"]:  # Simple check for testing
                    token = jwt_handler.create_access_token({"sub": username})
                    return JSONResponse({
                        "access_token": token,
                        "token_type": "bearer",
                        "user": {
                            "username": user_db.username,
                            "email": user_db.email,
                            "roles": user_db.roles
                        }
                    })
            
            return JSONResponse(
                {"error": "Invalid credentials"},
                status_code=401
            )
        
        @app.get("/protected")
        async def protected_endpoint(
            current_user: Annotated[User, get_current_user_dependency]
        ):
            """Protected endpoint requiring authentication."""
            return JSONResponse({
                "message": f"Hello, {current_user.username}!",
                "user": {
                    "username": current_user.username,
                    "email": current_user.email,
                    "roles": current_user.roles,
                    "permissions": current_user.permissions
                }
            })
        
        @app.get("/admin")
        async def admin_endpoint(
            current_user: Annotated[User, get_current_user_dependency],
            _: Annotated[None, require_permission("admin")]
        ):
            """Admin-only endpoint requiring specific permission."""
            return JSONResponse({
                "message": "Admin access granted",
                "admin_user": current_user.username
            })
        
        # Store JWT handler and test users for test access
        app.jwt_handler = jwt_handler
        app.test_users = test_users
        
        return app
    
    @pytest.mark.asyncio
    async def test_public_endpoint_access(self, app_with_auth):
        """Test that public endpoints are accessible without authentication."""
        app = app_with_auth
        
        # Mock request/response
        scope = MockRSGIScope(
            proto="http",
            method="GET",
            path="/",
            headers=[],
            query_string=b"",
            server=("localhost", 8000),
            scheme="http"
        )
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response
        assert len(messages) >= 2  # At least response.start and response.body
        # The response should be successful (status 200)
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200
    
    @pytest.mark.asyncio
    async def test_login_endpoint_success(self, app_with_auth):
        """Test successful login with valid credentials."""
        app = app_with_auth
        
        # Mock login request
        scope = MockRSGIScope(
            proto="http",
            method="POST",
            path="/login",
            headers=[
                (b"content-type", b"application/x-www-form-urlencoded")
            ],
            query_string=b"username=admin&password=admin123",
            server=("localhost", 8000),
            scheme="http"
        )
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, app_with_auth):
        """Test that protected endpoints reject requests without tokens."""
        app = app_with_auth
        
        # Mock request without Authorization header
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response - should be 401 Unauthorized
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 401
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(self, app_with_auth):
        """Test that protected endpoints accept valid tokens."""
        app = app_with_auth
        
        # Create a valid token
        token = app.jwt_handler.create_access_token({"sub": "admin"})
        
        # Mock request with valid Authorization header
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [
                (b"authorization", f"Bearer {token}".encode())
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response - should be 200 OK
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_with_regular_user(self, app_with_auth):
        """Test that admin endpoints reject regular users."""
        app = app_with_auth
        
        # Create a token for regular user
        token = app.jwt_handler.create_access_token({"sub": "user"})
        
        # Mock request with user token
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin",
            "headers": [
                (b"authorization", f"Bearer {token}".encode())
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response - should be 403 Forbidden
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 403
    
    @pytest.mark.asyncio
    async def test_admin_endpoint_with_admin_user(self, app_with_auth):
        """Test that admin endpoints accept admin users."""
        app = app_with_auth
        
        # Create a token for admin user
        token = app.jwt_handler.create_access_token({"sub": "admin"})
        
        # Mock request with admin token
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin",
            "headers": [
                (b"authorization", f"Bearer {token}".encode())
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response - should be 200 OK
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200


class TestMultiSchemeAuthentication:
    """Test application with multiple authentication schemes."""
    
    @pytest.fixture
    def multi_auth_app(self):
        """Create app with multiple authentication schemes."""
        app = Velithon(
            title="Multi-Auth Test App",
            include_security_middleware=True
        )
        
        # Authentication schemes
        bearer_scheme = HTTPBearer()
        basic_scheme = HTTPBasic()
        api_key_scheme = APIKeyHeader(name="X-API-Key")
        
        # Mock API keys
        valid_api_keys = {"secret-key-123", "admin-key-456"}
        
        @app.get("/bearer-auth")
        async def bearer_auth_endpoint(request: Request):
            """Endpoint using Bearer token authentication."""
            try:
                credentials = await bearer_scheme(request)
                return JSONResponse({
                    "message": "Bearer auth successful",
                    "token_length": len(credentials.credentials)
                })
            except AuthenticationError as e:
                return JSONResponse(
                    {"error": str(e)},
                    status_code=401
                )
        
        @app.get("/basic-auth")
        async def basic_auth_endpoint(request: Request):
            """Endpoint using Basic authentication."""
            try:
                credentials = basic_scheme(request)
                # Simple validation for testing
                if credentials.username == "admin" and credentials.password == "secret":
                    return JSONResponse({
                        "message": "Basic auth successful",
                        "username": credentials.username
                    })
                else:
                    return JSONResponse(
                        {"error": "Invalid credentials"},
                        status_code=401
                    )
            except AuthenticationError as e:
                return JSONResponse(
                    {"error": str(e)},
                    status_code=401
                )
        
        @app.get("/api-key-auth")
        async def api_key_auth_endpoint(request: Request):
            """Endpoint using API key authentication."""
            try:
                api_key = api_key_scheme(request)
                if api_key in valid_api_keys:
                    return JSONResponse({
                        "message": "API key auth successful",
                        "key_hint": api_key[:6] + "..."
                    })
                else:
                    return JSONResponse(
                        {"error": "Invalid API key"},
                        status_code=401
                    )
            except AuthenticationError as e:
                return JSONResponse(
                    {"error": str(e)},
                    status_code=401
                )
        
        return app
    
    @pytest.mark.asyncio
    async def test_bearer_authentication(self, multi_auth_app):
        """Test Bearer token authentication."""
        app = multi_auth_app
        
        # Mock request with Bearer token
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/bearer-auth",
            "headers": [
                (b"authorization", b"Bearer test-token-123")
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200
    
    @pytest.mark.asyncio
    async def test_basic_authentication_success(self, multi_auth_app):
        """Test successful Basic authentication."""
        app = multi_auth_app
        
        # Encode credentials
        import base64
        credentials = base64.b64encode(b"admin:secret").decode()
        
        # Mock request with Basic auth
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/basic-auth",
            "headers": [
                (b"authorization", f"Basic {credentials}".encode())
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200
    
    @pytest.mark.asyncio
    async def test_api_key_authentication_success(self, multi_auth_app):
        """Test successful API key authentication."""
        app = multi_auth_app
        
        # Mock request with API key
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api-key-auth",
            "headers": [
                (b"x-api-key", b"secret-key-123")
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 200
    
    @pytest.mark.asyncio
    async def test_api_key_authentication_failure(self, multi_auth_app):
        """Test failed API key authentication."""
        app = multi_auth_app
        
        # Mock request with invalid API key
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api-key-auth",
            "headers": [
                (b"x-api-key", b"invalid-key")
            ],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check response
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 401


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    @pytest.fixture
    def app_with_security_middleware(self):
        """Create app with security middleware enabled."""
        return Velithon(
            title="Security Middleware Test",
            include_security_middleware=True
        )
    
    @pytest.mark.asyncio
    async def test_security_headers_added(self, app_with_security_middleware):
        """Test that security middleware adds security headers."""
        app = app_with_security_middleware
        
        @app.get("/test")
        async def test_endpoint():
            return JSONResponse({"message": "test"})
        
        # Mock request
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http"
        }
        
        protocol = AsyncMock()
        messages = []
        
        async def mock_send(message):
            messages.append(message)
        
        protocol.send = mock_send
        
        # Call the app
        await app(scope, protocol)
        
        # Check that security headers are present
        start_message = messages[0]
        assert start_message["type"] == "http.response.start"
        
        headers = dict(start_message["headers"])
        
        # Check for common security headers
        expected_headers = [
            b"x-content-type-options",
            b"x-frame-options",
            b"x-xss-protection"
        ]
        
        for header in expected_headers:
            assert header in headers


if __name__ == "__main__":
    pytest.main([__file__])
