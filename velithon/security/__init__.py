"""Velithon Security Module.

A comprehensive authentication and authorization system inspired by FastAPI's excellent design
but enhanced for Velithon's architecture. Provides OAuth2, JWT, API Key, and various
authentication schemes with seamless OpenAPI integration.
"""  # noqa: E501

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
    'APIKeyCookie',
    'APIKeyHeader',
    'APIKeyQuery',
    # Exceptions
    'AuthenticationError',
    'AuthorizationError',
    # Permissions
    'CommonPermissions',
    'HTTPBasic',
    'HTTPBearer',
    'InvalidTokenError',
    # JWT
    'JWTHandler',
    # Models
    'LoginRequest',
    'MissingTokenError',
    'OAuth2AuthorizationCodeBearer',
    'OAuth2PasswordBearer',
    'OAuth2PasswordRequestForm',
    'Permission',
    'PermissionChecker',
    'PermissionDependency',
    'RequirePermissions',
    'Security',
    'SecurityBase',
    'SecurityError',
    'Token',
    'TokenData',
    'TokenExpiredError',
    'User',
    'UserCreate',
    'UserInDB',
    # Dependencies
    'authenticate_user',
    'get_current_active_user',
    'get_current_user',
    # Utils
    'get_password_hash',
    'get_user_from_database',
    'hash_password',  # Alias for backward compatibility
    'require_permission',
    'require_permissions',
    'verify_password',
]

# Backward compatibility aliases
hash_password = get_password_hash
