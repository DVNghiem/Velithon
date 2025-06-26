"""Security models for Velithon authentication system."""

from datetime import datetime
from typing import Any

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    Field = lambda **kwargs: None


class Token(BaseModel):
    """OAuth2 token response model."""
    
    access_token: str = Field(..., description="The access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int | None = Field(None, description="Token expiration in seconds")
    refresh_token: str | None = Field(None, description="Refresh token")
    scope: str | None = Field(None, description="Token scope")


class TokenData(BaseModel):
    """Token data model for internal use."""
    
    username: str | None = Field(None, description="Username")
    user_id: str | int | None = Field(None, description="User ID")
    scopes: list[str] = Field(default_factory=list, description="Token scopes")
    expires_at: datetime | None = Field(None, description="Expiration time")


class User(BaseModel):
    """Basic user model."""
    
    username: str = Field(..., description="Username")
    email: str | None = Field(None, description="Email address")
    full_name: str | None = Field(None, description="Full name")
    disabled: bool = Field(default=False, description="Whether user is disabled")
    roles: list[str] = Field(default_factory=list, description="User roles")
    permissions: list[str] = Field(default_factory=list, description="User permissions")
    scopes: list[str] = Field(default_factory=list, description="OAuth scopes")


class UserInDB(User):
    """User model with hashed password for database storage."""
    
    hashed_password: str = Field(..., description="Hashed password")


class UserCreate(BaseModel):
    """User creation model."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    full_name: str | None = Field(None, description="Full name")
    password: str = Field(..., min_length=8, description="Password")


class UserUpdate(BaseModel):
    """User update model."""
    
    email: str | None = Field(None, description="Email address")
    full_name: str | None = Field(None, description="Full name")
    disabled: bool | None = Field(None, description="Whether user is disabled")
    scopes: list[str] | None = Field(None, description="User permissions")


class LoginRequest(BaseModel):
    """Login request model."""
    
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class SecurityScope(BaseModel):
    """Security scope definition."""
    
    scope_name: str = Field(..., description="Scope name")
    description: str = Field(..., description="Scope description")


if not PYDANTIC_AVAILABLE:
    # Fallback implementations when Pydantic is not available
    
    class Token:
        """OAuth2 token response model."""
        
        def __init__(self, access_token: str, token_type: str = "bearer",
                     expires_in: int | None = None, refresh_token: str | None = None,
                     scope: str | None = None):
            self.access_token = access_token
            self.token_type = token_type
            self.expires_in = expires_in
            self.refresh_token = refresh_token
            self.scope = scope
    
    class TokenData:
        """Token data model for internal use."""
        
        def __init__(self, username: str | None = None, user_id: str | int | None = None,
                     scopes: list[str] | None = None, expires_at: datetime | None = None):
            self.username = username
            self.user_id = user_id
            self.scopes = scopes or []
            self.expires_at = expires_at
    
    class User:
        """Basic user model."""
        
        def __init__(self, username: str, email: str | None = None,
                     full_name: str | None = None, disabled: bool = False,
                     roles: list[str] | None = None, 
                     permissions: list[str] | None = None,
                     scopes: list[str] | None = None):
            """Initialize user."""
            self.username = username
            self.email = email
            self.full_name = full_name
            self.disabled = disabled
            self.roles = roles or []
            self.permissions = permissions or []
            self.scopes = scopes or []
    
    class UserInDB(User):
        """User model with hashed password for database storage."""
        
        def __init__(self, hashed_password: str, **kwargs):
            super().__init__(**kwargs)
            self.hashed_password = hashed_password
