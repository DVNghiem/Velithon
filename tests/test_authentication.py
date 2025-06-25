"""
Test suite for Velithon authentication and security components.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import base64
import json

from velithon.security import (
    HTTPBearer, HTTPBasic, APIKeyHeader, OAuth2PasswordBearer,
    JWTHandler, User, UserInDB, UserCreate, Token, TokenData,
    get_password_hash, verify_password, hash_password,
    AuthenticationError, AuthorizationError, TokenExpiredError,
    InvalidTokenError, MissingTokenError,
    require_permission, Permission, PermissionChecker,
    authenticate_user
)


class TestPasswordUtils:
    """Test password hashing and verification utilities."""
    
    def test_hash_password(self):
        """Test password hashing functionality."""
        password = "test_password123"
        hashed = hash_password(password)
        
        assert hashed != password
        # Check if it's bcrypt format or fallback format
        assert hashed.startswith("$2b$") or ":" in hashed
        assert len(hashed) > 50
    
    def test_verify_password_valid(self):
        """Test password verification with valid password."""
        password = "test_password123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_invalid(self):
        """Test password verification with invalid password."""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_get_password_hash_alias(self):
        """Test that get_password_hash is an alias for hash_password."""
        password = "test_password123"
        hash1 = hash_password(password)
        hash2 = get_password_hash(password)
        
        # They should both be valid hashes
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestUserModels:
    """Test user data models."""
    
    def test_user_model_creation(self):
        """Test creating a User model."""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            roles=["user"],
            permissions=["read", "write"]
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.disabled is False
        assert user.roles == ["user"]
        assert user.permissions == ["read", "write"]
    
    def test_user_model_defaults(self):
        """Test User model with default values."""
        user = User(username="testuser", email="test@example.com")
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name is None
        assert user.disabled is False
        assert user.roles == []
        assert user.permissions == []
    
    def test_user_in_db_model(self):
        """Test creating a UserInDB model."""
        user_db = UserInDB(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$hash...",
            full_name="Test User",
            disabled=False,
            roles=["user"],
            permissions=["read"]
        )
        
        assert user_db.username == "testuser"
        assert user_db.hashed_password == "$2b$12$hash..."
    
    def test_user_create_model(self):
        """Test creating a UserCreate model."""
        user_create = UserCreate(
            username="newuser",
            email="new@example.com", 
            password="password123",
            full_name="New User"
        )
        
        assert user_create.username == "newuser"
        assert user_create.password == "password123"
        assert len(user_create.password) >= 8  # Minimum length validation
    
    def test_user_create_password_validation(self):
        """Test UserCreate password validation."""
        with pytest.raises(ValueError):
            UserCreate(
                username="newuser",
                email="new@example.com",
                password="short",  # Too short
                full_name="New User"
            )
    
    def test_token_model(self):
        """Test Token model."""
        token = Token(
            access_token="test-token-123",
            token_type="bearer",
            expires_in=3600
        )
        
        assert token.access_token == "test-token-123"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
    
    def test_token_data_model(self):
        """Test TokenData model."""
        token_data = TokenData(
            username="testuser",
            scopes=["read", "write"]
        )
        
        assert token_data.username == "testuser"
        assert token_data.scopes == ["read", "write"]


class TestJWTHandler:
    """Test JWT token handling."""
    
    def test_jwt_handler_creation(self):
        """Test creating JWT handler."""
        handler = JWTHandler(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire=timedelta(minutes=30)
        )
        
        assert handler.config.secret_key == "test-secret-key"
        assert handler.config.algorithm == "HS256"
    
    def test_create_and_decode_token(self):
        """Test token creation and decoding."""
        handler = JWTHandler(
            secret_key="test-secret-key",
            algorithm="HS256"
        )
        
        payload = {"sub": "testuser", "scope": "user"}
        token = handler.create_access_token(payload)
        
        assert isinstance(token, str)
        assert len(token) > 50
        
        decoded = handler.decode_token(token)
        assert decoded["sub"] == "testuser"
        assert decoded["scope"] == "user"
        assert "exp" in decoded
    
    def test_token_with_expiration(self):
        """Test token creation with custom expiration."""
        handler = JWTHandler(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire=timedelta(minutes=30)
        )
        
        payload = {"sub": "testuser"}
        token = handler.create_access_token(payload)
        decoded = handler.decode_token(token)
        
        # Check that expiration is set correctly
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = exp_time - now
        
        # Should be close to 30 minutes (allowing for small time differences)
        assert 1700 < time_diff.total_seconds() < 1900
    
    def test_token_expiration_error(self):
        """Test handling of expired tokens."""
        handler = JWTHandler(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire=timedelta(seconds=-1)  # Already expired
        )
        
        payload = {"sub": "testuser"}
        token = handler.create_access_token(payload)
        
        with pytest.raises(TokenExpiredError):
            handler.decode_token(token)
    
    def test_invalid_token_error(self):
        """Test handling of invalid tokens."""
        handler = JWTHandler(
            secret_key="test-secret-key",
            algorithm="HS256"
        )
        
        with pytest.raises(InvalidTokenError):
            handler.decode_token("invalid.token.here")
    
    def test_wrong_secret_key(self):
        """Test token validation with wrong secret key."""
        handler1 = JWTHandler(secret_key="secret1")
        handler2 = JWTHandler(secret_key="secret2")
        
        token = handler1.create_access_token({"sub": "testuser"})
        
        with pytest.raises(InvalidTokenError):
            handler2.decode_token(token)


class TestAuthenticationSchemes:
    """Test authentication schemes."""
    
    @pytest.mark.asyncio
    async def test_http_bearer_success(self):
        """Test HTTPBearer with valid token."""
        scheme = HTTPBearer()
        
        # Create a simple mock request with headers
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": "Bearer test-token-123"})
        
        credentials = await scheme(request)
        assert credentials == "test-token-123"
    
    @pytest.mark.asyncio
    async def test_http_bearer_missing_header(self):
        """Test HTTPBearer with missing Authorization header."""
        scheme = HTTPBearer()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({})
        
        with pytest.raises((AuthenticationError, MissingTokenError)):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_http_bearer_invalid_format(self):
        """Test HTTPBearer with invalid Authorization format."""
        scheme = HTTPBearer()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": "Basic dGVzdA=="})
        
        with pytest.raises(AuthenticationError):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_http_bearer_no_token(self):
        """Test HTTPBearer with Bearer but no token."""
        scheme = HTTPBearer()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": "Bearer"})
        
        with pytest.raises(AuthenticationError):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_http_basic_success(self):
        """Test HTTPBasic with valid credentials."""
        scheme = HTTPBasic()
        
        # Base64 encoded "testuser:password"
        credentials_b64 = base64.b64encode(b"testuser:password").decode()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": f"Basic {credentials_b64}"})
        
        credentials = await scheme(request)
        assert credentials == "testuser:password"
    
    @pytest.mark.asyncio
    async def test_http_basic_missing_header(self):
        """Test HTTPBasic with missing Authorization header."""
        scheme = HTTPBasic()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({})
        
        with pytest.raises((AuthenticationError, MissingTokenError)):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_http_basic_invalid_encoding(self):
        """Test HTTPBasic with invalid base64 encoding."""
        scheme = HTTPBasic()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": "Basic invalid-base64"})
        
        with pytest.raises(AuthenticationError):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_http_basic_no_colon(self):
        """Test HTTPBasic with credentials missing colon separator."""
        scheme = HTTPBasic()
        
        # Base64 encoded "testuser" (no colon/password)
        credentials_b64 = base64.b64encode(b"testuser").decode()
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": f"Basic {credentials_b64}"})
        
        with pytest.raises(AuthenticationError):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_api_key_header_success(self):
        """Test APIKeyHeader with valid key."""
        scheme = APIKeyHeader(name="X-API-Key")
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"X-API-Key": "secret-api-key"})
        
        api_key = await scheme(request)
        assert api_key == "secret-api-key"
    
    @pytest.mark.asyncio
    async def test_api_key_header_missing(self):
        """Test APIKeyHeader with missing key."""
        scheme = APIKeyHeader(name="X-API-Key")
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({})
        
        with pytest.raises((AuthenticationError, MissingTokenError)):
            await scheme(request)
    
    @pytest.mark.asyncio
    async def test_api_key_header_custom_name(self):
        """Test APIKeyHeader with custom header name."""
        scheme = APIKeyHeader(name="X-Custom-Key")
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"X-Custom-Key": "custom-key-value"})
        
        api_key = await scheme(request)
        assert api_key == "custom-key-value"
    
    @pytest.mark.asyncio
    async def test_oauth2_password_bearer_success(self):
        """Test OAuth2PasswordBearer with valid token."""
        scheme = OAuth2PasswordBearer(token_url="/token")
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({"Authorization": "Bearer oauth-token-123"})
        
        token = await scheme(request)
        assert token == "oauth-token-123"
    
    @pytest.mark.asyncio
    async def test_oauth2_password_bearer_missing_token(self):
        """Test OAuth2PasswordBearer with missing token."""
        scheme = OAuth2PasswordBearer(token_url="/token")
        
        class MockRequest:
            def __init__(self, headers_dict):
                self.headers = headers_dict
        
        request = MockRequest({})
        
        with pytest.raises((AuthenticationError, MissingTokenError)):
            await scheme(request)
    
    def test_oauth2_openapi_definition(self):
        """Test OAuth2PasswordBearer OpenAPI definition."""
        scheme = OAuth2PasswordBearer(token_url="/auth/token")
        definition = scheme.get_openapi_security_definition()
        
        expected = {
            "type": "oauth2",
            "description": "OAuth2 password flow with Bearer token",
            "flows": {
                "password": {
                    "tokenUrl": "/auth/token",
                    "scopes": {}
                }
            }
        }
        assert definition == expected


class TestPermissions:
    """Test permission system."""
    
    def test_permission_creation(self):
        """Test creating Permission objects."""
        perm = Permission("admin", "Administrative access")
        
        assert perm.name == "admin"
        assert perm.description == "Administrative access"
        assert str(perm) == "admin"
    
    def test_permission_equality(self):
        """Test permission equality comparison."""
        perm1 = Permission("admin", "Admin access")
        perm2 = Permission("admin", "Different description")
        perm3 = Permission("user", "User access")
        
        assert perm1 == perm2  # Same name
        assert perm1 != perm3  # Different name
        assert perm1 == "admin"  # String comparison
        assert perm1 != "user"
    
    def test_permission_checker_has_permission(self):
        """Test PermissionChecker.has_permission method."""
        checker = PermissionChecker()
        
        user_permissions = ["read", "write", Permission("admin", "Admin")]
        
        assert checker.has_permission(user_permissions, "read")
        assert checker.has_permission(user_permissions, "write")
        assert checker.has_permission(user_permissions, Permission("admin", "Admin"))
        assert not checker.has_permission(user_permissions, "delete")
    
    def test_permission_checker_has_all_permissions(self):
        """Test PermissionChecker.has_all_permissions method."""
        checker = PermissionChecker()
        
        user_permissions = ["read", "write", "admin"]
        required_permissions = ["read", "write"]
        
        assert checker.has_all_permissions(user_permissions, required_permissions)
        
        required_permissions_missing = ["read", "write", "delete"]
        assert not checker.has_all_permissions(user_permissions, required_permissions_missing)
    
    def test_permission_checker_has_any_permission(self):
        """Test PermissionChecker.has_any_permission method."""
        checker = PermissionChecker()
        
        user_permissions = ["read", "write"]
        
        assert checker.has_any_permission(user_permissions, ["read", "admin"])
        assert checker.has_any_permission(user_permissions, ["write", "delete"])
        assert not checker.has_any_permission(user_permissions, ["admin", "delete"])
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test require_permission decorator with valid permission."""
        request = Mock()
        request.state = Mock()
        
        # Mock user with required permission
        user = User(
            username="testuser",
            email="test@example.com",
            permissions=["read", "write", "admin"]
        )
        request.state.user = user
        
        # Create permission dependency
        permission_dependency = require_permission("admin")
        
        # Should not raise any exception
        result = await permission_dependency(request)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_require_permission_failure(self):
        """Test require_permission decorator without required permission."""
        request = Mock()
        request.state = Mock()
        
        # Mock user without required permission
        user = User(
            username="testuser",
            email="test@example.com",
            permissions=["read", "write"]
        )
        request.state.user = user
        
        # Create permission dependency
        permission_dependency = require_permission("admin")
        
        # Should raise AuthorizationError
        with pytest.raises(AuthorizationError, match="Missing required permission: admin"):
            await permission_dependency(request)
    
    @pytest.mark.asyncio
    async def test_require_permission_no_user(self):
        """Test require_permission decorator with no authenticated user."""
        request = Mock()
        request.state = Mock()
        request.state.user = None
        
        # Create permission dependency
        permission_dependency = require_permission("admin")
        
        # Should raise AuthorizationError
        with pytest.raises(AuthorizationError, match="User not authenticated"):
            await permission_dependency(request)


class TestSecurityExceptions:
    """Test security exception hierarchy."""
    
    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Invalid credentials")
    
    def test_authorization_error(self):
        """Test AuthorizationError exception."""
        with pytest.raises(AuthorizationError):
            raise AuthorizationError("Access denied")
    
    def test_token_expired_error(self):
        """Test TokenExpiredError exception."""
        with pytest.raises(TokenExpiredError):
            raise TokenExpiredError("Token has expired")
    
    def test_invalid_token_error(self):
        """Test InvalidTokenError exception."""
        with pytest.raises(InvalidTokenError):
            raise InvalidTokenError("Invalid token format")
    
    def test_exception_inheritance(self):
        """Test that all security exceptions inherit from appropriate base classes."""
        from velithon.security.exceptions import SecurityError
        
        # All should inherit from SecurityError
        assert issubclass(AuthenticationError, SecurityError)
        assert issubclass(AuthorizationError, SecurityError)
        assert issubclass(TokenExpiredError, SecurityError)
        assert issubclass(InvalidTokenError, SecurityError)


class TestSecurityDependencies:
    """Test security dependency functions."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test authenticate_user function with valid credentials."""
        # Mock the FAKE_USERS_DB with our test user
        test_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": get_password_hash("password123"),
            "disabled": False,
            "roles": ["user"],
            "permissions": ["read"]
        }
        
        test_db = {"testuser": test_user_data}
        with patch('velithon.security.dependencies.FAKE_USERS_DB', test_db):
            user = await authenticate_user("testuser", "password123")
            assert user is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self):
        """Test authenticate_user function with invalid password."""
        # Mock database function
        async def mock_get_user(username: str):
            if username == "testuser":
                return UserInDB(
                    username="testuser",
                    email="test@example.com",
                    hashed_password=get_password_hash("password123"),
                    disabled=False
                )
            return None
        
        with patch('velithon.security.dependencies.get_user_from_database', mock_get_user):
            user = await authenticate_user("testuser", "wrongpassword")
            assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authenticate_user function with non-existent user."""
        # Mock database function
        async def mock_get_user(username: str):
            return None
        
        with patch('velithon.security.dependencies.get_user_from_database', mock_get_user):
            user = await authenticate_user("nonexistent", "password123")
            assert user is None


if __name__ == "__main__":
    pytest.main([__file__])
