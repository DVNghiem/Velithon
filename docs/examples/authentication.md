# Authentication Example

Complete authentication system using JWT tokens with Velithon.

## Overview

This example demonstrates how to implement a full authentication system with user registration, login, and protected routes.

## Complete Authentication System

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse
from velithon.exceptions import HTTPException
from velithon.security import HTTPBearer, JWTHandler
from velithon.di import inject, Provide, ServiceContainer
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import datetime

app = Velithon()

# JWT Configuration
JWT_SECRET = "your-secret-key-change-this-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime.datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# In-memory user storage (use a database in production)
users_db = {}
next_user_id = 1

# Services
class AuthService:
    def __init__(self):
        self.jwt_handler = JWTHandler(
            secret_key=JWT_SECRET,
            algorithm=JWT_ALGORITHM
        )
    
    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.hash_password(plain_password) == hashed_password
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in users_db.values():
            if user.username == username:
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        for user in users_db.values():
            if user.email == email:
                return user
        return None
    
    def create_user(self, user_data: UserRegister) -> User:
        global next_user_id
        
        # Check if user already exists
        if self.get_user_by_username(user_data.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        
        if self.get_user_by_email(user_data.email):
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create user
        hashed_password = self.hash_password(user_data.password)
        user = User(
            id=next_user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            created_at=datetime.datetime.now()
        )
        
        # Store user with hashed password
        users_db[next_user_id] = {
            "user": user,
            "password": hashed_password
        }
        next_user_id += 1
        
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user_record = None
        for record in users_db.values():
            if record["user"].username == username:
                user_record = record
                break
        
        if not user_record:
            return None
        
        if not self.verify_password(password, user_record["password"]):
            return None
        
        return user_record["user"]
    
    def create_access_token(self, user: User) -> Token:
        payload = {
            "sub": user.username,
            "user_id": user.id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        
        token = self.jwt_handler.encode(payload)
        
        return Token(
            access_token=token,
            expires_in=JWT_EXPIRATION_HOURS * 3600  # seconds
        )
    
    def get_current_user(self, token: str) -> User:
        try:
            payload = self.jwt_handler.decode(token)
            username = payload.get("sub")
            
            if not username:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            user = self.get_user_by_username(username)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            return user
            
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

# Dependency setup
container = ServiceContainer()
container.register(AuthService, AuthService())

# Security scheme
bearer_auth = HTTPBearer()

# Authentication endpoints
@app.post("/register", response_model=User, tags=["auth"])
@inject
async def register(
    user_data: UserRegister,
    auth_service: Provide[AuthService]
):
    """Register a new user"""
    user = auth_service.create_user(user_data)
    return OptimizedJSONResponse(user.dict(), status_code=201)

@app.post("/login", response_model=Token, tags=["auth"])
@inject
async def login(
    credentials: UserLogin,
    auth_service: Provide[AuthService]
):
    """Login and get access token"""
    user = auth_service.authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    token = auth_service.create_access_token(user)
    return OptimizedJSONResponse(token.dict())

@app.get("/me", response_model=User, tags=["auth"])
@inject
async def get_current_user(
    token: Provide[HTTPBearer] = bearer_auth,
    auth_service: Provide[AuthService]
):
    """Get current user information"""
    user = auth_service.get_current_user(token)
    return OptimizedJSONResponse(user.dict())

# Protected endpoints
@app.get("/protected", tags=["protected"])
@inject
async def protected_endpoint(
    token: Provide[HTTPBearer] = bearer_auth,
    auth_service: Provide[AuthService]
):
    """A protected endpoint that requires authentication"""
    user = auth_service.get_current_user(token)
    return OptimizedJSONResponse({
        "message": f"Hello {user.username}, this is a protected endpoint!",
        "user_id": user.id
    })

@app.get("/admin", tags=["admin"])
@inject
async def admin_endpoint(
    token: Provide[HTTPBearer] = bearer_auth,
    auth_service: Provide[AuthService]
):
    """Admin-only endpoint (simplified example)"""
    user = auth_service.get_current_user(token)
    
    # Simple admin check (in real app, use roles/permissions)
    if user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return OptimizedJSONResponse({
        "message": "Welcome to the admin panel",
        "users_count": len(users_db)
    })

# User management endpoints
@app.get("/users", tags=["users"])
@inject
async def list_users(
    token: Provide[HTTPBearer] = bearer_auth,
    auth_service: Provide[AuthService]
):
    """List all users (admin only)"""
    current_user = auth_service.get_current_user(token)
    
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = [record["user"].dict() for record in users_db.values()]
    return OptimizedJSONResponse(users)

@app.put("/me", response_model=User, tags=["users"])
@inject
async def update_profile(
    profile_update: dict,
    token: Provide[HTTPBearer] = bearer_auth,
    auth_service: Provide[AuthService]
):
    """Update current user profile"""
    user = auth_service.get_current_user(token)
    
    # Update allowed fields
    allowed_fields = ["full_name", "email"]
    for field, value in profile_update.items():
        if field in allowed_fields and hasattr(user, field):
            setattr(user, field, value)
    
    # Update in storage
    for record in users_db.values():
        if record["user"].id == user.id:
            record["user"] = user
            break
    
    return OptimizedJSONResponse(user.dict())

# Register services with the app
app.container = container

if __name__ == "__main__":
    # Create an admin user for testing
    auth_service = AuthService()
    try:
        admin_user = UserRegister(
            username="admin",
            email="admin@example.com",
            password="admin123",
            full_name="Administrator"
        )
        auth_service.create_user(admin_user)
        print("Admin user created: username=admin, password=admin123")
    except HTTPException:
        print("Admin user already exists")
    
    app.run(debug=True)
```

## Usage Examples

### Register a New User

```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Access Protected Endpoint

```bash
curl -X GET "http://localhost:8000/protected" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Get Current User Info

```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Update Profile

```bash
curl -X PUT "http://localhost:8000/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "full_name": "John Smith"
  }'
```

## Key Features Demonstrated

- **User Registration**: Create new user accounts with validation
- **Password Hashing**: Secure password storage
- **JWT Tokens**: Stateless authentication
- **Protected Routes**: Endpoints requiring authentication
- **Dependency Injection**: Clean service architecture
- **Role-based Access**: Simple admin permissions
- **User Management**: Profile updates and user listing

## Security Considerations

1. **Change the JWT secret** in production
2. **Use environment variables** for configuration
3. **Implement proper password requirements**
4. **Add rate limiting** for login attempts
5. **Use HTTPS** in production
6. **Implement token refresh** mechanism
7. **Add proper logging** for security events

## Next Steps

- Add password reset functionality
- Implement role-based permissions system
- Add OAuth2 integration
- Include email verification
- Add session management
- Implement multi-factor authentication
