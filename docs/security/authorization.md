# Authorization

This guide covers implementing authorization and access control in Velithon applications.

## Role-Based Access Control (RBAC)

### Basic Role System

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from velithon.di import inject, Provide, ServiceContainer
from enum import Enum
from functools import wraps
import jwt
from datetime import datetime, timedelta

class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"

class Permission(Enum):
    READ_USERS = "read_users"
    WRITE_USERS = "write_users"
    DELETE_USERS = "delete_users"
    MODERATE_CONTENT = "moderate_content"

# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.READ_USERS,
        Permission.WRITE_USERS,
        Permission.DELETE_USERS,
        Permission.MODERATE_CONTENT
    ],
    Role.MODERATOR: [
        Permission.READ_USERS,
        Permission.MODERATE_CONTENT
    ],
    Role.USER: [
        Permission.READ_USERS
    ]
}

class AuthorizationService:
    def __init__(self):
        self.secret_key = "your-secret-key"
    
    def create_token(self, user_id: str, role: Role) -> str:
        """Create JWT token with user role."""
        payload = {
            "user_id": user_id,
            "role": role.value,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if role has specific permission."""
        return permission in ROLE_PERMISSIONS.get(role, [])

# Authorization decorators
def require_auth(func):
    """Decorator to require authentication."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid authorization header"},
                status_code=401
            )
        
        token = auth_header.split(" ")[1]
        auth_service = ServiceContainer.get(AuthorizationService)
        
        try:
            payload = auth_service.verify_token(token)
            request.state.user_id = payload["user_id"]
            request.state.role = Role(payload["role"])
            return await func(request, *args, **kwargs)
        except ValueError as e:
            return JSONResponse(
                {"error": str(e)},
                status_code=401
            )
    
    return wrapper

def require_permission(permission: Permission):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, "role"):
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            auth_service = ServiceContainer.get(AuthorizationService)
            if not auth_service.has_permission(request.state.role, permission):
                return JSONResponse(
                    {"error": "Insufficient permissions"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_role(required_role: Role):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, "role"):
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            if request.state.role != required_role:
                return JSONResponse(
                    {"error": f"Role '{required_role.value}' required"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

app = Velithon()

# Register services
class AuthorizationContainer(ServiceContainer):
    authorization_service = AuthorizationService()

@app.post("/login")
async def login(request: Request):
    """Login endpoint that returns JWT token."""
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    
    # Mock authentication - replace with real authentication
    if username == "admin" and password == "admin":
        role = Role.ADMIN
    elif username == "moderator" and password == "moderator":
        role = Role.MODERATOR
    elif username == "user" and password == "user":
        role = Role.USER
    else:
        return JSONResponse(
            {"error": "Invalid credentials"},
            status_code=401
        )
    
    auth_service = ServiceContainer.get(AuthorizationService)
    token = auth_service.create_token(username, role)
    
    return JSONResponse({
        "token": token,
        "role": role.value,
        "permissions": [p.value for p in ROLE_PERMISSIONS[role]]
    })

@app.get("/users")
@require_auth
@require_permission(Permission.READ_USERS)
async def get_users(request: Request):
    """Get all users - requires READ_USERS permission."""
    return JSONResponse({
        "users": [
            {"id": 1, "username": "user1", "role": "user"},
            {"id": 2, "username": "user2", "role": "user"},
            {"id": 3, "username": "admin1", "role": "admin"}
        ]
    })

@app.post("/users")
@require_auth
@require_permission(Permission.WRITE_USERS)
async def create_user(request: Request):
    """Create new user - requires WRITE_USERS permission."""
    data = await request.json()
    return JSONResponse({
        "message": "User created successfully",
        "user": data
    })

@app.delete("/users/{user_id}")
@require_auth
@require_permission(Permission.DELETE_USERS)
async def delete_user(request: Request):
    """Delete user - requires DELETE_USERS permission."""
    user_id = request.path_params["user_id"]
    return JSONResponse({
        "message": f"User {user_id} deleted successfully"
    })

@app.post("/moderate/content")
@require_auth
@require_permission(Permission.MODERATE_CONTENT)
async def moderate_content(request: Request):
    """Moderate content - requires MODERATE_CONTENT permission."""
    data = await request.json()
    return JSONResponse({
        "message": "Content moderated successfully",
        "action": data.get("action", "approved")
    })

@app.get("/admin/dashboard")
@require_auth
@require_role(Role.ADMIN)
async def admin_dashboard(request: Request):
    """Admin-only dashboard."""
    return JSONResponse({
        "dashboard": "admin",
        "stats": {
            "total_users": 100,
            "active_sessions": 25,
            "pending_moderation": 5
        }
    })

if __name__ == "__main__":
    # Run with: velithon run --app authorization_example:app --host 0.0.0.0 --port 8000
    print("Run with: velithon run --app authorization_example:app --host 0.0.0.0 --port 8000")
```

## Resource-Based Authorization

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from velithon.di import inject, Provide, ServiceContainer
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Resource:
    id: str
    name: str
    owner_id: str
    permissions: List[str]

class ResourceService:
    def __init__(self):
        # Mock data - replace with database
        self.resources = {
            "doc1": Resource("doc1", "Document 1", "user1", ["read", "write"]),
            "doc2": Resource("doc2", "Document 2", "user2", ["read"]),
            "doc3": Resource("doc3", "Document 3", "user1", ["read", "write", "delete"])
        }
    
    def get_resource(self, resource_id: str) -> Optional[Resource]:
        return self.resources.get(resource_id)
    
    def user_can_access(self, user_id: str, resource_id: str, action: str) -> bool:
        """Check if user can perform action on resource."""
        resource = self.get_resource(resource_id)
        if not resource:
            return False
        
        # Owner can do anything
        if resource.owner_id == user_id:
            return True
        
        # Check specific permissions
        return action in resource.permissions

def require_resource_permission(action: str):
    """Decorator to check resource-specific permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, "user_id"):
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            resource_id = request.path_params.get("resource_id")
            if not resource_id:
                return JSONResponse(
                    {"error": "Resource ID required"},
                    status_code=400
                )
            
            resource_service = ServiceContainer.get(ResourceService)
            if not resource_service.user_can_access(
                request.state.user_id, resource_id, action
            ):
                return JSONResponse(
                    {"error": "Access denied to resource"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

app = Velithon()

# Register services
class ResourceContainer(ServiceContainer):
    resource_service = ResourceService()

@app.get("/resources/{resource_id}")
@require_auth
@require_resource_permission("read")
async def get_resource(request: Request):
    """Get resource - requires read permission."""
    resource_id = request.path_params["resource_id"]
    resource_service = ServiceContainer.get(ResourceService)
    resource = resource_service.get_resource(resource_id)
    
    return JSONResponse({
        "resource": {
            "id": resource.id,
            "name": resource.name,
            "owner": resource.owner_id
        }
    })

@app.put("/resources/{resource_id}")
@require_auth
@require_resource_permission("write")
async def update_resource(request: Request):
    """Update resource - requires write permission."""
    resource_id = request.path_params["resource_id"]
    data = await request.json()
    
    return JSONResponse({
        "message": f"Resource {resource_id} updated successfully",
        "data": data
    })

@app.delete("/resources/{resource_id}")
@require_auth
@require_resource_permission("delete")
async def delete_resource(request: Request):
    """Delete resource - requires delete permission."""
    resource_id = request.path_params["resource_id"]
    
    return JSONResponse({
        "message": f"Resource {resource_id} deleted successfully"
    })
```

## Attribute-Based Access Control (ABAC)

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime, time

@dataclass
class AccessContext:
    user_id: str
    user_role: str
    user_department: str
    resource_id: str
    resource_type: str
    resource_sensitivity: str
    action: str
    time: datetime
    ip_address: str

class PolicyEngine:
    def __init__(self):
        self.policies = [
            self.working_hours_policy,
            self.department_access_policy,
            self.sensitivity_policy,
            self.admin_override_policy
        ]
    
    def evaluate(self, context: AccessContext) -> tuple[bool, str]:
        """Evaluate all policies and return access decision."""
        for policy in self.policies:
            allowed, reason = policy(context)
            if not allowed:
                return False, reason
        return True, "Access granted"
    
    def working_hours_policy(self, context: AccessContext) -> tuple[bool, str]:
        """Allow access only during working hours for sensitive resources."""
        if context.resource_sensitivity == "high":
            current_time = context.time.time()
            if not (time(9, 0) <= current_time <= time(17, 0)):
                return False, "Access to sensitive resources only allowed during working hours"
        return True, ""
    
    def department_access_policy(self, context: AccessContext) -> tuple[bool, str]:
        """Department-based access control."""
        if context.resource_type == "financial":
            if context.user_department not in ["finance", "executive"]:
                return False, "Financial resources only accessible by finance and executive departments"
        return True, ""
    
    def sensitivity_policy(self, context: AccessContext) -> tuple[bool, str]:
        """Sensitivity-based access control."""
        if context.resource_sensitivity == "confidential":
            if context.user_role not in ["manager", "admin"]:
                return False, "Confidential resources require manager or admin role"
        return True, ""
    
    def admin_override_policy(self, context: AccessContext) -> tuple[bool, str]:
        """Admins can access everything."""
        if context.user_role == "admin":
            return True, "Admin override"
        return True, ""

def check_abac_access(func):
    """Decorator for ABAC access control."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, "user_id"):
            return JSONResponse(
                {"error": "Authentication required"},
                status_code=401
            )
        
        # Build access context
        context = AccessContext(
            user_id=request.state.user_id,
            user_role=getattr(request.state, "role", "user"),
            user_department=getattr(request.state, "department", "general"),
            resource_id=request.path_params.get("resource_id", ""),
            resource_type=request.path_params.get("resource_type", "general"),
            resource_sensitivity=request.headers.get("X-Resource-Sensitivity", "low"),
            action=request.method.lower(),
            time=datetime.now(),
            ip_address=request.client.host if request.client else "unknown"
        )
        
        # Evaluate policies
        policy_engine = ServiceContainer.get(PolicyEngine)
        allowed, reason = policy_engine.evaluate(context)
        
        if not allowed:
            return JSONResponse(
                {"error": f"Access denied: {reason}"},
                status_code=403
            )
        
        return await func(request, *args, **kwargs)
    return wrapper

app = Velithon()
class PolicyContainer(ServiceContainer):
    policy_engine = PolicyEngine()

@app.get("/resources/{resource_type}/{resource_id}")
@require_auth
@check_abac_access
async def get_abac_resource(request: Request):
    """Get resource with ABAC authorization."""
    resource_type = request.path_params["resource_type"]
    resource_id = request.path_params["resource_id"]
    
    return JSONResponse({
        "resource_type": resource_type,
        "resource_id": resource_id,
        "message": "Access granted by ABAC policies"
    })
```

## Testing Authorization

```python
import pytest
import httpx
import jwt
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_role_based_access():
    """Test role-based access control."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        response = await client.post("/login", json={
            "username": "admin",
            "password": "admin"
        })
        admin_token = response.json()["token"]
        
        # Admin can access admin dashboard
        response = await client.get(
            "/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Login as regular user
        response = await client.post("/login", json={
            "username": "user",
            "password": "user"
        })
        user_token = response.json()["token"]
        
        # User cannot access admin dashboard
        response = await client.get(
            "/admin/dashboard",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_permission_based_access():
    """Test permission-based access control."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Login as user (has READ_USERS permission)
        response = await client.post("/login", json={
            "username": "user",
            "password": "user"
        })
        user_token = response.json()["token"]
        
        # User can read users
        response = await client.get(
            "/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        
        # User cannot create users (no WRITE_USERS permission)
        response = await client.post(
            "/users",
            json={"username": "newuser"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_resource_based_access():
    """Test resource-based access control."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Create token for user1
        auth_service = AuthorizationService()
        token = auth_service.create_token("user1", Role.USER)
        
        # User1 can access their own resource
        response = await client.get(
            "/resources/doc1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # User1 cannot access other user's resource
        response = await client.get(
            "/resources/doc2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_expired_token():
    """Test expired token handling."""
    auth_service = AuthorizationService()
    
    # Create expired token
    payload = {
        "user_id": "test",
        "role": "user",
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    }
    expired_token = jwt.encode(payload, auth_service.secret_key, algorithm="HS256")
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/users",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert "expired" in response.json()["error"].lower()
```

## Best Practices

1. **Principle of Least Privilege**: Grant minimum required permissions
2. **Role Hierarchy**: Design clear role hierarchies with inheritance
3. **Resource Ownership**: Implement clear resource ownership models
4. **Audit Logging**: Log all authorization decisions for compliance
5. **Token Management**: Implement proper token lifecycle management
6. **Policy Testing**: Thoroughly test authorization policies
7. **Performance**: Cache authorization decisions where appropriate
8. **Defense in Depth**: Use multiple layers of authorization checks
