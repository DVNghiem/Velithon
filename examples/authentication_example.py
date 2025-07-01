"""Comprehensive Authentication Example for Velithon.

This example demonstrates the complete authentication system including:
1. JWT Bearer token authentication
2. Basic authentication
3. API Key authentication
4. OAuth2 Password Bearer flow
5. Role-based permissions
6. Protected endpoints with different security schemes
7. OpenAPI/Swagger documentation integration
8. User registration and login flows
"""

from datetime import datetime, timedelta
from typing import Annotated

from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.auth import AuthenticationMiddleware, SecurityMiddleware
from velithon.requests import Request
from velithon.responses import JSONResponse, HTMLResponse
from velithon.routing import Router
from velithon.security import (
    APIKeyHeader,
    AuthenticationError,
    AuthorizationError,
    HTTPBasic,
    HTTPBearer,
    JWTHandler,
    OAuth2PasswordBearer,
    TokenData,
    User,
    UserCreate,
    UserInDB,
    LoginRequest,
    hash_password,
    require_permission,
    verify_password,
)

# =============================================================================
# Configuration and Setup
# =============================================================================

# JWT Configuration
import os
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize JWT handler
jwt_handler = JWTHandler(secret_key=SECRET_KEY, algorithm=ALGORITHM)

# Security schemes
bearer_scheme = HTTPBearer()
basic_scheme = HTTPBasic()
api_key_scheme = APIKeyHeader(name="X-API-Key")
oauth2_scheme = OAuth2PasswordBearer(token_url="token")

# =============================================================================
# Mock Database and User Management
# =============================================================================

# In-memory user database (replace with real database in production)
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": hash_password("admin123"),
        "email": "admin@example.com",
        "full_name": "Administrator",
        "disabled": False,
        "roles": ["admin", "user"],
        "permissions": ["read", "write", "delete", "admin"],
    },
    "john": {
        "username": "john",
        "hashed_password": hash_password("secret123"),
        "email": "john@example.com",
        "full_name": "John Doe",
        "disabled": False,
        "roles": ["user"],
        "permissions": ["read", "write"],
    },
    "alice": {
        "username": "alice",
        "hashed_password": hash_password("alice456"),
        "email": "alice@example.com",
        "full_name": "Alice Smith",
        "disabled": True,
        "roles": ["user"],
        "permissions": ["read"],
    },
}

# API Keys database (replace with real database in production)
fake_api_keys_db = {
    "sk-1234567890abcdef": {
        "name": "Production API Key",
        "user": "admin",
        "permissions": ["read", "write"],
        "expires_at": None,
    },
    "sk-test123456789": {
        "name": "Test API Key",
        "user": "john",
        "permissions": ["read"],
        "expires_at": datetime.utcnow() + timedelta(days=30),
    },
}

def get_user(username: str) -> UserInDB | None:
    """Get user from database by username."""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> UserInDB | None:
    """Authenticate user with username and password."""
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def authenticate_api_key(api_key: str) -> UserInDB | None:
    """Authenticate user with API key."""
    if api_key not in fake_api_keys_db:
        return None
    
    key_info = fake_api_keys_db[api_key]
    
    # Check if API key is expired
    if key_info["expires_at"] and datetime.utcnow() > key_info["expires_at"]:
        return None
    
    user = get_user(key_info["user"])
    if user:
        # Override user permissions with API key permissions
        user.permissions = key_info["permissions"]
    
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    return jwt_handler.encode_token(to_encode)

# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user_jwt(request: Request) -> User:
    """Get current user from JWT token."""
    try:
        token = bearer_scheme(request)
        payload = jwt_handler.decode_token(token.credentials)
        username: str = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")
        token_data = TokenData(username=username)
    except Exception as exc:
        raise AuthenticationError("Invalid token") from exc
    
    user = get_user(username=token_data.username)
    if user is None:
        raise AuthenticationError("User not found")
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=user.roles,
        permissions=user.permissions,
    )

async def get_current_user_basic(request: Request) -> User:
    """Get current user from Basic authentication."""
    credentials = basic_scheme(request)
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=user.roles,
        permissions=user.permissions,
    )

async def get_current_user_api_key(request: Request) -> User:
    """Get current user from API key."""
    api_key = api_key_scheme(request)
    user = authenticate_api_key(api_key)
    if not user:
        raise AuthenticationError("Invalid API key")
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=user.roles,
        permissions=user.permissions,
    )

async def get_current_user_oauth2(request: Request) -> User:
    """Get current user from OAuth2 token."""
    oauth2_scheme(request)  # Validate the token is present
    return await get_current_user_jwt(request)

# =============================================================================
# API Endpoints
# =============================================================================

# Public endpoints
async def home():
    """Public home endpoint."""
    return HTMLResponse("""
    <html>
        <head><title>Velithon Authentication Example</title></head>
        <body>
            <h1>Velithon Authentication Example</h1>
            <p>This is a public endpoint. No authentication required.</p>
            <h2>Available Endpoints:</h2>
            <ul>
                <li><a href="/docs">API Documentation (Swagger UI)</a></li>
                <li><strong>POST /token</strong> - Login and get JWT token</li>
                <li><strong>POST /register</strong> - Register new user</li>
                <li><strong>GET /users/me</strong> - Get current user (JWT Bearer)</li>
                <li><strong>GET /users/profile</strong> - Get user profile (Basic Auth)</li>
                <li><strong>GET /admin/users</strong> - Admin endpoint (JWT + admin permission)</li>
                <li><strong>GET /api/data</strong> - API data (API Key)</li>
                <li><strong>GET /oauth2/me</strong> - OAuth2 protected endpoint</li>
            </ul>
            <h2>Test Credentials:</h2>
            <p><strong>Admin:</strong> username=admin, password=admin123</p>
            <p><strong>User:</strong> username=john, password=secret123</p>
            <p><strong>API Key:</strong> X-API-Key: sk-1234567890abcdef</p>
        </body>
    </html>
    """)

async def register_user(user_data: UserCreate):
    """Register a new user."""
    if user_data.username in fake_users_db:
        return JSONResponse(
            {"error": "Username already exists"}, 
            status_code=400
        )
    
    # Create new user
    fake_users_db[user_data.username] = {
        "username": user_data.username,
        "hashed_password": hash_password(user_data.password),
        "email": user_data.email,
        "full_name": user_data.full_name or user_data.username,
        "disabled": False,
        "roles": ["user"],
        "permissions": ["read"],
    }
    
    return JSONResponse({
        "message": "User created successfully",
        "username": user_data.username
    })

async def login_for_access_token(form_data: LoginRequest):
    """Authenticate user and return JWT token."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        return JSONResponse(
            {"error": "Incorrect username or password"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    })

# Protected endpoints with different authentication methods

async def read_users_me(
    current_user: Annotated[User, get_current_user_jwt]
):
    """Get current user information (JWT Bearer)."""
    if current_user.disabled:
        return JSONResponse(
            {"error": "Inactive user"}, 
            status_code=400
        )
    
    return JSONResponse({
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
        "auth_method": "JWT Bearer"
    })

async def read_user_profile(
    current_user: Annotated[User, get_current_user_basic]
):
    """Get user profile (Basic Authentication)."""
    return JSONResponse({
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "auth_method": "Basic Authentication"
    })

async def read_api_data(
    current_user: Annotated[User, get_current_user_api_key]
):
    """Get API data (API Key Authentication)."""
    return JSONResponse({
        "data": [
            {"id": 1, "value": "Sample data 1"},
            {"id": 2, "value": "Sample data 2"},
            {"id": 3, "value": "Sample data 3"},
        ],
        "user": current_user.username,
        "permissions": current_user.permissions,
        "auth_method": "API Key"
    })

async def read_oauth2_me(
    current_user: Annotated[User, get_current_user_oauth2]
):
    """OAuth2 protected endpoint."""
    return JSONResponse({
        "username": current_user.username,
        "email": current_user.email,
        "auth_method": "OAuth2 Password Bearer"
    })

# Admin endpoints with role-based permissions

async def list_all_users(
    current_user: Annotated[User, get_current_user_jwt],
    _: Annotated[None, require_permission("admin")]
):
    """List all users (Admin only)."""
    users = []
    for username, user_data in fake_users_db.items():
        users.append({
            "username": username,
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "disabled": user_data["disabled"],
            "roles": user_data["roles"],
        })
    
    return JSONResponse({
        "users": users,
        "total": len(users),
        "requested_by": current_user.username
    })

async def delete_user(
    username: str,
    current_user: Annotated[User, get_current_user_jwt],
    _: Annotated[None, require_permission("admin")]
):
    """Delete a user (Admin only)."""
    if username == current_user.username:
        return JSONResponse(
            {"error": "Cannot delete yourself"}, 
            status_code=400
        )
    
    if username not in fake_users_db:
        return JSONResponse(
            {"error": "User not found"}, 
            status_code=404
        )
    
    del fake_users_db[username]
    return JSONResponse({
        "message": f"User {username} deleted successfully",
        "deleted_by": current_user.username
    })

# =============================================================================
# Application Setup
# =============================================================================

# Create the main application
app = Velithon(
    title="Velithon Authentication Example",
    description="""
    A comprehensive example demonstrating Velithon's authentication system.
    
    ## Authentication Methods
    
    This API supports multiple authentication methods:
    
    * **JWT Bearer Token** - Use the `/token` endpoint to get a token
    * **Basic Authentication** - Username and password in Authorization header
    * **API Key** - Pass API key in `X-API-Key` header
    * **OAuth2 Password Bearer** - OAuth2 flow with password grant
    
    ## Test Credentials
    
    * **Admin User**: username=`admin`, password=`admin123`
    * **Regular User**: username=`john`, password=`secret123`  
    * **API Key**: `sk-1234567890abcdef`
    
    ## Security Features
    
    * Role-based access control
    * Permission-based authorization
    * JWT token expiration
    * API key expiration
    * Secure password hashing
    * OpenAPI security scheme documentation
    """,
    version="1.0.0",
    middleware=[
        Middleware(SecurityMiddleware),
        Middleware(AuthenticationMiddleware),
    ]
)

# Add routes
app.router.add_api_route("/", home, methods=["GET"], tags=["Public"])
app.router.add_api_route("/register", register_user, methods=["POST"], tags=["Authentication"])
app.router.add_api_route("/token", login_for_access_token, methods=["POST"], tags=["Authentication"])

# JWT Bearer protected routes
app.router.add_api_route("/users/me", read_users_me, methods=["GET"], tags=["Users"])

# Basic Auth protected routes  
app.router.add_api_route("/users/profile", read_user_profile, methods=["GET"], tags=["Users"])

# API Key protected routes
app.router.add_api_route("/api/data", read_api_data, methods=["GET"], tags=["API"])

# OAuth2 protected routes
app.router.add_api_route("/oauth2/me", read_oauth2_me, methods=["GET"], tags=["OAuth2"])

# Admin routes with role-based permissions
admin_router = Router(path="/admin")
admin_router.add_api_route("/users", list_all_users, methods=["GET"], tags=["Admin"])
admin_router.add_api_route("/users/{username}", delete_user, methods=["DELETE"], tags=["Admin"])

app.include_router(admin_router)

# =============================================================================
# Run the application
# =============================================================================

if __name__ == "__main__":
    print("🚀 Starting Velithon Authentication Example")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🏠 Home Page: http://localhost:8000/")
    print("🔑 Test with: admin/admin123 or john/secret123")
    
    # Use Granian server for RSGI
    import granian
    
    server = granian.Granian(
        target="examples.authentication_example:app",
        address="0.0.0.0",
        port=8000,
        interface="rsgi",
        reload=True,
        log_enabled=True,
    )
    server.serve()
