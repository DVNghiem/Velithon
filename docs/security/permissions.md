# Permissions

This guide covers implementing fine-grained permissions and access control in Velithon applications.

## Permission-Based Access Control

```python
from velithon import Velithon, Request
from velithon.responses import JSONResponse
from velithon.di import inject, Provide, ServiceContainer
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Any
from functools import wraps
import json

class Action(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"

class ResourceType(Enum):
    USER = "user"
    POST = "post"
    COMMENT = "comment"
    FILE = "file"
    ADMIN = "admin"

@dataclass
class Permission:
    id: str
    name: str
    description: str
    resource_type: ResourceType
    action: Action

@dataclass
class Role:
    id: str
    name: str
    description: str
    permissions: Set[str]  # Set of permission IDs

@dataclass
class User:
    id: str
    username: str
    roles: Set[str]  # Set of role IDs
    direct_permissions: Set[str]  # Direct permission assignments

class PermissionService:
    def __init__(self):
        self.permissions: Dict[str, Permission] = {}
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        
        # Initialize default permissions and roles
        self._initialize_permissions()
        self._initialize_roles()
        self._initialize_users()
    
    def _initialize_permissions(self):
        """Initialize default permissions."""
        permissions = [
            # User permissions
            Permission("user.create", "Create User", "Create new users", ResourceType.USER, Action.CREATE),
            Permission("user.read", "Read User", "View user information", ResourceType.USER, Action.READ),
            Permission("user.update", "Update User", "Modify user information", ResourceType.USER, Action.UPDATE),
            Permission("user.delete", "Delete User", "Delete users", ResourceType.USER, Action.DELETE),
            
            # Post permissions
            Permission("post.create", "Create Post", "Create new posts", ResourceType.POST, Action.CREATE),
            Permission("post.read", "Read Post", "View posts", ResourceType.POST, Action.READ),
            Permission("post.update", "Update Post", "Modify posts", ResourceType.POST, Action.UPDATE),
            Permission("post.delete", "Delete Post", "Delete posts", ResourceType.POST, Action.DELETE),
            
            # Comment permissions
            Permission("comment.create", "Create Comment", "Create comments", ResourceType.COMMENT, Action.CREATE),
            Permission("comment.read", "Read Comment", "View comments", ResourceType.COMMENT, Action.READ),
            Permission("comment.update", "Update Comment", "Modify comments", ResourceType.COMMENT, Action.UPDATE),
            Permission("comment.delete", "Delete Comment", "Delete comments", ResourceType.COMMENT, Action.DELETE),
            
            # File permissions
            Permission("file.create", "Upload File", "Upload files", ResourceType.FILE, Action.CREATE),
            Permission("file.read", "Download File", "Download files", ResourceType.FILE, Action.READ),
            Permission("file.update", "Update File", "Modify files", ResourceType.FILE, Action.UPDATE),
            Permission("file.delete", "Delete File", "Delete files", ResourceType.FILE, Action.DELETE),
            
            # Admin permissions
            Permission("admin.read", "Admin Read", "View admin information", ResourceType.ADMIN, Action.READ),
            Permission("admin.execute", "Admin Execute", "Execute admin operations", ResourceType.ADMIN, Action.EXECUTE),
        ]
        
        for perm in permissions:
            self.permissions[perm.id] = perm
    
    def _initialize_roles(self):
        """Initialize default roles."""
        roles = [
            Role(
                "guest",
                "Guest",
                "Basic read-only access",
                {"post.read", "comment.read"}
            ),
            Role(
                "user",
                "Regular User",
                "Standard user permissions",
                {"post.read", "post.create", "post.update", "comment.read", "comment.create", "comment.update", "file.read"}
            ),
            Role(
                "moderator",
                "Moderator",
                "Content moderation permissions",
                {"post.read", "post.create", "post.update", "post.delete", "comment.read", "comment.create", "comment.update", "comment.delete", "file.read", "file.delete"}
            ),
            Role(
                "admin",
                "Administrator",
                "Full administrative access",
                set(self.permissions.keys())  # All permissions
            )
        ]
        
        for role in roles:
            self.roles[role.id] = role
    
    def _initialize_users(self):
        """Initialize demo users."""
        users = [
            User("user1", "john_doe", {"user"}, set()),
            User("user2", "jane_smith", {"user", "moderator"}, set()),
            User("admin1", "admin", {"admin"}, set()),
        ]
        
        for user in users:
            self.users[user.id] = user
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user (from roles + direct permissions)."""
        user = self.users.get(user_id)
        if not user:
            return set()
        
        all_permissions = set(user.direct_permissions)
        
        # Add permissions from roles
        for role_id in user.roles:
            role = self.roles.get(role_id)
            if role:
                all_permissions.update(role.permissions)
        
        return all_permissions
    
    def has_permission(self, user_id: str, permission_id: str) -> bool:
        """Check if user has specific permission."""
        user_permissions = self.get_user_permissions(user_id)
        return permission_id in user_permissions
    
    def has_resource_permission(self, user_id: str, resource_type: ResourceType, action: Action) -> bool:
        """Check if user has permission for resource type and action."""
        permission_id = f"{resource_type.value}.{action.value}"
        return self.has_permission(user_id, permission_id)
    
    def add_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Add role to user."""
        user = self.users.get(user_id)
        if not user or role_id not in self.roles:
            return False
        
        user.roles.add(role_id)
        return True
    
    def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Remove role from user."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.roles.discard(role_id)
        return True
    
    def grant_permission(self, user_id: str, permission_id: str) -> bool:
        """Grant direct permission to user."""
        user = self.users.get(user_id)
        if not user or permission_id not in self.permissions:
            return False
        
        user.direct_permissions.add(permission_id)
        return True
    
    def revoke_permission(self, user_id: str, permission_id: str) -> bool:
        """Revoke direct permission from user."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.direct_permissions.discard(permission_id)
        return True

def require_permission(permission_id: str):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get current user (from authentication)
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            permission_service = ServiceContainer.get(PermissionService)
            if not permission_service.has_permission(user_id, permission_id):
                return JSONResponse(
                    {"error": f"Permission '{permission_id}' required"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_resource_permission(resource_type: ResourceType, action: Action):
    """Decorator to require permission for resource type and action."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            permission_service = ServiceContainer.get(PermissionService)
            if not permission_service.has_resource_permission(user_id, resource_type, action):
                return JSONResponse(
                    {"error": f"Permission required: {resource_type.value}.{action.value}"},
                    status_code=403
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def check_permissions(*permission_ids):
    """Decorator to check multiple permissions (all required)."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            permission_service = ServiceContainer.get(PermissionService)
            
            for permission_id in permission_ids:
                if not permission_service.has_permission(user_id, permission_id):
                    return JSONResponse(
                        {"error": f"Missing required permission: {permission_id}"},
                        status_code=403
                    )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def check_any_permission(*permission_ids):
    """Decorator to check if user has any of the specified permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            permission_service = ServiceContainer.get(PermissionService)
            
            for permission_id in permission_ids:
                if permission_service.has_permission(user_id, permission_id):
                    return await func(request, *args, **kwargs)
            
            return JSONResponse(
                {"error": f"One of these permissions required: {', '.join(permission_ids)}"},
                status_code=403
            )
        return wrapper
    return decorator

app = Velithon()

# Register services
class PermissionContainer(ServiceContainer):
    permission_service = PermissionService()

# Mock authentication middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Mock authentication middleware."""
    # In real app, extract user from JWT token or session
    user_id = request.headers.get("X-User-ID", "user1")  # Mock user ID
    request.state.user_id = user_id
    
    response = await call_next(request)
    return response

# Permission management endpoints

@app.get("/permissions")
async def list_permissions(request: Request):
    """List all available permissions."""
    permission_service = ServiceContainer.get(PermissionService)
    
    permissions = [
        {
            "id": perm.id,
            "name": perm.name,
            "description": perm.description,
            "resource_type": perm.resource_type.value,
            "action": perm.action.value
        }
        for perm in permission_service.permissions.values()
    ]
    
    return JSONResponse({"permissions": permissions})

@app.get("/roles")
async def list_roles(request: Request):
    """List all available roles."""
    permission_service = ServiceContainer.get(PermissionService)
    
    roles = [
        {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": list(role.permissions)
        }
        for role in permission_service.roles.values()
    ]
    
    return JSONResponse({"roles": roles})

@app.get("/users/{user_id}/permissions")
async def get_user_permissions(request: Request):
    """Get user's effective permissions."""
    target_user_id = request.path_params["user_id"]
    current_user_id = request.state.user_id
    
    # Users can view their own permissions, admins can view any
    permission_service = ServiceContainer.get(PermissionService)
    if (target_user_id != current_user_id and 
        not permission_service.has_permission(current_user_id, "admin.read")):
        return JSONResponse(
            {"error": "Access denied"},
            status_code=403
        )
    
    user = permission_service.users.get(target_user_id)
    if not user:
        return JSONResponse(
            {"error": "User not found"},
            status_code=404
        )
    
    user_permissions = permission_service.get_user_permissions(target_user_id)
    
    return JSONResponse({
        "user_id": target_user_id,
        "username": user.username,
        "roles": list(user.roles),
        "direct_permissions": list(user.direct_permissions),
        "effective_permissions": list(user_permissions)
    })

@app.post("/users/{user_id}/roles")
@require_permission("admin.execute")
async def add_role_to_user(request: Request):
    """Add role to user (admin only)."""
    user_id = request.path_params["user_id"]
    data = await request.json()
    role_id = data.get("role_id")
    
    if not role_id:
        return JSONResponse(
            {"error": "role_id is required"},
            status_code=400
        )
    
    permission_service = ServiceContainer.get(PermissionService)
    success = permission_service.add_role_to_user(user_id, role_id)
    
    if not success:
        return JSONResponse(
            {"error": "Failed to add role (user or role not found)"},
            status_code=400
        )
    
    return JSONResponse({
        "message": f"Role '{role_id}' added to user '{user_id}'"
    })

@app.delete("/users/{user_id}/roles/{role_id}")
@require_permission("admin.execute")
async def remove_role_from_user(request: Request):
    """Remove role from user (admin only)."""
    user_id = request.path_params["user_id"]
    role_id = request.path_params["role_id"]
    
    permission_service = ServiceContainer.get(PermissionService)
    success = permission_service.remove_role_from_user(user_id, role_id)
    
    if not success:
        return JSONResponse(
            {"error": "Failed to remove role (user not found)"},
            status_code=400
        )
    
    return JSONResponse({
        "message": f"Role '{role_id}' removed from user '{user_id}'"
    })

@app.post("/users/{user_id}/permissions")
@require_permission("admin.execute")
async def grant_permission_to_user(request: Request):
    """Grant direct permission to user (admin only)."""
    user_id = request.path_params["user_id"]
    data = await request.json()
    permission_id = data.get("permission_id")
    
    if not permission_id:
        return JSONResponse(
            {"error": "permission_id is required"},
            status_code=400
        )
    
    permission_service = ServiceContainer.get(PermissionService)
    success = permission_service.grant_permission(user_id, permission_id)
    
    if not success:
        return JSONResponse(
            {"error": "Failed to grant permission (user or permission not found)"},
            status_code=400
        )
    
    return JSONResponse({
        "message": f"Permission '{permission_id}' granted to user '{user_id}'"
    })

@app.delete("/users/{user_id}/permissions/{permission_id}")
@require_permission("admin.execute")
async def revoke_permission_from_user(request: Request):
    """Revoke direct permission from user (admin only)."""
    user_id = request.path_params["user_id"]
    permission_id = request.path_params["permission_id"]
    
    permission_service = ServiceContainer.get(PermissionService)
    success = permission_service.revoke_permission(user_id, permission_id)
    
    if not success:
        return JSONResponse(
            {"error": "Failed to revoke permission (user not found)"},
            status_code=400
        )
    
    return JSONResponse({
        "message": f"Permission '{permission_id}' revoked from user '{user_id}'"
    })

# Protected resource endpoints

@app.get("/posts")
@require_resource_permission(ResourceType.POST, Action.READ)
async def get_posts(request: Request):
    """Get posts - requires post.read permission."""
    return JSONResponse({
        "posts": [
            {"id": 1, "title": "Post 1", "content": "Content 1"},
            {"id": 2, "title": "Post 2", "content": "Content 2"},
            {"id": 3, "title": "Post 3", "content": "Content 3"}
        ]
    })

@app.post("/posts")
@require_resource_permission(ResourceType.POST, Action.CREATE)
async def create_post(request: Request):
    """Create post - requires post.create permission."""
    data = await request.json()
    return JSONResponse({
        "message": "Post created successfully",
        "post": data,
        "created_by": request.state.user_id
    })

@app.put("/posts/{post_id}")
@require_resource_permission(ResourceType.POST, Action.UPDATE)
async def update_post(request: Request):
    """Update post - requires post.update permission."""
    post_id = request.path_params["post_id"]
    data = await request.json()
    
    return JSONResponse({
        "message": f"Post {post_id} updated successfully",
        "post": data,
        "updated_by": request.state.user_id
    })

@app.delete("/posts/{post_id}")
@require_resource_permission(ResourceType.POST, Action.DELETE)
async def delete_post(request: Request):
    """Delete post - requires post.delete permission."""
    post_id = request.path_params["post_id"]
    
    return JSONResponse({
        "message": f"Post {post_id} deleted successfully",
        "deleted_by": request.state.user_id
    })

@app.get("/admin/users")
@check_permissions("admin.read", "user.read")
async def admin_get_users(request: Request):
    """Admin endpoint requiring multiple permissions."""
    permission_service = ServiceContainer.get(PermissionService)
    
    users = [
        {
            "id": user.id,
            "username": user.username,
            "roles": list(user.roles),
            "permissions": list(permission_service.get_user_permissions(user.id))
        }
        for user in permission_service.users.values()
    ]
    
    return JSONResponse({"users": users})

@app.get("/moderation/content")
@check_any_permission("post.delete", "comment.delete", "admin.execute")
async def moderate_content(request: Request):
    """Moderation endpoint - requires any moderation permission."""
    return JSONResponse({
        "message": "Moderation access granted",
        "pending_items": [
            {"type": "post", "id": 1, "reason": "spam"},
            {"type": "comment", "id": 5, "reason": "inappropriate"}
        ]
    })

if __name__ == "__main__":
    # Run with: velithon run --app permissions_example:app --host 0.0.0.0 --port 8000
    print("Run with: velithon run --app permissions_example:app --host 0.0.0.0 --port 8000")
```

## Resource-Level Permissions

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ResourcePermission:
    user_id: str
    resource_type: str
    resource_id: str
    permissions: Set[str]

class ResourcePermissionService:
    def __init__(self):
        self.resource_permissions: Dict[str, ResourcePermission] = {}
    
    def _get_key(self, user_id: str, resource_type: str, resource_id: str) -> str:
        """Generate key for resource permission."""
        return f"{user_id}:{resource_type}:{resource_id}"
    
    def grant_resource_permission(
        self, 
        user_id: str, 
        resource_type: str, 
        resource_id: str, 
        permissions: Set[str]
    ):
        """Grant permissions for specific resource."""
        key = self._get_key(user_id, resource_type, resource_id)
        
        if key in self.resource_permissions:
            self.resource_permissions[key].permissions.update(permissions)
        else:
            self.resource_permissions[key] = ResourcePermission(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                permissions=permissions
            )
    
    def has_resource_permission(
        self, 
        user_id: str, 
        resource_type: str, 
        resource_id: str, 
        permission: str
    ) -> bool:
        """Check if user has permission for specific resource."""
        key = self._get_key(user_id, resource_type, resource_id)
        resource_perm = self.resource_permissions.get(key)
        
        if resource_perm:
            return permission in resource_perm.permissions
        
        return False

def require_resource_access(resource_type: str, permission: str):
    """Decorator for resource-level permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user_id = getattr(request.state, "user_id", None)
            if not user_id:
                return JSONResponse(
                    {"error": "Authentication required"},
                    status_code=401
                )
            
            # Extract resource ID from path parameters
            resource_id = request.path_params.get("resource_id") or request.path_params.get("id")
            if not resource_id:
                return JSONResponse(
                    {"error": "Resource ID required"},
                    status_code=400
                )
            
            # Check general permission first
            permission_service = ServiceContainer.get(PermissionService)
            general_permission = f"{resource_type}.{permission}"
            
            if permission_service.has_permission(user_id, general_permission):
                return await func(request, *args, **kwargs)
            
            # Check resource-specific permission
            resource_perm_service = ServiceContainer.get(ResourcePermissionService)
            if resource_perm_service.has_resource_permission(user_id, resource_type, resource_id, permission):
                return await func(request, *args, **kwargs)
            
            return JSONResponse(
                {"error": f"Permission '{permission}' required for {resource_type} {resource_id}"},
                status_code=403
            )
        return wrapper
    return decorator

# Register resource permission service
class ResourcePermissionContainer(ServiceContainer):
    resource_permission_service = ResourcePermissionService()

@app.get("/files/{file_id}")
@require_resource_access("file", "read")
async def get_file(request: Request):
    """Get specific file with resource-level permissions."""
    file_id = request.path_params["file_id"]
    return JSONResponse({
        "file_id": file_id,
        "filename": f"file_{file_id}.txt",
        "content": "File content here..."
    })

@app.put("/files/{file_id}")
@require_resource_access("file", "update")
async def update_file(request: Request):
    """Update specific file with resource-level permissions."""
    file_id = request.path_params["file_id"]
    data = await request.json()
    
    return JSONResponse({
        "message": f"File {file_id} updated",
        "data": data
    })
```

## Testing Permissions

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_permission_enforcement():
    """Test permission enforcement on endpoints."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # user1 has 'user' role with post.read permission
        response = await client.get(
            "/posts",
            headers={"X-User-ID": "user1"}
        )
        assert response.status_code == 200
        
        # user1 doesn't have post.delete permission
        response = await client.delete(
            "/posts/1",
            headers={"X-User-ID": "user1"}
        )
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_admin_permissions():
    """Test admin permissions."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # admin1 has all permissions
        response = await client.get(
            "/admin/users",
            headers={"X-User-ID": "admin1"}
        )
        assert response.status_code == 200
        
        # Regular user cannot access admin endpoint
        response = await client.get(
            "/admin/users",
            headers={"X-User-ID": "user1"}
        )
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_role_management():
    """Test role management endpoints."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Add role to user (admin only)
        response = await client.post(
            "/users/user1/roles",
            json={"role_id": "moderator"},
            headers={"X-User-ID": "admin1"}
        )
        assert response.status_code == 200
        
        # Non-admin cannot add roles
        response = await client.post(
            "/users/user1/roles",
            json={"role_id": "moderator"},
            headers={"X-User-ID": "user1"}
        )
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_permission_management():
    """Test direct permission management."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Grant permission (admin only)
        response = await client.post(
            "/users/user1/permissions",
            json={"permission_id": "post.delete"},
            headers={"X-User-ID": "admin1"}
        )
        assert response.status_code == 200
        
        # Verify user now has the permission
        response = await client.delete(
            "/posts/1",
            headers={"X-User-ID": "user1"}
        )
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_multiple_permissions():
    """Test endpoints requiring multiple permissions."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Admin endpoint requires both admin.read and user.read
        response = await client.get(
            "/admin/users",
            headers={"X-User-ID": "admin1"}
        )
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_any_permission():
    """Test endpoints requiring any of multiple permissions."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Moderation endpoint accepts any moderation permission
        response = await client.get(
            "/moderation/content",
            headers={"X-User-ID": "user2"}  # user2 has moderator role
        )
        assert response.status_code == 200

def test_permission_service():
    """Test permission service functionality."""
    permission_service = PermissionService()
    
    # Test has_permission
    assert permission_service.has_permission("user1", "post.read")
    assert not permission_service.has_permission("user1", "post.delete")
    
    # Test role management
    assert permission_service.add_role_to_user("user1", "moderator")
    assert permission_service.has_permission("user1", "post.delete")
    
    # Test direct permission grant
    assert permission_service.grant_permission("user1", "admin.read")
    assert permission_service.has_permission("user1", "admin.read")
    
    # Test permission revocation
    assert permission_service.revoke_permission("user1", "admin.read")
    assert not permission_service.has_permission("user1", "admin.read")
```

## Permission Caching

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional

class PermissionCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.cache: Dict[str, tuple[Set[str], datetime]] = {}
        self.ttl_seconds = ttl_seconds
    
    def _get_cache_key(self, user_id: str) -> str:
        return f"permissions:{user_id}"
    
    def get(self, user_id: str) -> Optional[Set[str]]:
        """Get cached permissions for user."""
        key = self._get_cache_key(user_id)
        
        if key in self.cache:
            permissions, cached_at = self.cache[key]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.ttl_seconds):
                return permissions
            else:
                # Cache expired
                del self.cache[key]
        
        return None
    
    def set(self, user_id: str, permissions: Set[str]):
        """Cache permissions for user."""
        key = self._get_cache_key(user_id)
        self.cache[key] = (permissions, datetime.utcnow())
    
    def invalidate(self, user_id: str):
        """Invalidate cached permissions for user."""
        key = self._get_cache_key(user_id)
        self.cache.pop(key, None)
    
    def clear(self):
        """Clear all cached permissions."""
        self.cache.clear()

class CachedPermissionService(PermissionService):
    def __init__(self):
        super().__init__()
        self.cache = PermissionCache()
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get user permissions with caching."""
        # Try cache first
        cached_permissions = self.cache.get(user_id)
        if cached_permissions is not None:
            return cached_permissions
        
        # Compute permissions
        permissions = super().get_user_permissions(user_id)
        
        # Cache result
        self.cache.set(user_id, permissions)
        
        return permissions
    
    def add_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Add role and invalidate cache."""
        result = super().add_role_to_user(user_id, role_id)
        if result:
            self.cache.invalidate(user_id)
        return result
    
    def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Remove role and invalidate cache."""
        result = super().remove_role_from_user(user_id, role_id)
        if result:
            self.cache.invalidate(user_id)
        return result
    
    def grant_permission(self, user_id: str, permission_id: str) -> bool:
        """Grant permission and invalidate cache."""
        result = super().grant_permission(user_id, permission_id)
        if result:
            self.cache.invalidate(user_id)
        return result
    
    def revoke_permission(self, user_id: str, permission_id: str) -> bool:
        """Revoke permission and invalidate cache."""
        result = super().revoke_permission(user_id, permission_id)
        if result:
            self.cache.invalidate(user_id)
        return result
```

## Best Practices

1. **Principle of Least Privilege**: Grant minimum required permissions
2. **Role-Based Design**: Use roles for common permission sets
3. **Resource-Level Permissions**: Implement fine-grained access control
4. **Permission Caching**: Cache permissions to improve performance
5. **Audit Logging**: Log all permission changes and access attempts
6. **Regular Reviews**: Periodically review and cleanup permissions
7. **Clear Naming**: Use descriptive permission and role names
8. **Documentation**: Document all permissions and their purposes
9. **Testing**: Thoroughly test permission enforcement
10. **Separation of Concerns**: Keep permission logic separate from business logic
