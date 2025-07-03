# Authentication

Velithon provides comprehensive authentication capabilities including JWT tokens, API keys, session-based authentication, and OAuth2 integration.

## Overview

Authentication in Velithon is handled through middleware and dependency injection, allowing for flexible and secure authentication patterns.

## JWT Authentication

### Setup

```python
from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.auth import JWTAuthenticationMiddleware
from velithon.responses import OptimizedJSONResponse
from velithon.exceptions import UnauthorizedException
import jwt
from datetime import datetime, timedelta
from typing import Annotated

# JWT Configuration
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = Velithon(middleware=[
    Middleware(JWTAuthenticationMiddleware, 
               secret_key=SECRET_KEY, 
               algorithm=ALGORITHM)
])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/login")
async def login(credentials: dict):
    # Validate credentials (implement your logic)
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not validate_user(username, password):
        raise UnauthorizedException("Invalid credentials")
    
    access_token = create_access_token(data={"sub": username})
    return OptimizedJSONResponse({
        "access_token": access_token,
        "token_type": "bearer"
    })

@app.get("/protected")
async def protected_endpoint(user: Annotated[dict, Depends(get_current_user)]):
    return OptimizedJSONResponse({"message": f"Hello, {user['username']}!"})
```

### JWT Dependency

```python
from velithon.dependencies import Depends
from velithon.exceptions import UnauthorizedException
from jose import JWTError, jwt

async def get_current_user(request: Request) -> dict:
    credentials_exception = UnauthorizedException(
        "Could not validate credentials"
    )
    
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise credentials_exception
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise credentials_exception
    except ValueError:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(username)  # Implement your user lookup
    if user is None:
        raise credentials_exception
    
    return user
```

## API Key Authentication

### Setup

```python
from velithon.middleware.auth import APIKeyAuthenticationMiddleware

app = Velithon(middleware=[
    Middleware(APIKeyAuthenticationMiddleware, 
               api_keys=["api-key-1", "api-key-2"],
               header_name="X-API-Key")
])

@app.get("/api/data")
async def get_data(request: Request):
    api_key = request.headers.get("X-API-Key")
    # API key is automatically validated by middleware
    return OptimizedJSONResponse({"data": "sensitive information"})
```

### Custom API Key Validation

```python
async def validate_api_key(api_key: str) -> bool:
    # Implement your API key validation logic
    # Could check database, cache, etc.
    return api_key in valid_api_keys

class CustomAPIKeyMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, protocol):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            api_key = headers.get(b"x-api-key", b"").decode()
            
            if not await validate_api_key(api_key):
                # Return 401 Unauthorized
                response = OptimizedJSONResponse(
                    {"error": "Invalid API key"}, 
                    status_code=401
                )
                await response(scope, protocol)
                return
        
        await self.app(scope, protocol)

app = Velithon(middleware=[Middleware(CustomAPIKeyMiddleware)])
```

## Session-Based Authentication

### Setup

```python
from velithon.middleware.session import SessionMiddleware
from velithon.middleware.auth import SessionAuthenticationMiddleware

app = Velithon(middleware=[
    Middleware(SessionMiddleware, secret_key="session-secret"),
    Middleware(SessionAuthenticationMiddleware)
])

@app.post("/login")
async def login(request: Request, credentials: dict):
    username = credentials.get("username")
    password = credentials.get("password")
    
    if validate_user(username, password):
        request.session["user_id"] = user.id
        request.session["username"] = username
        request.session["authenticated"] = True
        
        return OptimizedJSONResponse({"message": "Logged in successfully"})
    
    raise UnauthorizedException("Invalid credentials")

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return OptimizedJSONResponse({"message": "Logged out successfully"})

@app.get("/profile")
async def get_profile(request: Request):
    if not request.session.get("authenticated"):
        raise UnauthorizedException("Not authenticated")
    
    username = request.session.get("username")
    return OptimizedJSONResponse({"username": username})
```

## OAuth2 Authentication

### Authorization Code Flow

```python
from velithon.middleware.oauth2 import OAuth2AuthorizationCodeMiddleware
import httpx

OAUTH2_CONFIG = {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "authorization_url": "https://provider.com/oauth/authorize",
    "token_url": "https://provider.com/oauth/token",
    "redirect_uri": "http://localhost:8000/auth/callback"
}

app = Velithon(middleware=[
    Middleware(OAuth2AuthorizationCodeMiddleware, **OAUTH2_CONFIG)
])

@app.get("/auth/login")
async def oauth_login():
    auth_url = (
        f"{OAUTH2_CONFIG['authorization_url']}"
        f"?client_id={OAUTH2_CONFIG['client_id']}"
        f"&redirect_uri={OAUTH2_CONFIG['redirect_uri']}"
        f"&response_type=code"
        f"&scope=read:user"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def oauth_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            OAUTH2_CONFIG["token_url"],
            data={
                "client_id": OAUTH2_CONFIG["client_id"],
                "client_secret": OAUTH2_CONFIG["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": OAUTH2_CONFIG["redirect_uri"]
            }
        )
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        
        # Store token and create session
        # Implement your token storage logic
        
        return RedirectResponse("/dashboard")
```

## Role-Based Authorization

### Decorator-Based Authorization

```python
from functools import wraps
from velithon.exceptions import ForbiddenException

def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):  # It's a request
                    request = arg
                    break
            
            if not request:
                raise ForbiddenException("Request not found")
            
            user = await get_current_user(request)
            if user.get("role") != required_role:
                raise ForbiddenException("Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.get("/admin/users")
@require_role("admin")
async def get_all_users(request: Request):
    return OptimizedJSONResponse({"users": get_users()})
```

### Permission-Based Authorization

```python
from enum import Enum

class Permission(Enum):
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    DELETE_USERS = "delete:users"
    ADMIN = "admin"

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):
                    request = arg
                    break
            
            user = await get_current_user(request)
            user_permissions = user.get("permissions", [])
            
            if permission.value not in user_permissions and Permission.ADMIN.value not in user_permissions:
                raise ForbiddenException(f"Missing permission: {permission.value}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.delete("/users/{user_id}")
@require_permission(Permission.DELETE_USERS)
async def delete_user(request: Request, user_id: int):
    delete_user_by_id(user_id)
    return OptimizedJSONResponse({"message": "User deleted"})
```

## Multi-Factor Authentication

### TOTP (Time-based One-Time Password)

```python
import pyotp
import qrcode
from io import BytesIO
import base64

@app.post("/auth/setup-2fa")
async def setup_2fa(user: Annotated[dict, Depends(get_current_user)]):
    # Generate a secret key for the user
    secret = pyotp.random_base32()
    
    # Save secret to user record
    save_user_2fa_secret(user["id"], secret)
    
    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user["email"],
        issuer_name="Your App Name"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for frontend
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    
    return OptimizedJSONResponse({
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code_data}"
    })

@app.post("/auth/verify-2fa")
async def verify_2fa(
    user: Annotated[dict, Depends(get_current_user)],
    totp_code: str
):
    user_secret = get_user_2fa_secret(user["id"])
    if not user_secret:
        raise UnauthorizedException("2FA not set up")
    
    totp = pyotp.TOTP(user_secret)
    
    if not totp.verify(totp_code):
        raise UnauthorizedException("Invalid 2FA code")
    
    # Mark user as fully authenticated
    # Update session or JWT with 2FA verification
    
    return OptimizedJSONResponse({"message": "2FA verified successfully"})
```

## Authentication Middleware Chain

```python
from velithon.middleware import Middleware
from velithon.middleware.auth import (
    JWTAuthenticationMiddleware,
    APIKeyAuthenticationMiddleware,
    SessionAuthenticationMiddleware
)

# Multiple authentication methods
app = Velithon(middleware=[
    # Try JWT first
    Middleware(JWTAuthenticationMiddleware, 
               secret_key=SECRET_KEY, 
               algorithm=ALGORITHM,
               optional=True),
    
    # Fall back to API key
    Middleware(APIKeyAuthenticationMiddleware, 
               api_keys=API_KEYS,
               optional=True),
    
    # Fall back to session
    Middleware(SessionAuthenticationMiddleware, optional=True),
])

@app.get("/api/data")
async def get_data(request: Request):
    # Check if user is authenticated by any method
    user = getattr(request, "user", None)
    auth_method = getattr(request, "auth_method", None)
    
    if not user:
        raise UnauthorizedException("Authentication required")
    
    return OptimizedJSONResponse({
        "data": "protected data",
        "auth_method": auth_method,
        "user": user
    })
```

## Best Practices

### Security Headers

```python
from velithon.middleware.security import SecurityHeadersMiddleware

app = Velithon(middleware=[
    Middleware(SecurityHeadersMiddleware, 
               csp="default-src 'self'",
               hsts=True,
               frame_options="DENY")
])
```

### Rate Limiting

```python
from velithon.middleware.ratelimit import RateLimitMiddleware

app = Velithon(middleware=[
    Middleware(RateLimitMiddleware, 
               requests_per_minute=60,
               burst_size=10)
])
```

### Password Security

```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

@app.post("/register")
async def register(user_data: dict):
    password = user_data["password"]
    
    # Validate password strength
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    
    hashed_password = hash_password(password)
    
    # Save user with hashed password
    save_user({
        **user_data,
        "password": hashed_password
    })
    
    return OptimizedJSONResponse({"message": "User registered successfully"})
```

## Testing Authentication

```python
import pytest
import httpx

@pytest.fixture
async def client():
    # Note: Velithon doesn't have a built-in TestClient
    # Use httpx for testing HTTP endpoints
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client):
    response = await client.get("/protected")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client):
    token = create_access_token({"sub": "testuser"})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/protected", headers=headers)
    assert response.status_code == 200

def test_login_with_valid_credentials(client):
    response = client.post("/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## Next Steps

- [Authorization →](authorization.md)
- [JWT Tokens →](jwt.md)
- [Security Best Practices →](best-practices.md)
