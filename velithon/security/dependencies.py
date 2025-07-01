"""Authentication dependencies for Velithon security system."""

from typing import Annotated

from velithon.requests import Request

from .auth import OAuth2PasswordBearer
from .exceptions import AuthenticationError, AuthorizationError
from .jwt import decode_access_token
from .models import User


# Default OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(token_url="/token")


async def get_current_user(
    request: Request,
    token: Annotated[str, oauth2_scheme]
) -> User:
    """Get current user from JWT token."""
    try:
        token_data = decode_access_token(token)
        username = token_data.username
        
        if username is None:
            raise AuthenticationError("Invalid token: no username")
        
        # TODO: Replace with actual user lookup from database
        # This is a placeholder implementation
        user = await get_user_from_database(username)
        if user is None:
            raise AuthenticationError("User not found")
        
        return user
        
    except Exception as e:
        if isinstance(e, (AuthenticationError, AuthorizationError)):
            raise
        raise AuthenticationError("Could not validate credentials") from e


async def get_current_active_user(
    current_user: Annotated[User, get_current_user]
) -> User:
    """Get current active user (not disabled)."""
    if current_user.disabled:
        raise AuthorizationError("User account is disabled")
    return current_user


async def require_auth(request: Request) -> str:
    """Require authentication and return the token."""
    token = await oauth2_scheme(request)
    if not token:
        raise AuthenticationError("Authentication required")
    return token


# Placeholder user database functions
# In a real application, these would connect to your database

FAKE_USERS_DB = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": (
            "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        ),
        "disabled": False,
        "scopes": ["user:read", "user:write"]
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Smith", 
        "email": "alice@example.com",
        "hashed_password": (
            "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        ),
        "disabled": False,
        "scopes": ["user:read", "user:write", "admin:read"]
    },
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "hashed_password": (
            "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        ),
        "disabled": False,
        "scopes": ["user:read", "user:write", "admin:read", "admin:write", "admin:full"]
    }
}


async def get_user_from_database(username: str) -> User | None:
    """Get user from database by username."""
    user_data = FAKE_USERS_DB.get(username)
    if user_data:
        return User(**user_data)
    return None


async def authenticate_user(username: str, password: str) -> User | None:
    """Authenticate user with username and password."""
    from .utils import verify_password
    
    user_data = FAKE_USERS_DB.get(username)
    if not user_data:
        return None
    
    if not verify_password(password, user_data["hashed_password"]):
        return None
    
    return User(**user_data)


def create_user_dependency(
    require_active: bool = True,
    require_scopes: list[str] | None = None
):
    """Create a user dependency with specific requirements."""
    
    async def user_dependency(request: Request) -> User:
        """Get user with specific requirements."""
        # Get token
        token = await oauth2_scheme(request)
        if not token:
            raise AuthenticationError("Authentication required")
        
        # Decode token and get user
        try:
            token_data = decode_access_token(token)
            username = token_data.username
            
            if username is None:
                raise AuthenticationError("Invalid token: no username")
            
            user = await get_user_from_database(username)
            if user is None:
                raise AuthenticationError("User not found")
            
            # Check if user is active
            if require_active and user.disabled:
                raise AuthorizationError("User account is disabled")
            
            # Check scopes
            if require_scopes:
                user_scopes = set(user.scopes)
                required_scopes = set(require_scopes)
                if not required_scopes.issubset(user_scopes):
                    missing_scopes = required_scopes - user_scopes
                    raise AuthorizationError(
                        f"Missing required scopes: {list(missing_scopes)}"
                    )
            
            return user
            
        except Exception as e:
            if isinstance(e, (AuthenticationError, AuthorizationError)):
                raise
            raise AuthenticationError("Could not validate credentials") from e
    
    return user_dependency


# Convenient pre-built dependencies
async def get_admin_user(request: Request) -> User:
    """Get current user with admin privileges."""
    user_dep = create_user_dependency(
        require_active=True,
        require_scopes=["admin:read"]
    )
    return await user_dep(request)


async def get_superuser(request: Request) -> User:
    """Get current user with full admin privileges."""
    user_dep = create_user_dependency(
        require_active=True,
        require_scopes=["admin:full"]
    )
    return await user_dep(request)
