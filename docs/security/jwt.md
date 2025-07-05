# JWT Tokens

This guide covers implementing JWT (JSON Web Token) authentication and authorization in Velithon applications.

## Basic JWT Implementation

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from velithon.di import inject, Provide, ServiceContainer
import jwt
import bcrypt
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any
import secrets

@dataclass
class User:
    id: str
    username: str
    email: str
    password_hash: str
    is_active: bool = True
    roles: list = None
    created_at: datetime = None

class JWTService:
    def __init__(self, secret_key: str = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create access token with short expiration."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token with long expiration."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = None) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if token_type and payload.get("type") != token_type:
                raise jwt.InvalidTokenError(f"Invalid token type. Expected {token_type}")
            
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token."""
        payload = self.verify_token(refresh_token, "refresh")
        
        # Create new access token with same user data
        access_data = {
            "sub": payload["sub"],
            "username": payload.get("username"),
            "roles": payload.get("roles", [])
        }
        return self.create_access_token(access_data)

class UserService:
    def __init__(self):
        # Mock user database - replace with real database
        self.users = {
            "user1": User(
                id="user1",
                username="john_doe",
                email="john@example.com",
                password_hash=bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode(),
                roles=["user"]
            ),
            "admin1": User(
                id="admin1",
                username="admin",
                email="admin@example.com",
                password_hash=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
                roles=["admin", "user"]
            )
        }
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        return user

app = Velithon()

# Register services
class JWTContainer(ServiceContainer):
    jwt_service = JWTService()
    user_service = UserService()

def get_current_user(request: Request) -> Optional[User]:
    """Extract current user from JWT token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    jwt_service = JWTContainer.jwt_service
    user_service = JWTContainer.user_service
    
    try:
        payload = jwt_service.verify_token(token, "access")
        user_id = payload.get("sub")
        if user_id:
            return user_service.get_user_by_id(user_id)
    except ValueError:
        return None
    
    return None

def require_jwt_auth(func):
    """Decorator to require JWT authentication."""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return JSONResponse(
                {"error": "Authentication required"},
                status_code=401
            )
        
        request.state.current_user = user
        return await func(request, *args, **kwargs)
    
    return wrapper

def require_roles(*required_roles):
    """Decorator to require specific roles."""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, "current_user"):
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            user = request.state.current_user
            if not any(role in user.roles for role in required_roles):
                return JSONResponse(
                    {"error": f"Roles required: {', '.join(required_roles)}"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.post("/auth/login")
async def login(request: Request):
    """Login endpoint that returns JWT tokens."""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return JSONResponse(
            {"error": "Username and password required"},
            status_code=400
        )
    
    user_service = ServiceContainer.get(UserService)
    user = user_service.authenticate_user(username, password)
    
    if not user:
        return JSONResponse(
            {"error": "Invalid credentials"},
            status_code=401
        )
    
    jwt_service = ServiceContainer.get(JWTService)
    
    # Create token payload
    token_data = {
        "sub": user.id,
        "username": user.username,
        "roles": user.roles
    }
    
    # Generate tokens
    access_token = jwt_service.create_access_token(token_data)
    refresh_token = jwt_service.create_refresh_token(token_data)
    
    return JSONResponse({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": jwt_service.access_token_expire_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles
        }
    })

@app.post("/auth/refresh")
async def refresh_token(request: Request):
    """Refresh access token using refresh token."""
    data = await request.json()
    refresh_token = data.get("refresh_token")
    
    if not refresh_token:
        return JSONResponse(
            {"error": "Refresh token required"},
            status_code=400
        )
    
    jwt_service = ServiceContainer.get(JWTService)
    
    try:
        new_access_token = jwt_service.refresh_access_token(refresh_token)
        return JSONResponse({
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": jwt_service.access_token_expire_minutes * 60
        })
    except ValueError as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=401
        )

@app.get("/auth/me")
@require_jwt_auth
async def get_current_user_info(request: Request):
    """Get current user information."""
    user = request.state.current_user
    return JSONResponse({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "is_active": user.is_active
    })

@app.post("/auth/logout")
@require_jwt_auth
async def logout(request: Request):
    """Logout endpoint (in practice, you'd blacklist the token)."""
    # In a real application, you would:
    # 1. Add the token to a blacklist
    # 2. Store blacklisted tokens in Redis with expiration
    # 3. Check blacklist in token verification
    
    return JSONResponse({
        "message": "Successfully logged out"
    })

@app.get("/protected")
@require_jwt_auth
async def protected_endpoint(request: Request):
    """Protected endpoint requiring authentication."""
    user = request.state.current_user
    return JSONResponse({
        "message": f"Hello {user.username}!",
        "user_id": user.id,
        "roles": user.roles
    })

@app.get("/admin-only")
@require_jwt_auth
@require_roles("admin")
async def admin_only_endpoint(request: Request):
    """Admin-only endpoint."""
    user = request.state.current_user
    return JSONResponse({
        "message": f"Admin access granted for {user.username}",
        "admin_data": "Sensitive admin information"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Advanced JWT Features

### Token Blacklisting

```python
import redis
from typing import Set
import json

class TokenBlacklist:
    def __init__(self, redis_client=None):
        # Use Redis for distributed blacklist, or in-memory set for single instance
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.memory_blacklist: Set[str] = set()
        self.use_redis = redis_client is not None
    
    def add_token(self, token: str, expires_in: int = None):
        """Add token to blacklist."""
        if self.use_redis:
            # Set expiration based on token expiration
            self.redis_client.setex(f"blacklist:{token}", expires_in or 3600, "1")
        else:
            self.memory_blacklist.add(token)
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        if self.use_redis:
            return self.redis_client.exists(f"blacklist:{token}")
        else:
            return token in self.memory_blacklist
    
    def remove_token(self, token: str):
        """Remove token from blacklist (for testing)."""
        if self.use_redis:
            self.redis_client.delete(f"blacklist:{token}")
        else:
            self.memory_blacklist.discard(token)

class EnhancedJWTService(JWTService):
    def __init__(self, secret_key: str = None, algorithm: str = "HS256"):
        super().__init__(secret_key, algorithm)
        self.blacklist = TokenBlacklist()
    
    def verify_token(self, token: str, token_type: str = None) -> Dict[str, Any]:
        """Verify token and check blacklist."""
        # Check blacklist first
        if self.blacklist.is_blacklisted(token):
            raise ValueError("Token has been revoked")
        
        return super().verify_token(token, token_type)
    
    def revoke_token(self, token: str):
        """Revoke (blacklist) a token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            # Calculate remaining TTL
            exp = payload.get("exp")
            if exp:
                remaining_ttl = int(exp - datetime.utcnow().timestamp())
                if remaining_ttl > 0:
                    self.blacklist.add_token(token, remaining_ttl)
        except jwt.InvalidTokenError:
            # Token is already invalid, no need to blacklist
            pass

# Updated logout endpoint
@app.post("/auth/logout")
@require_jwt_auth
async def enhanced_logout(request: Request):
    """Logout with token revocation."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        jwt_service = ServiceContainer.get(EnhancedJWTService)
        jwt_service.revoke_token(token)
    
    return JSONResponse({
        "message": "Successfully logged out"
    })
```

### JWT with Claims and Scopes

```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TokenClaims:
    user_id: str
    username: str
    roles: List[str]
    scopes: List[str]
    tenant_id: str = None
    session_id: str = None

class ScopedJWTService(JWTService):
    def create_access_token(self, claims: TokenClaims) -> str:
        """Create access token with claims and scopes."""
        data = {
            "sub": claims.user_id,
            "username": claims.username,
            "roles": claims.roles,
            "scopes": claims.scopes,
            "tenant_id": claims.tenant_id,
            "session_id": claims.session_id
        }
        return super().create_access_token(data)
    
    def verify_scope(self, token: str, required_scope: str) -> bool:
        """Verify if token has required scope."""
        try:
            payload = self.verify_token(token, "access")
            scopes = payload.get("scopes", [])
            return required_scope in scopes
        except ValueError:
            return False

def require_scope(scope: str):
    """Decorator to require specific scope."""
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            token = auth_header.split(" ")[1]
            jwt_service = ServiceContainer.get(ScopedJWTService)
            
            if not jwt_service.verify_scope(token, scope):
                return JSONResponse(
                    {"error": f"Scope '{scope}' required"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.get("/api/users/read")
@require_scope("users:read")
async def read_users(request: Request):
    """Endpoint requiring users:read scope."""
    return JSONResponse({"users": ["user1", "user2"]})

@app.post("/api/users/write")
@require_scope("users:write")
async def write_users(request: Request):
    """Endpoint requiring users:write scope."""
    data = await request.json()
    return JSONResponse({"message": "User created", "user": data})
```

## JWT Security Best Practices

### Secure Token Storage

```python
from velithon.responses import HTMLResponse

@app.get("/secure-client")
async def secure_client():
    """Example of secure token handling in client."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure JWT Client</title>
    </head>
    <body>
        <h1>Secure JWT Authentication</h1>
        
        <div id="auth-form">
            <h2>Login</h2>
            <form id="loginForm">
                <input type="text" id="username" placeholder="Username" required>
                <input type="password" id="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
        
        <div id="user-info" style="display: none;">
            <h2>User Information</h2>
            <div id="userDetails"></div>
            <button onclick="logout()">Logout</button>
        </div>

        <script>
            // Secure token storage using httpOnly cookies (server-side implementation needed)
            // For demo purposes, we'll use sessionStorage (not recommended for production)
            
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                try {
                    const response = await fetch('/auth/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ username, password })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        
                        // Store tokens securely
                        sessionStorage.setItem('access_token', data.access_token);
                        sessionStorage.setItem('refresh_token', data.refresh_token);
                        
                        showUserInfo(data.user);
                    } else {
                        const error = await response.json();
                        alert('Login failed: ' + error.error);
                    }
                } catch (error) {
                    alert('Login error: ' + error.message);
                }
            });
            
            function showUserInfo(user) {
                document.getElementById('auth-form').style.display = 'none';
                document.getElementById('user-info').style.display = 'block';
                document.getElementById('userDetails').innerHTML = 
                    '<p>Username: ' + user.username + '</p>' +
                    '<p>Email: ' + user.email + '</p>' +
                    '<p>Roles: ' + user.roles.join(', ') + '</p>';
            }
            
            async function logout() {
                const token = sessionStorage.getItem('access_token');
                
                if (token) {
                    try {
                        await fetch('/auth/logout', {
                            method: 'POST',
                            headers: {
                                'Authorization': 'Bearer ' + token
                            }
                        });
                    } catch (error) {
                        console.error('Logout error:', error);
                    }
                }
                
                sessionStorage.removeItem('access_token');
                sessionStorage.removeItem('refresh_token');
                
                document.getElementById('auth-form').style.display = 'block';
                document.getElementById('user-info').style.display = 'none';
                document.getElementById('username').value = '';
                document.getElementById('password').value = '';
            }
            
            // Auto-refresh token before expiration
            setInterval(async function() {
                const refreshToken = sessionStorage.getItem('refresh_token');
                
                if (refreshToken) {
                    try {
                        const response = await fetch('/auth/refresh', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ refresh_token: refreshToken })
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            sessionStorage.setItem('access_token', data.access_token);
                        } else {
                            // Refresh failed, redirect to login
                            logout();
                        }
                    } catch (error) {
                        console.error('Token refresh error:', error);
                    }
                }
            }, 25 * 60 * 1000); // Refresh every 25 minutes (before 30-minute expiration)
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)
```

## Testing JWT Authentication

```python
import pytest
import httpx
from datetime import datetime, timedelta
import jwt

@pytest.mark.asyncio
async def test_jwt_login():
    """Test JWT login flow."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json={
            "username": "john_doe",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

@pytest.mark.asyncio
async def test_jwt_protected_endpoint():
    """Test accessing protected endpoint with JWT."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post("/auth/login", json={
            "username": "john_doe",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Hello john_doe" in data["message"]

@pytest.mark.asyncio
async def test_jwt_token_refresh():
    """Test token refresh functionality."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post("/auth/login", json={
            "username": "john_doe",
            "password": "password123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_jwt_expired_token():
    """Test handling of expired tokens."""
    jwt_service = JWTService()
    
    # Create expired token
    expired_payload = {
        "sub": "test_user",
        "username": "test",
        "exp": datetime.utcnow() - timedelta(hours=1)
    }
    expired_token = jwt.encode(expired_payload, jwt_service.secret_key, algorithm="HS256")
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_jwt_invalid_token():
    """Test handling of invalid tokens."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_jwt_role_based_access():
    """Test role-based access with JWT."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        admin_response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        admin_token = admin_response.json()["access_token"]
        
        # Admin can access admin endpoint
        response = await client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Login as regular user
        user_response = await client.post("/auth/login", json={
            "username": "john_doe",
            "password": "password123"
        })
        user_token = user_response.json()["access_token"]
        
        # User cannot access admin endpoint
        response = await client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
```

## Best Practices

1. **Use Strong Secret Keys**: Generate cryptographically secure random keys
2. **Short Access Token Expiry**: Keep access tokens short-lived (15-30 minutes)
3. **Secure Storage**: Store tokens securely (httpOnly cookies for web)
4. **Token Rotation**: Implement refresh token rotation
5. **Blacklisting**: Implement token blacklisting for logout
6. **Scope Limitation**: Use scopes to limit token permissions
7. **HTTPS Only**: Always use HTTPS in production
8. **Input Validation**: Validate all token-related inputs
9. **Audit Logging**: Log authentication events
10. **Rate Limiting**: Implement rate limiting on auth endpoints
