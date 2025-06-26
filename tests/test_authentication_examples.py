"""
Tests for Velithon authentication examples.

These tests verify that the example applications work correctly
and demonstrate proper authentication usage patterns.
"""
import pytest
from unittest.mock import patch, Mock
import asyncio
from typing import Annotated

from velithon import Velithon
from velithon.requests import Request
from velithon.security import (
    HTTPBearer, JWTHandler, User, AuthenticationError,
    get_password_hash
)
from velithon.responses import JSONResponse


class TestSimpleAuthExample:
    """Test the simple authentication example patterns."""
    
    def test_jwt_handler_setup(self):
        """Test JWT handler configuration from simple example."""
        SECRET_KEY = "test-secret-key-here"
        jwt_handler = JWTHandler(secret_key=SECRET_KEY)
        
        assert jwt_handler.config.secret_key == SECRET_KEY
        assert jwt_handler.config.algorithm == "HS256"  # Default algorithm
    
    def test_bearer_scheme_setup(self):
        """Test Bearer authentication scheme setup."""
        bearer_scheme = HTTPBearer()
        
        # Test scheme configuration
        openapi_def = bearer_scheme.get_openapi_security_definition()
        assert openapi_def["type"] == "http"
        assert openapi_def["scheme"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_get_current_user_function(self):
        """Test the get_current_user dependency function pattern."""
        SECRET_KEY = "test-secret-key"
        jwt_handler = JWTHandler(secret_key=SECRET_KEY)
        bearer_scheme = HTTPBearer()
        
        # Create a test token
        test_token = jwt_handler.create_access_token({"sub": "testuser"})
        
        # Mock request with Bearer token
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": f"Bearer {test_token}"})
        
        # Define the get_current_user function (from simple example pattern)
        async def get_current_user(request) -> User:
            """Get current user from JWT token."""
            try:
                credentials = await bearer_scheme(request)
                payload = jwt_handler.decode_token(credentials)
                username = payload.get("sub")
                if not username:
                    raise AuthenticationError("Invalid token")
                
                # In a real app, you'd fetch user from database
                return User(
                    username=username,
                    email=f"{username}@example.com",
                    full_name=f"User {username}",
                    disabled=False,
                    roles=["user"],
                    permissions=["read"],
                )
            except Exception as exc:
                raise AuthenticationError("Invalid or missing token") from exc
        
        # Test the function
        user = await get_current_user(request)
        assert user.username == "testuser"
        assert user.email == "testuser@example.com"
        assert user.full_name == "User testuser"
        assert user.roles == ["user"]
        assert user.permissions == ["read"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        jwt_handler = JWTHandler(secret_key="test-secret-key")
        bearer_scheme = HTTPBearer()
        
        # Mock request with invalid token
        request = Mock()
        request.headers = {"Authorization": "Bearer invalid-token"}
        
        async def get_current_user(request) -> User:
            """Get current user from JWT token."""
            try:
                credentials = await bearer_scheme(request)
                payload = jwt_handler.decode_token(credentials.credentials)
                username = payload.get("sub")
                if not username:
                    raise AuthenticationError("Invalid token")
                
                return User(
                    username=username,
                    email=f"{username}@example.com",
                    full_name=f"User {username}",
                    disabled=False,
                    roles=["user"],
                    permissions=["read"],
                )
            except Exception as exc:
                raise AuthenticationError("Invalid or missing token") from exc
        
        # Test that it raises an authentication error
        with pytest.raises(AuthenticationError):
            await get_current_user(request)


class TestAuthenticationFlowExample:
    """Test complete authentication flow from examples."""
    
    @pytest.fixture
    def example_app(self):
        """Create an app following the example patterns."""
        SECRET_KEY = "test-secret-key-here"
        jwt_handler = JWTHandler(secret_key=SECRET_KEY)
        bearer_scheme = HTTPBearer()
        
        app = Velithon(
            title="Authentication Flow Test",
            description="Test authentication flow patterns",
            include_security_middleware=True,
        )
        
        # Store handlers for test access
        app.jwt_handler = jwt_handler
        app.bearer_scheme = bearer_scheme
        
        async def get_current_user(request) -> User:
            """Get current user from JWT token."""
            try:
                credentials = await bearer_scheme(request)
                payload = jwt_handler.decode_token(credentials.credentials)
                username = payload.get("sub")
                if not username:
                    raise AuthenticationError("Invalid token")
                
                return User(
                    username=username,
                    email=f"{username}@example.com",
                    full_name=f"User {username}",
                    disabled=False,
                    roles=["user"],
                    permissions=["read"],
                )
            except Exception as exc:
                raise AuthenticationError("Invalid or missing token") from exc
        
        @app.get("/")
        async def public_endpoint():
            """Public endpoint - no authentication required."""
            return JSONResponse({
                "message": "Hello! This is a public endpoint.",
                "info": "To access protected endpoints, you need a JWT token.",
                "login_url": "/login",
            })
        
        @app.post("/login")
        async def login(username: str, password: str):
            """Simple login endpoint that returns a JWT token."""
            # In a real app, verify credentials against database
            if username == "admin" and password == "secret":
                token = jwt_handler.create_access_token({"sub": username})
                return JSONResponse({
                    "access_token": token,
                    "token_type": "bearer",
                    "message": "Login successful!",
                })
            else:
                return JSONResponse(
                    {"error": "Invalid credentials"},
                    status_code=401,
                )
        
        @app.get("/protected")
        async def protected_endpoint(
            current_user: Annotated[User, get_current_user]
        ):
            """Protected endpoint - requires JWT authentication."""
            return JSONResponse({
                "message": f"Hello, {current_user.full_name}!",
                "username": current_user.username,
                "permissions": current_user.permissions,
                "info": "This is a protected endpoint",
            })
        
        return app
    
    def test_app_creation_with_security(self, example_app):
        """Test that app is created with security middleware enabled."""
        app = example_app
        
        assert app.title == "Authentication Flow Test"
        assert app.include_security_middleware is True
        
        # Check that JWT handler is configured
        assert hasattr(app, "jwt_handler")
        assert app.jwt_handler.config.secret_key == "test-secret-key-here"
    
    def test_login_token_generation(self, example_app):
        """Test login endpoint token generation."""
        app = example_app
        jwt_handler = app.jwt_handler
        
        # Test token creation (simulating login success)
        username = "admin"
        token = jwt_handler.create_access_token({"sub": username})
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
        
        # Verify token can be decoded
        payload = jwt_handler.decode_token(token)
        assert payload["sub"] == username
        assert "exp" in payload  # Expiration time should be present
    
    def test_token_validation_flow(self, example_app):
        """Test complete token validation flow."""
        app = example_app
        jwt_handler = app.jwt_handler
        
        # Create a valid token
        username = "testuser"
        token = jwt_handler.create_access_token({"sub": username})
        
        # Verify token validation
        payload = jwt_handler.decode_token(token)
        assert payload["sub"] == username
        
        # Test invalid token
        with pytest.raises(Exception):  # Should raise InvalidTokenError or similar
            jwt_handler.decode_token("invalid.token.here")


class TestExampleSecurityPatterns:
    """Test security patterns used in examples."""
    
    def test_password_validation_pattern(self):
        """Test password validation patterns from examples."""
        # Test password hashing pattern
        test_password = "secret123"
        hashed_password = get_password_hash(test_password)
        
        assert hashed_password != test_password
        # Our hash format uses hex encoding with salt separated by colon
        assert ":" in hashed_password
        parts = hashed_password.split(":")
        assert len(parts) == 2
        # Both parts should be hex strings
        assert all(c in "0123456789abcdef" for c in parts[0])
        assert all(c in "0123456789abcdef" for c in parts[1])
        
        # Test verification pattern
        from velithon.security import verify_password
        assert verify_password(test_password, hashed_password) is True
        assert verify_password("wrong_password", hashed_password) is False
    
    def test_user_model_pattern(self):
        """Test User model creation patterns from examples."""
        # Test user creation pattern from examples
        user = User(
            username="john",
            email="john@example.com",
            full_name="John Doe",
            disabled=False,
            roles=["user", "admin"],
            permissions=["read", "write", "delete"],
        )
        
        assert user.username == "john"
        assert user.email == "john@example.com"
        assert user.full_name == "John Doe"
        assert user.disabled is False
        assert "user" in user.roles
        assert "admin" in user.roles
        assert "read" in user.permissions
        assert "write" in user.permissions
        assert "delete" in user.permissions
    
    def test_error_handling_pattern(self):
        """Test error handling patterns from examples."""
        # Test that authentication errors are properly defined
        error = AuthenticationError("Invalid credentials")
        assert str(error) == "Invalid credentials"
        assert isinstance(error, Exception)
        
        # Test error in authentication flow
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Token expired")
    
    def test_openapi_integration_pattern(self):
        """Test OpenAPI integration patterns from examples."""
        app = Velithon(
            title="Example API",
            description="Example with authentication",
            version="1.0.0"
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Get OpenAPI specification
        openapi_spec = app.get_openapi()
        
        # Verify structure matches example patterns
        assert openapi_spec["info"]["title"] == "Example API"
        assert openapi_spec["info"]["description"] == "Example with authentication"
        assert openapi_spec["info"]["version"] == "1.0.0"
        
        # Verify security schemes are included
        assert "components" in openapi_spec
        assert "securitySchemes" in openapi_spec["components"]
        
        security_schemes = openapi_spec["components"]["securitySchemes"]
        assert "bearerAuth" in security_schemes
        
        # Verify Bearer token configuration
        bearer_scheme = security_schemes["bearerAuth"]
        assert bearer_scheme["type"] == "http"
        assert bearer_scheme["scheme"] == "bearer"
        assert bearer_scheme["bearerFormat"] == "JWT"


if __name__ == "__main__":
    pytest.main([__file__])
