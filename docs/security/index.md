# Security

Velithon provides comprehensive security features to help you build secure web applications. This section covers authentication, authorization, and security best practices.

## Overview

Security in Velithon is built around several key components:

- **Authentication**: Verifying user identity
- **Authorization**: Controlling access to resources
- **Session Management**: Secure session handling
- **Security Headers**: Protection against common attacks
- **Input Validation**: Preventing injection attacks

## Authentication

### JWT Authentication

Velithon supports JWT (JSON Web Tokens) for stateless authentication:

```python
from velithon.security import JWTManager
from velithon.security.models import User

# Initialize JWT manager
jwt_manager = JWTManager(secret_key="your-secret-key")

@app.post("/login")
async def login(username: str, password: str):
    # Verify credentials
    user = await verify_user(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    token = jwt_manager.create_token(
        user_id=user.id,
        username=user.username,
        expires_in=3600  # 1 hour
    )
    
    return {"access_token": token, "token_type": "bearer"}

@app.get("/protected")
async def protected_route(token: str = Depends(jwt_manager.verify_token)):
    return {"message": "Access granted", "user": token.user_id}
```

### OAuth2 Support

Velithon provides OAuth2 integration for third-party authentication:

```python
from velithon.security import OAuth2Manager

oauth2_manager = OAuth2Manager(
    client_id="your-client-id",
    client_secret="your-client-secret",
    redirect_uri="http://localhost:8000/auth/callback"
)

@app.get("/auth/google")
async def google_auth():
    auth_url = oauth2_manager.get_authorization_url("google")
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def auth_callback(code: str):
    token_data = await oauth2_manager.get_token("google", code)
    user_info = await oauth2_manager.get_user_info("google", token_data)
    
    # Create session or JWT token
    return {"user": user_info}
```

### API Key Authentication

For API-based authentication:

```python
from velithon.security import APIKeyAuth

api_auth = APIKeyAuth(api_keys=["key1", "key2", "key3"])

@app.get("/api/data")
async def get_data(api_key: str = Depends(api_auth.verify)):
    return {"data": "sensitive information"}
```

### Basic Authentication

Simple username/password authentication:

```python
from velithon.security import BasicAuth

basic_auth = BasicAuth(
    credentials={
        "admin": "password123",
        "user": "userpass"
    }
)

@app.get("/admin")
async def admin_route(auth: dict = Depends(basic_auth.verify)):
    return {"message": f"Welcome {auth['username']}"}
```

## Authorization

### Role-Based Access Control (RBAC)

Velithon provides a flexible RBAC system:

```python
from velithon.security import RBACManager

rbac = RBACManager()

# Define roles and permissions
rbac.add_role("admin", ["read", "write", "delete", "manage_users"])
rbac.add_role("user", ["read", "write"])
rbac.add_role("guest", ["read"])

@app.get("/users")
async def list_users(user: dict = Depends(jwt_manager.verify_token)):
    if not rbac.has_permission(user["role"], "read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {"users": ["user1", "user2", "user3"]}

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    user: dict = Depends(jwt_manager.verify_token)
):
    if not rbac.has_permission(user["role"], "delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {"message": f"User {user_id} deleted"}
```

### Permission Decorators

Use decorators for cleaner authorization:

```python
from velithon.security import require_permission

@app.get("/admin/users")
@require_permission("manage_users")
async def admin_users(user: dict = Depends(jwt_manager.verify_token)):
    return {"users": ["admin1", "admin2"]}

@app.post("/admin/users")
@require_permission("manage_users")
async def create_user(user: dict = Depends(jwt_manager.verify_token)):
    return {"message": "User created"}
```

## Session Management

### Secure Sessions

Velithon provides secure session management:

```python
from velithon.middleware import SessionMiddleware

app = Velithon(
    middleware=[
        SessionMiddleware(
            secret_key="your-secret-key",
            max_age=3600,  # 1 hour
            secure=True,    # HTTPS only
            http_only=True, # Prevent XSS
            same_site="strict"  # CSRF protection
        )
    ]
)

@app.post("/login")
async def login(request: Request, username: str, password: str):
    user = await verify_user(username, password)
    if user:
        # Store user data in session
        request.session["user_id"] = user.id
        request.session["username"] = user.username
        request.session["role"] = user.role
        return {"message": "Logged in successfully"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/profile")
async def profile(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "user_id": user_id,
        "username": request.session.get("username"),
        "role": request.session.get("role")
    }

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}
```

## Security Headers

### Automatic Security Headers

Velithon automatically adds security headers:

```python
from velithon.middleware import SecurityMiddleware

app = Velithon(
    middleware=[
        SecurityMiddleware(
            add_security_headers=True,
            content_security_policy="default-src 'self'",
            strict_transport_security="max-age=31536000; includeSubDomains"
        )
    ]
)
```

**Default Security Headers:**
- `X-Content-Type-Options: nosniff` - Prevent MIME type sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - Enable XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Control referrer information
- `Content-Security-Policy` - Prevent XSS and injection attacks

## Input Validation

### Request Validation

Use Pydantic for input validation:

```python
from pydantic import BaseModel, validator
from velithon.security import sanitize_input

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return sanitize_input(v)
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

@app.post("/users")
async def create_user(user: UserCreate):
    # Password should be hashed before storage
    hashed_password = hash_password(user.password)
    
    # Create user in database
    return {"message": "User created", "username": user.username}
```

### SQL Injection Prevention

Velithon provides utilities to prevent SQL injection:

```python
from velithon.security import sanitize_sql

@app.get("/users")
async def get_users(search: str = ""):
    # Sanitize search parameter
    safe_search = sanitize_sql(search)
    
    # Use parameterized queries
    query = "SELECT * FROM users WHERE name LIKE %s"
    users = await database.execute(query, (f"%{safe_search}%",))
    
    return {"users": users}
```

## CSRF Protection

### CSRF Tokens

Protect against Cross-Site Request Forgery:

```python
from velithon.security import CSRFProtection

csrf = CSRFProtection(secret_key="your-secret-key")

@app.get("/form")
async def get_form(request: Request):
    token = csrf.generate_token(request)
    return HTMLResponse(f"""
    <form method="POST" action="/submit">
        <input type="hidden" name="csrf_token" value="{token}">
        <input type="text" name="data">
        <button type="submit">Submit</button>
    </form>
    """)

@app.post("/submit")
async def submit_form(request: Request, data: str, csrf_token: str):
    if not csrf.verify_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    # Process form data
    return {"message": "Form submitted successfully"}
```

## Rate Limiting

### Request Rate Limiting

Protect against abuse with rate limiting:

```python
from velithon.security import RateLimiter

rate_limiter = RateLimiter(
    requests_per_minute=60,
    burst_size=10
)

@app.get("/api/data")
async def get_data(request: Request):
    client_ip = request.client.host
    
    if not rate_limiter.allow_request(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
    return {"data": "sensitive information"}
```

## Security Best Practices

### 1. Use HTTPS in Production

```python
app = Velithon(
    middleware=[
        SecurityMiddleware(
            force_https=True,
            hsts_max_age=31536000
        )
    ]
)
```

### 2. Secure Cookie Settings

```python
app = Velithon(
    middleware=[
        SessionMiddleware(
            secret_key="your-secret-key",
            secure=True,      # HTTPS only
            http_only=True,   # Prevent XSS
            same_site="strict"  # CSRF protection
        )
    ]
)
```

### 3. Input Sanitization

```python
from velithon.security import sanitize_html, sanitize_sql

@app.post("/comment")
async def add_comment(content: str):
    # Sanitize user input
    safe_content = sanitize_html(content)
    
    # Store in database
    await database.execute(
        "INSERT INTO comments (content) VALUES (%s)",
        (safe_content,)
    )
    
    return {"message": "Comment added"}
```

### 4. Password Security

```python
from velithon.security import hash_password, verify_password

@app.post("/register")
async def register(username: str, password: str):
    # Hash password before storage
    hashed_password = hash_password(password)
    
    # Store in database
    await database.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (username, hashed_password)
    )
    
    return {"message": "User registered"}

@app.post("/login")
async def login(username: str, password: str):
    # Get user from database
    user = await database.fetch_one(
        "SELECT * FROM users WHERE username = %s",
        (username,)
    )
    
    if user and verify_password(password, user["password"]):
        return {"message": "Login successful"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")
```

### 5. Logging Security Events

```python
import logging
from velithon.security import SecurityLogger

security_logger = SecurityLogger()

@app.post("/login")
async def login(username: str, password: str):
    try:
        user = await verify_user(username, password)
        if user:
            security_logger.log_successful_login(username, request.client.host)
            return {"message": "Login successful"}
        else:
            security_logger.log_failed_login(username, request.client.host)
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        security_logger.log_security_event("login_error", str(e))
        raise
```

This comprehensive security system helps you build secure applications while maintaining the high performance that Velithon provides.
