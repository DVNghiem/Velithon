# Velithon Authentication Guide

Velithon provides a comprehensive, modular authentication system inspired by FastAPI's design patterns. The system includes multiple authentication schemes, role-based permissions, automatic OpenAPI documentation integration, and enterprise-grade security features.

## Overview

The Velithon authentication system is designed with security, flexibility, and ease of use in mind. It provides:

- **Multiple Authentication Schemes**: JWT Bearer, HTTP Basic, API Key, OAuth2
- **Role-Based Access Control (RBAC)**: Fine-grained permissions and role management
- **Automatic OpenAPI Integration**: Security schemes automatically documented in Swagger UI
- **Middleware Integration**: Built-in security middleware for headers and error handling
- **Extensible Design**: Easy to customize and extend for specific use cases
- **Production Ready**: Secure defaults, proper error handling, and performance optimized

## Architecture

The authentication system consists of several key components:

1. **Security Schemes** (`velithon.security.auth`): Handle credential extraction and validation
2. **User Models** (`velithon.security.models`): Structured user data representation
3. **JWT Handler** (`velithon.security.jwt`): Token creation, validation, and management
4. **Permissions** (`velithon.security.permissions`): Role and permission-based authorization
5. **Middleware** (`velithon.middleware.auth`): Request/response processing and security headers
6. **Dependencies** (`velithon.security.dependencies`): Reusable authentication and authorization functions

## Quick Start

### Basic Setup

To use authentication in your Velithon application, start by enabling the built-in security middleware:

```python
from velithon import Velithon

# Enable security features with default configuration
app = Velithon(
    title="My Secure App",
    description="A secure API with authentication",
    version="1.0.0",
    include_security_middleware=True,  # Enables AuthenticationMiddleware and SecurityMiddleware
)
```

### Complete Minimal Example

Here's a complete working example with JWT authentication:

```python
from typing import Annotated
from datetime import datetime, timedelta
from velithon import Velithon
from velithon.security import (
    HTTPBearer, JWTHandler, User, UserInDB, 
    get_password_hash, verify_password,
    AuthenticationError
)
from velithon.responses import JSONResponse

# Configuration
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize app and security components
app = Velithon(title="Secure API", include_security_middleware=True)
jwt_handler = JWTHandler(
    secret_key=SECRET_KEY,
    algorithm=ALGORITHM,
    access_token_expire=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
)
bearer_scheme = HTTPBearer()

# Fake user database (replace with real database)
fake_users_db = {
    "admin": UserInDB(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=get_password_hash("admin123"),
        roles=["admin"],
        permissions=["read", "write", "admin"]
    )
}

# Authentication functions
def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = fake_users_db.get(username)
    if user and verify_password(password, user.hashed_password):
        return user
    return None

async def get_current_user(request) -> User:
    """Extract and validate JWT token from request"""
    try:
        # Extract token from Authorization header
        token = await bearer_scheme(request)
        
        # Decode and validate token
        payload = jwt_handler.decode_token(token)
        username = payload.get("sub")
        
        if username is None:
            raise AuthenticationError("Invalid token: missing subject")
        
        # Get user from database
        user = fake_users_db.get(username)
        if user is None:
            raise AuthenticationError("User not found")
        
        # Convert to public User model (without password hash)
        return User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            roles=user.roles,
            permissions=user.permissions
        )
    except Exception as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")

# Endpoints
@app.post("/login")
async def login(username: str, password: str):
    """Authenticate user and return JWT token"""
    user = authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Invalid username or password")
    
    # Create JWT token
    token_data = {"sub": user.username}
    access_token = jwt_handler.create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "username": user.username,
            "email": user.email,
            "roles": user.roles
        }
    }

@app.get("/")
async def public_endpoint():
    """Public endpoint accessible without authentication"""
    return {"message": "This is a public endpoint"}

@app.get("/protected")
async def protected_endpoint(
    current_user: Annotated[User, get_current_user]
):
    """Protected endpoint requiring valid JWT token"""
    return {
        "message": f"Hello, {current_user.full_name}!",
        "user": current_user.username,
        "roles": current_user.roles
    }

@app.get("/admin")
async def admin_endpoint(
    current_user: Annotated[User, get_current_user]
):
    """Admin-only endpoint"""
    if "admin" not in current_user.roles:
        raise AuthenticationError("Admin access required")
    
    return {
        "message": "Admin access granted",
        "users": list(fake_users_db.keys())
    }

```

This complete example provides:
- JWT-based authentication
- Login endpoint for token generation
- Protected endpoints with user validation
- Role-based access control
- Automatic OpenAPI documentation

## Authentication Schemes

Velithon supports multiple authentication schemes that can be used individually or combined:

### 1. JWT Bearer Token Authentication

The most common authentication method for modern APIs. Supports stateless authentication with signed tokens.

```python
from velithon.security import HTTPBearer

# Initialize Bearer scheme
bearer_scheme = HTTPBearer(
    scheme_name="JWT Bearer",  # Custom name for OpenAPI docs
    description="JWT token authentication",
    auto_error=True  # Automatically raise errors for missing/invalid tokens
)

# Usage in dependency function
async def get_current_user_bearer(request) -> User:
    """Extract JWT token from Authorization: Bearer <token> header"""
    token = await bearer_scheme(request)
    
    try:
        # Validate token and extract user info
        payload = jwt_handler.decode_token(token)
        username = payload.get("sub")
        
        # Fetch user from database/cache
        user = await get_user_by_username(username)
        if not user:
            raise AuthenticationError("User not found")
            
        return user
    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except InvalidTokenError:
        raise AuthenticationError("Invalid token")

# Use in endpoint
@app.get("/user/profile")
async def get_profile(
    current_user: Annotated[User, get_current_user_bearer]
):
    return {"profile": current_user.dict()}
```

**Bearer Token Features:**
- Automatic `Authorization: Bearer <token>` header parsing
- Built-in error handling for malformed headers
- OpenAPI documentation with "Authorize" button
- Stateless authentication
- Supports refresh token patterns

### 2. HTTP Basic Authentication

Traditional username/password authentication using HTTP Basic Auth. Suitable for simple APIs or internal services.

```python
from velithon.security import HTTPBasic
import base64

# Initialize Basic Auth scheme
basic_scheme = HTTPBasic(
    scheme_name="HTTP Basic",
    description="Username and password authentication",
    auto_error=True
)

# Usage in dependency function
async def get_current_user_basic(request) -> User:
    """Extract credentials from Authorization: Basic <base64> header"""
    credentials = await basic_scheme(request)
    # credentials is a string in format "username:password"
    username, password = credentials.split(":", 1)
    
    # Authenticate user
    user = await authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Invalid username or password")
    
    return user

# Rate-limited login endpoint using Basic Auth
@app.post("/basic-login")
async def basic_login(
    current_user: Annotated[User, get_current_user_basic]
):
    """Login using HTTP Basic Auth and return user info"""
    return {
        "message": "Authentication successful",
        "user": current_user.username,
        "method": "basic_auth"
    }

# Protected endpoint with Basic Auth
@app.get("/basic-protected")
async def basic_protected(
    current_user: Annotated[User, get_current_user_basic]
):
    return {"message": f"Hello {current_user.full_name}!", "auth_method": "basic"}
```

**Basic Auth Features:**
- Automatic `Authorization: Basic <credentials>` header parsing
- Built-in base64 decoding
- Username/password extraction
- Browser-compatible (shows login dialog)
- Simple integration for internal tools

### 3. API Key Authentication

Token-based authentication using custom headers. Perfect for service-to-service communication and third-party integrations.

```python
from velithon.security import APIKeyHeader

# Initialize API Key schemes with different headers
api_key_scheme = APIKeyHeader(
    name="X-API-Key",  # Header name
    scheme_name="API Key",
    description="API key for service authentication",
    auto_error=True
)

# Alternative API key in different header
service_key_scheme = APIKeyHeader(
    name="X-Service-Token",
    scheme_name="Service Token",
    description="Service-to-service authentication token"
)

# API key validation function
async def validate_api_key(api_key: str) -> User:
    """Validate API key and return associated user/service"""
    # Check against database or cache
    key_info = await get_api_key_info(api_key)
    if not key_info or not key_info.is_active:
        raise AuthenticationError("Invalid or inactive API key")
    
    # Check rate limits and permissions
    if await is_rate_limited(api_key):
        raise AuthenticationError("Rate limit exceeded")
    
    # Return service user or associated account
    return User(
        username=key_info.service_name,
        email=key_info.contact_email,
        roles=key_info.roles,
        permissions=key_info.permissions
    )

# Dependency function
async def get_current_user_api_key(request) -> User:
    """Extract and validate API key from X-API-Key header"""
    api_key = await api_key_scheme(request)
    return await validate_api_key(api_key)

# API endpoint for external services
@app.get("/api/v1/data")
async def get_data(
    current_user: Annotated[User, get_current_user_api_key],
    limit: int = 100
):
    """External API endpoint using API key authentication"""
    return {
        "data": await fetch_data_for_user(current_user, limit),
        "service": current_user.username,
        "auth_method": "api_key"
    }

# API key management endpoints
@app.post("/admin/api-keys")
async def create_api_key(
    current_user: Annotated[User, get_current_admin_user],
    key_request: APIKeyCreateRequest
):
    """Create new API key (admin only)"""
    new_key = await generate_api_key(
        service_name=key_request.service_name,
        permissions=key_request.permissions,
        expires_at=key_request.expires_at
    )
    return {"api_key": new_key.key, "expires_at": new_key.expires_at}
```

**API Key Features:**
- Custom header name configuration
- Service-to-service authentication
- Rate limiting integration
- Permission scoping
- Key rotation and expiration
- Audit logging support

### 4. OAuth2 Password Bearer

OAuth2-compliant token authentication. Provides standardized token exchange and refresh patterns.

```python
from velithon.security import OAuth2PasswordBearer

# Initialize OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/oauth/token",  # Token endpoint URL
    scheme_name="OAuth2",
    description="OAuth2 password bearer authentication",
    scopes={
        "read": "Read access to resources",
        "write": "Write access to resources", 
        "admin": "Administrative access"
    }
)

# OAuth2 token endpoint
@app.post("/oauth/token")
async def oauth_token(
    username: str,
    password: str,
    scope: str = "",
    grant_type: str = "password"
):
    """OAuth2 token endpoint"""
    if grant_type != "password":
        raise AuthenticationError("Unsupported grant type")
    
    # Authenticate user
    user = await authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    # Parse and validate requested scopes
    requested_scopes = scope.split() if scope else []
    granted_scopes = []
    
    for requested_scope in requested_scopes:
        if requested_scope in user.permissions:
            granted_scopes.append(requested_scope)
    
    # Create token with scopes
    token_data = {
        "sub": user.username,
        "scopes": granted_scopes
    }
    access_token = jwt_handler.create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": " ".join(granted_scopes),
        "refresh_token": generate_refresh_token(user.username)
    }

async def get_current_user_oauth2(request) -> User:
    """Extract OAuth2 token and validate basic authentication"""
    token = await oauth2_scheme(request)
    
    try:
        payload = jwt_handler.decode_token(token)
        username = payload.get("sub")
        
        user = await get_user_by_username(username)
        if not user:
            raise AuthenticationError("User not found")
        
        return user
        
    except Exception as e:
        raise AuthenticationError(f"OAuth2 validation failed: {str(e)}")

# Basic OAuth2 endpoints (scope validation not fully implemented yet)
@app.get("/oauth/read-data")
async def read_data(
    current_user: Annotated[User, get_current_user_oauth2]
):
    """Basic OAuth2 protected endpoint"""
    return {"data": "sensitive data", "user": current_user.username}

@app.post("/oauth/write-data") 
async def write_data(
    current_user: Annotated[User, get_current_user_oauth2],
    data: dict
):
    """Basic OAuth2 protected endpoint"""
    await save_data(data, current_user)
    return {"message": "Data saved successfully"}
```

**OAuth2 Features:**
- Standard OAuth2 password flow
- Basic token authentication
- OpenAPI OAuth2 documentation
- Token introspection endpoints

*Note: Advanced scope validation and refresh token support are planned for future releases.*

## User Management

### User Models and Data Structures

Velithon provides structured user models for different use cases:

```python
from velithon.security import User, UserInDB, UserCreate, Token, TokenData
from typing import Optional
from datetime import datetime

# Base user model - for API responses (excludes sensitive data)
user = User(
    username="john_doe",
    email="john@example.com", 
    full_name="John Doe",
    disabled=False,
    roles=["user", "editor"],
    permissions=["read", "write", "edit_own"]
)

# Database user model - includes hashed password for storage
user_db = UserInDB(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe",
    hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/r2.z6OQSu",
    disabled=False,
    roles=["user", "editor"],
    permissions=["read", "write", "edit_own"],
    created_at=datetime.utcnow(),
    last_login=datetime.utcnow()
)

# User creation model - for registration endpoints
new_user = UserCreate(
    username="jane_doe",
    email="jane@example.com", 
    password="secure_password_123",  # Plain text password (will be hashed)
    full_name="Jane Doe",
    roles=["user"]  # Default roles
)

# Token models for API responses
token = Token(
    access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    token_type="bearer",
    expires_in=3600
)

token_data = TokenData(
    username="john_doe",
    scopes=["read", "write"],
    expires_at=datetime.utcnow()
)
```

### Advanced User Model Customization

Create custom user models for specific requirements:

```python
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any
from datetime import datetime
from velithon.security import User

class OrganizationUser(User):
    """Extended user model with organization context"""
    organization_id: str
    department: str
    job_title: Optional[str] = None
    manager_id: Optional[str] = None
    employee_id: str
    access_level: int = Field(ge=1, le=5, description="Access level 1-5")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ServiceAccount(User):
    """Service account model for API integrations"""
    service_type: str
    api_version: str
    rate_limit: int = Field(default=1000, description="Requests per hour")
    ip_whitelist: List[str] = Field(default_factory=list)
    webhook_urls: List[str] = Field(default_factory=list)

# Usage with custom models
async def get_org_user(request) -> OrganizationUser:
    """Get user with organization context"""
    base_user = await get_current_user(request)
    
    # Fetch additional organization data
    org_data = await get_user_organization_data(base_user.username)
    
    return OrganizationUser(
        **base_user.dict(),
        organization_id=org_data.org_id,
        department=org_data.department,
        job_title=org_data.job_title,
        employee_id=org_data.employee_id,
        access_level=org_data.access_level
    )

@app.get("/org/team-members")
async def get_team_members(
    current_user: Annotated[OrganizationUser, get_org_user]
):
    """Get team members in same department"""
    return await get_department_members(
        current_user.organization_id, 
        current_user.department
    )
```

### Password Security and Hashing

Velithon uses industry-standard bcrypt for password hashing:

```python
from velithon.security import hash_password, verify_password, get_password_hash
import secrets
import string

# Hash passwords with automatic salt generation
def secure_hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return hash_password(password)  # Uses bcrypt with random salt

# Verify passwords securely
def authenticate_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return verify_password(plain_password, hashed_password)

# Password strength validation
def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password meets security requirements"""
    issues = []
    score = 0
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    else:
        score += 1
        
    if not any(c.isupper() for c in password):
        issues.append("Password must contain uppercase letters")
    else:
        score += 1
        
    if not any(c.islower() for c in password):
        issues.append("Password must contain lowercase letters") 
    else:
        score += 1
        
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain numbers")
    else:
        score += 1
        
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        issues.append("Password must contain special characters")
    else:
        score += 1
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "strength_score": score,
        "strength_level": ["Very Weak", "Weak", "Fair", "Good", "Strong"][score]
    }

# Generate secure passwords
def generate_secure_password(length: int = 16) -> str:
    """Generate cryptographically secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Generate API keys
def generate_api_key(prefix: str = "vth", length: int = 32) -> str:
    """Generate secure API key with prefix"""
    key_part = secrets.token_urlsafe(length)
    return f"{prefix}_{key_part}"

# Password reset token generation
def generate_reset_token() -> str:
    """Generate secure password reset token"""
    return secrets.token_urlsafe(32)

# Example usage in user registration
@app.post("/register")
async def register_user(user_data: UserCreate):
    """Register new user with password validation"""
    
    # Validate password strength
    password_check = validate_password_strength(user_data.password)
    if not password_check["is_valid"]:
        raise ValidationError(f"Weak password: {', '.join(password_check['issues'])}")
    
    # Check if user already exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        raise AuthenticationError("Username already registered")
    
    existing_email = await get_user_by_email(user_data.email)
    if existing_email:
        raise AuthenticationError("Email already registered")
    
    # Hash password and create user
    hashed_password = hash_password(user_data.password)
    
    new_user = UserInDB(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        roles=user_data.roles or ["user"],
        permissions=["read"],  # Default permissions
        created_at=datetime.utcnow()
    )
    
    # Save to database
    user_id = await save_user(new_user)
    
    # Send welcome email
    await send_welcome_email(new_user.email, new_user.full_name)
    
    return {
        "message": "User registered successfully",
        "user_id": user_id,
        "username": new_user.username
    }
```

### User Database Integration

Example integration with popular databases:

```python
# PostgreSQL with asyncpg
import asyncpg
from datetime import datetime
from typing import Optional

class PostgreSQLUserProvider:
    def __init__(self, connection_pool: asyncpg.Pool):
        self.pool = connection_pool
    
    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Fetch user from PostgreSQL database"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT username, email, full_name, hashed_password, 
                       disabled, roles, permissions, created_at, last_login
                FROM users WHERE username = $1
                """, username
            )
            
            if row:
                return UserInDB(
                    username=row['username'],
                    email=row['email'],
                    full_name=row['full_name'],
                    hashed_password=row['hashed_password'],
                    disabled=row['disabled'],
                    roles=row['roles'],
                    permissions=row['permissions'],
                    created_at=row['created_at'],
                    last_login=row['last_login']
                )
            return None
    
    async def create_user(self, user: UserInDB) -> str:
        """Create new user in database"""
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(
                """
                INSERT INTO users (username, email, full_name, hashed_password, 
                                 roles, permissions, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                user.username, user.email, user.full_name, 
                user.hashed_password, user.roles, user.permissions, 
                user.created_at
            )
            return str(user_id)
    
    async def update_last_login(self, username: str) -> None:
        """Update user's last login timestamp"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = $1 WHERE username = $2",
                datetime.utcnow(), username
            )

# MongoDB with motor
import motor.motor_asyncio
from bson import ObjectId

class MongoUserProvider:
    def __init__(self, database: motor.motor_asyncio.AsyncIOMotorDatabase):
        self.db = database
        self.users = database.users
    
    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Fetch user from MongoDB"""
        doc = await self.users.find_one({"username": username})
        if doc:
            doc.pop('_id', None)  # Remove MongoDB ObjectId
            return UserInDB(**doc)
        return None
    
    async def create_user(self, user: UserInDB) -> str:
        """Create new user in MongoDB"""
        user_dict = user.dict()
        result = await self.users.insert_one(user_dict)
        return str(result.inserted_id)

# Redis for session/token management
import aioredis
import json
from datetime import timedelta

class RedisSessionManager:
    def __init__(self, redis_client: aiorededis.Redis):
        self.redis = redis_client
    
    async def store_session(self, session_id: str, user_data: dict, ttl: timedelta):
        """Store user session in Redis"""
        await self.redis.setex(
            f"session:{session_id}",
            int(ttl.total_seconds()),
            json.dumps(user_data)
        )
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve user session from Redis"""
        data = await self.redis.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    
    async def invalidate_session(self, session_id: str):
        """Remove session from Redis"""
        await self.redis.delete(f"session:{session_id}")
```

## Permissions and Role-Based Access Control

Velithon provides a basic permission system for role-based access control (RBAC).

### Basic Permission System

```python
from velithon.security import require_permission, Permission, PermissionChecker
from typing import Annotated

# Define permissions as constants
class Permissions:
    READ = "read"
    WRITE = "write" 
    DELETE = "delete"
    ADMIN = "admin"
    USER_MANAGE = "user:manage"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"

# Simple permission-based authorization
@app.get("/admin/users")
async def list_users(
    current_user: Annotated[User, get_current_user],
    _: Annotated[None, require_permission(Permissions.USER_MANAGE)]
):
    """Only users with 'user:manage' permission can access this"""
    return {"users": await get_all_users()}

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Annotated[User, get_current_user],
    _: Annotated[None, require_permission(Permissions.DELETE)]
):
    """Requires 'delete' permission"""
    await delete_user_by_id(user_id)
    return {"message": f"User {user_id} deleted"}
```

### Basic Role Checking

```python
from typing import List

def check_user_role(user: User, required_role: str) -> bool:
    """Check if user has required role"""
    return required_role in user.roles

def check_user_permission(user: User, required_permission: str) -> bool:
    """Check if user has required permission"""
    return required_permission in user.permissions

# Simple role-based endpoint protection
@app.get("/admin/dashboard")
async def admin_dashboard(
    current_user: Annotated[User, get_current_user]
):
    """Admin dashboard - requires admin role"""
    if "admin" not in current_user.roles:
        raise AuthenticationError("Admin access required")
    
    return {"dashboard": "admin_data"}

@app.get("/user/profile")
async def user_profile(
    current_user: Annotated[User, get_current_user]
):
    """User profile - requires read permission"""
    if "read" not in current_user.permissions:
        raise AuthenticationError("Read permission required")
    
    return {"profile": current_user.dict()}
```

*Note: Advanced RBAC features like role inheritance, attribute-based access control (ABAC), time-based permissions, and IP restrictions are planned for future releases.*

### Basic Permission System

```python
from velithon.security import require_permission, Permission, PermissionChecker
from typing import Annotated

# Define permissions as constants
class Permissions:
    READ = "read"
    WRITE = "write" 
    DELETE = "delete"
    ADMIN = "admin"
    USER_MANAGE = "user:manage"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"

# Simple permission-based authorization
@app.get("/admin/users")
async def list_users(
    current_user: Annotated[User, get_current_user],
    _: Annotated[None, require_permission(Permissions.USER_MANAGE)]
):
    """Only users with 'user:manage' permission can access this"""
    return {"users": await get_all_users()}

@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Annotated[User, get_current_user],
    _: Annotated[None, require_permission(Permissions.DELETE)]
):
    """Requires 'delete' permission"""
    await delete_user_by_id(user_id)
    return {"message": f"User {user_id} deleted"}
```
## JWT Token Handling

### JWT Configuration

```python
from velithon.security import JWTHandler
from datetime import timedelta

jwt_handler = JWTHandler(
    secret_key="your-secret-key",
    algorithm="HS256",
    access_token_expire=timedelta(minutes=30)
)

# Create token
token = jwt_handler.encode_token({"sub": "username", "scope": "user"})

# Decode token
payload = jwt_handler.decode_token(token)
```

### Token-Based Login Flow

```python
@app.post("/token")
async def login(username: str, password: str):
    # Authenticate user
    user = authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    # Create token
    token = jwt_handler.encode_token({"sub": user.username})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800
    }
```

## Middleware

Velithon includes two security middleware components:

### SecurityMiddleware

Adds security headers and handles CORS:

```python
from velithon.middleware.auth import SecurityMiddleware
from velithon.middleware import Middleware

app = Velithon(
    middleware=[
        Middleware(SecurityMiddleware)
    ]
)
```

### AuthenticationMiddleware

Handles authentication errors gracefully:

```python
from velithon.middleware.auth import AuthenticationMiddleware
from velithon.middleware import Middleware

app = Velithon(
    middleware=[
        Middleware(AuthenticationMiddleware)
    ]
)
```

## OpenAPI Integration and Swagger UI Authentication

Velithon automatically integrates authentication schemes with OpenAPI/Swagger documentation, providing interactive authentication in the Swagger UI.

### Basic OpenAPI Integration

When you enable security middleware, Velithon provides basic OpenAPI documentation for authentication schemes:

```python
from velithon import Velithon
from velithon.security import HTTPBearer, HTTPBasic, APIKeyHeader, OAuth2PasswordBearer

app = Velithon(
    title="My Secure API",
    description="API with comprehensive authentication",
    version="1.0.0",
    include_security_middleware=True  # Enables automatic OpenAPI security integration
)

# Define authentication schemes
bearer_auth = HTTPBearer()
basic_auth = HTTPBasic()
api_key_auth = APIKeyHeader(name="X-API-Key")
oauth2_auth = OAuth2PasswordBearer(
    tokenUrl="/token",
    scopes={
        "read": "Read access to data",
        "write": "Write access to data",
        "admin": "Administrative access"
    }
)
```

### Security Requirements in Swagger UI

Authentication dependencies are automatically detected and documented:

```python
from typing import Annotated

# JWT Bearer authentication
async def get_current_user_jwt(request) -> User:
    token = await bearer_auth(request)
    # ... validation logic
    return user

# Basic authentication
async def get_current_user_basic(request) -> User:
    credentials = await basic_auth(request)
    # credentials is a string in format "username:password"
    username, password = credentials.split(":", 1)
    return user

# API Key authentication
async def get_current_user_api_key(request) -> User:
    api_key = await api_key_auth(request)
    # ... validation logic
    return user

# Protected endpoints with automatic security documentation
@app.get("/protected/jwt", 
         summary="JWT Protected Endpoint",
         description="Requires valid JWT Bearer token")
async def jwt_protected(
    current_user: Annotated[User, get_current_user_jwt]
):
    """
    This endpoint requires JWT Bearer authentication.
    The Swagger UI will show a lock icon and allow token input.
    """
    return {"message": f"Hello {current_user.username}", "auth_method": "jwt"}

@app.get("/protected/basic",
         summary="Basic Auth Protected Endpoint", 
         description="Requires HTTP Basic authentication")
async def basic_protected(
    current_user: Annotated[User, get_current_user_basic]
):
    """
    This endpoint requires HTTP Basic authentication.
    The Swagger UI will show a lock icon with username/password fields.
    """
    return {"message": f"Hello {current_user.username}", "auth_method": "basic"}

@app.get("/protected/api-key",
         summary="API Key Protected Endpoint",
         description="Requires X-API-Key header")
async def api_key_protected(
    current_user: Annotated[User, get_current_user_api_key]
):
    """
    This endpoint requires API Key authentication.
    The Swagger UI will show a lock icon with API key input field.
    """
    return {"message": f"Hello {current_user.username}", "auth_method": "api_key"}
```

### Using Swagger UI for Authentication Testing

#### 1. JWT Bearer Token Authentication

When you open Swagger UI (`/docs`), you'll see:

1. **Lock icons** next to protected endpoints
2. **Authorize button** at the top right
3. **Security schemes** in the authorization modal

To test JWT authentication in Swagger UI:

```python
# First, create a login endpoint that returns a token
@app.post("/auth/login",
          summary="User Login",
          description="Authenticate and receive JWT token")
async def login(username: str, password: str):
    """
    Login endpoint for Swagger UI testing.
    
    Steps to use:
    1. Call this endpoint with your credentials
    2. Copy the returned access_token
    3. Click 'Authorize' in Swagger UI
    4. Paste token in Bearer field (without 'Bearer ' prefix)
    5. Click 'Authorize' and then 'Close'
    6. Now you can test protected endpoints
    """
    user = await authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    token = jwt_handler.create_access_token({"sub": user.username})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800,
        "instructions": "Copy this token and use it in the Swagger UI Authorize button"
    }

# Example of endpoint with detailed auth documentation
@app.get("/user/profile",
         summary="Get User Profile",
         description="Get current user's profile information",
         responses={
             200: {"description": "User profile retrieved successfully"},
             401: {"description": "Authentication required"},
             403: {"description": "Access forbidden"}
         })
async def get_user_profile(
    current_user: Annotated[User, get_current_user_jwt]
):
    """
    Get current authenticated user's profile.
    
    **Authentication Required**: JWT Bearer token
    
    **How to test in Swagger UI**:
    1. First call `/auth/login` to get a token
    2. Click the 🔒 icon next to this endpoint or the 'Authorize' button
    3. Enter your token in the Bearer field
    4. Test this endpoint
    """
    return {
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "permissions": current_user.permissions
    }
```

#### 2. OAuth2 with Scopes in Swagger UI

For OAuth2 with scopes, Swagger UI provides an advanced authorization interface:

```python
from velithon.security import OAuth2PasswordBearer

# OAuth2 scheme with scopes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/oauth/token",
    scopes={
        "profile:read": "Read user profile",
        "profile:write": "Update user profile", 
        "admin:users": "Manage users",
        "admin:system": "System administration"
    }
)

@app.post("/oauth/token",
          summary="OAuth2 Token Endpoint",
          description="Get OAuth2 access token with scopes")
async def oauth_token(username: str, password: str, scope: str = ""):
    """
    OAuth2 token endpoint for Swagger UI.
    
    **For Swagger UI OAuth2 flow**:
    1. Click 'Authorize' button
    2. Select the scopes you need
    3. Enter your username and password
    4. Click 'Authorize'
    
    The scopes will be automatically included in requests.
    """
    user = await authenticate_user(username, password)
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    # Parse requested scopes
    requested_scopes = scope.split() if scope else []
    granted_scopes = []
    
    # Grant scopes based on user permissions
    scope_permission_map = {
        "profile:read": "read",
        "profile:write": "write", 
        "admin:users": "admin",
        "admin:system": "admin"
    }
    
    for requested_scope in requested_scopes:
        required_permission = scope_permission_map.get(requested_scope)
        if required_permission in user.permissions:
            granted_scopes.append(requested_scope)
    
    token_data = {
        "sub": user.username,
        "scopes": granted_scopes
    }
    
    access_token = jwt_handler.create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": " ".join(granted_scopes)
    }

@app.get("/profile",
         summary="Get Profile (OAuth2)",
         description="Get user profile with OAuth2 authentication")
async def get_profile_oauth2(
    current_user: Annotated[User, get_current_user_oauth2]
):
    """
    Requires OAuth2 authentication.
    
    **Swagger UI will**:
    - Show this endpoint requires OAuth2
    - Allow OAuth2 authorization
    """
    return current_user.dict()

@app.put("/profile",
         summary="Update Profile (OAuth2)",
         description="Update user profile with OAuth2 authentication")
async def update_profile_oauth2(
    profile_data: dict,
    current_user: Annotated[User, get_current_user_oauth2]
):
    """
    Requires OAuth2 authentication.
    """
    await update_user_profile(current_user.username, profile_data)
    return {"message": "Profile updated successfully"}
```

#### 3. Multiple Authentication Methods

You can support multiple authentication methods on the same endpoint:

```python
async def get_current_user_flexible(request) -> User:
    """Support multiple authentication methods"""
    
    # Try JWT Bearer first
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            return await get_current_user_jwt(request)
        except AuthenticationError:
            pass
    
    # Try API Key
    if "X-API-Key" in request.headers:
        try:
            return await get_current_user_api_key(request)
        except AuthenticationError:
            pass
    
    # Try Basic Auth
    if auth_header.startswith("Basic "):
        try:
            return await get_current_user_basic(request)
        except AuthenticationError:
            pass
    
    raise AuthenticationError("Authentication required")

@app.get("/flexible-auth",
         summary="Flexible Authentication Endpoint",
         description="Accepts JWT, API Key, or Basic authentication")
async def flexible_auth_endpoint(
    current_user: Annotated[User, get_current_user_flexible]
):
    """
    This endpoint accepts multiple authentication methods:
    
    **JWT Bearer**: Add `Authorization: Bearer <token>` header
    **API Key**: Add `X-API-Key: <key>` header  
    **Basic Auth**: Add `Authorization: Basic <credentials>` header
    
    **In Swagger UI**:
    - You can use any of the configured authentication methods
    - Try different auth types by clicking the lock icons
    """
    return {
        "message": f"Authenticated as {current_user.username}",
        "available_methods": ["JWT Bearer", "API Key", "Basic Auth"]
    }
```

### Custom OpenAPI Security Documentation

You can customize how security schemes appear in the OpenAPI spec:

### Basic OpenAPI Customization

You can use the standard authentication schemes provided by Velithon:

```python
from velithon.security import APIKeyHeader

# API key scheme with custom configuration
api_key_auth = APIKeyHeader(
    name="X-API-Key",
    auto_error=True
)

@app.get("/api/external-data",
         summary="External Data Access",
         description="Access data using service API key")
async def external_data_access(
    current_user: Annotated[User, get_current_user_api_key]
):
    """
    External API endpoint requiring service API key.
    
    **API Key Requirements**:
    - Must be a valid service API key
    - Include in X-API-Key header
    - Contact support for API key provisioning
    
    **Swagger UI Usage**:
    1. Click the lock icon 🔒
    2. Enter your API key in the X-API-Key field
    3. Click Authorize
    """
    return {
        "data": "sensitive external data",
        "service": current_user.username
    }
```

### Swagger UI Configuration

Velithon automatically generates OpenAPI documentation for your authentication schemes when you enable security middleware.

### Testing Authentication in Swagger UI

Here's a complete example showing how users can test authentication:

```python
@app.get("/test/public", 
         summary="Public Endpoint",
         description="No authentication required - test that API is working")
async def test_public():
    """
    **Public endpoint** - no authentication required.
    
    Use this to verify the API is accessible before testing authenticated endpoints.
    """
    return {
        "message": "API is working!",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication": "not required"
    }

@app.get("/test/auth-status",
         summary="Authentication Status",
         description="Check your current authentication status")
async def test_auth_status(
    current_user: Annotated[User, get_current_user_flexible]
):
    """
    **Test your authentication** - shows your current auth status.
    
    **Steps to test**:
    1. First try without authentication (should fail)
    2. Get a token from `/auth/login`
    3. Click 'Authorize' and enter your token
    4. Try this endpoint again (should succeed)
    """
    return {
        "authenticated": True,
        "user": current_user.username,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
        "message": "Authentication successful!"
    }

@app.get("/test/permissions/{permission}",
         summary="Test Permission",
         description="Test if you have a specific permission")
async def test_permission(
    permission: str,
    current_user: Annotated[User, get_current_user_flexible]
):
    """
    **Test specific permissions** - check if you have access to specific resources.
    
    **Common permissions to test**:
    - `read` - Basic read access
    - `write` - Write access
    - `admin` - Administrative access
    
    **Try different values** in the permission parameter to test your access levels.
    """
    has_permission = permission in current_user.permissions
    
    return {
        "permission": permission,
        "granted": has_permission,
        "user_permissions": current_user.permissions,
        "message": f"Permission '{permission}' {'granted' if has_permission else 'denied'}"
    }
```

### Swagger UI Authentication Flow Summary

1. **Setup**: Enable `include_security_middleware=True` in your Velithon app
2. **Login**: Use the `/auth/login` endpoint to get a token
3. **Authorize**: Click the "Authorize" button in Swagger UI
4. **Enter Credentials**: Paste your token or enter API key/username+password
5. **Test**: Lock icons 🔒 will show green when authenticated
6. **Verify**: Use test endpoints to verify your authentication status

The Swagger UI will automatically:
- Show lock icons on protected endpoints
- Display available authentication methods
- Allow interactive authentication testing
- Show authentication requirements in endpoint documentation
- Provide error messages for authentication failures

## Custom Authentication

### Custom Security Scheme

```python
from velithon.security.auth import SecurityScheme

class CustomKeyAuth(SecurityScheme):
    def __init__(self, header_name: str = "X-Custom-Key"):
        self.header_name = header_name
    
    def __call__(self, request) -> str:
        key = request.headers.get(self.header_name)
        if not key:
            raise AuthenticationError("Missing custom key")
        return key
    
    def get_openapi_schema(self) -> dict:
        return {
            "type": "apiKey",
            "in": "header", 
            "name": self.header_name
        }

# Use custom scheme
custom_auth = CustomKeyAuth("X-My-Key")
```

### Custom User Provider

```python
class DatabaseUserProvider:
    async def get_user(self, username: str) -> User | None:
        # Fetch from database
        user_record = await db.fetch_user(username)
        if user_record and verify_password(password, user_record["hashed_password"]):
            return User(**user_record)
        return None

# Use in dependency
user_provider = DatabaseUserProvider()

async def get_current_user(request) -> User:
    token = bearer_scheme(request)
    payload = jwt_handler.decode_token(token.credentials)
    username = payload.get("sub")
    
    user = await user_provider.get_user(username)
    if not user:
        raise AuthenticationError("User not found")
    
    return user
```

## Error Handling

### Authentication Errors

```python
from velithon.security import AuthenticationError, PermissionError

# Raise authentication errors
raise AuthenticationError("Invalid token")
raise AuthenticationError("Token expired") 
raise PermissionError("Insufficient permissions")
```

### Custom Error Handling

```python
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request, exc):
    return JSONResponse(
        {"error": "Authentication failed", "detail": str(exc)},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"}
    )

@app.exception_handler(PermissionError)  
async def permission_error_handler(request, exc):
    return JSONResponse(
        {"error": "Access denied", "detail": str(exc)},
        status_code=403
    )
```

## Best Practices

### 1. Use Environment Variables for Secrets

```python
import os

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key-for-dev")
jwt_handler = JWTHandler(secret_key=SECRET_KEY)
```

### 2. Implement Token Refresh

```python
@app.post("/refresh")
async def refresh_token(
    current_user: Annotated[User, get_current_user]
):
    new_token = jwt_handler.encode_token({"sub": current_user.username})
    return {"access_token": new_token, "token_type": "bearer"}
```

### 3. Use Database Sessions

```python
async def get_current_active_user(
    current_user: Annotated[User, get_current_user]
) -> User:
    if current_user.disabled:
        raise AuthenticationError("User account disabled")
    return current_user
```

### 4. Rate Limiting for Auth Endpoints

```python
from velithon.middleware import RateLimitMiddleware

app = Velithon(
    middleware=[
        Middleware(RateLimitMiddleware, 
                  rate_limit={"login": "5/minute"})
    ]
)
```

## Examples

Check out the complete examples:

- `examples/simple_auth_example.py` - Basic JWT authentication
- `examples/authentication_example.py` - Comprehensive authentication demo

## Security Considerations

### Production Security Checklist

Before deploying Velithon authentication to production, ensure these security measures are in place:

#### Environment and Configuration
- [ ] Use strong, unique JWT secret keys (minimum 32 characters)
- [ ] Store secrets in environment variables or secure vaults
- [ ] Enable HTTPS/TLS for all communications
- [ ] Configure proper CORS policies
- [ ] Set appropriate token expiration times
- [ ] Enable security headers middleware
- [ ] Configure rate limiting on authentication endpoints

#### Database Security
- [ ] Use connection pooling with proper limits
- [ ] Enable database encryption at rest
- [ ] Configure database access controls
- [ ] Implement database connection monitoring
- [ ] Set up database backups and recovery
- [ ] Use read replicas for user lookups if needed

#### Monitoring and Logging
- [ ] Configure structured logging for all auth events
- [ ] Set up alerts for failed authentication attempts
- [ ] Monitor for suspicious login patterns
- [ ] Track API rate limit violations
- [ ] Log all privilege escalations
- [ ] Implement audit trails for sensitive operations

#### Infrastructure Security
- [ ] Use container security scanning
- [ ] Configure network policies
- [ ] Implement pod security policies (Kubernetes)
- [ ] Use non-root container users
- [ ] Enable resource limits and quotas
- [ ] Configure health checks and readiness probes


### Common Troubleshooting Issues

#### JWT Token Problems

**Problem**: "Invalid token" errors in production

**Solution**:
```python
def debug_jwt_token(token: str, secret: str):
    """Debug JWT token issues"""
    import jwt
    from datetime import datetime
    
    try:
        # Decode without verification to see payload
        unverified = jwt.decode(token, options={"verify_signature": False})
        print(f"Token payload: {unverified}")
        
        # Check expiration
        if 'exp' in unverified:
            exp_time = datetime.fromtimestamp(unverified['exp'])
            print(f"Token expires: {exp_time}")
            print(f"Current time: {datetime.utcnow()}")
            print(f"Is expired: {datetime.utcnow() > exp_time}")
        
        # Verify with secret
        verified = jwt.decode(token, secret, algorithms=["HS256"])
        print("Token is valid!")
        return verified
        
    except jwt.ExpiredSignatureError:
        print("Token has expired")
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
    
    return None
```

#### Performance Issues

**Problem**: Slow authentication response times

**Solutions**:
- Implement Redis caching for user lookups
- Use database connection pooling
- Add indexes to user lookup queries
- Consider read replicas for authentication data

**Monitoring code**:
```python
import time
import functools

def monitor_auth_performance(func):
    """Monitor authentication performance"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            if duration > 1.0:  # Alert on slow operations
                logger.warning(f"Slow auth operation: {func.__name__} took {duration:.2f}s")
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Auth error in {func.__name__} after {duration:.2f}s: {e}")
            raise
    return wrapper

@monitor_auth_performance
async def get_current_user(request):
    # Your authentication logic here
    pass
```

For complete deployment examples and troubleshooting guides, see the [Velithon Production Deployment Guide](./deployment.md).

## Implementation Status

This guide describes the current and planned features of Velithon's authentication system:

### ✅ Currently Implemented
- **Core Authentication Schemes**: HTTPBearer, HTTPBasic, APIKeyHeader, APIKeyQuery, APIKeyCookie
- **OAuth2 Support**: Basic OAuth2PasswordBearer and OAuth2AuthorizationCodeBearer
- **User Models**: User, UserInDB, UserCreate, Token, TokenData with Pydantic integration
- **JWT Handling**: Complete JWTHandler class with token creation, validation, and decoding
- **Password Security**: BCrypt hashing with passlib and PBKDF2 fallback
- **Basic Permissions**: Permission and PermissionChecker classes with require_permission
- **Security Middleware**: AuthenticationMiddleware and SecurityMiddleware
- **OpenAPI Integration**: Basic security scheme documentation in Swagger UI
- **Exception Handling**: Comprehensive authentication and authorization exceptions

### 🚧 Planned for Future Releases
- **Advanced OAuth2 Scopes**: Detailed scope validation and enforcement
- **Complex RBAC**: Role inheritance, hierarchical permissions, wildcard permissions
- **ABAC Features**: Attribute-based access control with policy evaluation
- **Time-based Permissions**: Business hours restrictions and access windows
- **IP-based Security**: IP whitelisting and geolocation restrictions
- **Advanced OpenAPI**: Custom security scheme documentation and enhanced Swagger UI integration
- **Rate Limiting**: Built-in rate limiting for authentication endpoints
- **Session Management**: Redis-based session storage and management
- **Audit Logging**: Comprehensive authentication event logging
- **Database Integration**: Pre-built integrations with popular databases

### 📚 Usage Recommendations
- Use the currently implemented features for production applications
- Basic JWT authentication with role-based permissions covers most use cases
- For advanced features, implement custom logic using the existing foundation
- Monitor this documentation for updates on new feature availability

