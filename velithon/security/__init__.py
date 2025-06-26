"""Velithon Security Module.

A comprehensive authentication and authorization system inspired by FastAPI's excellent design
but enhanced for Velithon's architecture. Provides OAuth2, JWT, API Key, and various
authentication schemes with seamless OpenAPI integration.
"""

from .auth import (
    APIKeyCookie,
    APIKeyHeader,
    APIKeyQuery,
    HTTPBasic,
    HTTPBearer,
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    Security,
    SecurityBase,
)
from .dependencies import (
    authenticate_user,
    get_current_active_user,
    get_current_user,
    get_user_from_database,
)
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    MissingTokenError,
    SecurityError,
    TokenExpiredError,
)
from .jwt import JWTHandler
from .models import LoginRequest, Token, TokenData, User, UserCreate, UserInDB
from .permissions import (
    CommonPermissions,
    Depends,
    Permission,
    PermissionChecker,
    PermissionDependency,
    RequirePermissions,
    require_permission,
    require_permissions,
)
from .utils import get_password_hash, verify_password

__all__ = [
    # Authentication schemes
    "APIKeyCookie",
    "APIKeyHeader",
    "APIKeyQuery",
    "HTTPBasic",
    "HTTPBearer",
    "OAuth2AuthorizationCodeBearer",
    "OAuth2PasswordBearer",
    "OAuth2PasswordRequestForm",
    "Security",
    "SecurityBase",
    
    # Dependencies
    "authenticate_user",
    "get_current_active_user",
    "get_current_user",
    "get_user_from_database",
    
    # Permissions
    "CommonPermissions",
    "Depends",
    "Permission",
    "PermissionChecker",
    "PermissionDependency",
    "RequirePermissions",
    "require_permission",
    "require_permissions",
    
    # JWT
    "JWTHandler",
    
    # Models
    "LoginRequest",
    "Token",
    "TokenData",
    "User",
    "UserCreate",
    "UserInDB",
    
    # Utils
    "get_password_hash",
    "hash_password",  # Alias for backward compatibility
    "verify_password",
    
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "InvalidTokenError",
    "MissingTokenError",
    "SecurityError",
    "TokenExpiredError",
]

# Backward compatibility aliases
hash_password = get_password_hash
