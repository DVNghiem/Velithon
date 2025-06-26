"""Permission system for Velithon authentication."""

from typing import Any, Callable, Sequence

from velithon.requests import Request

from .exceptions import AuthorizationError


class Permission:
    """Base permission class."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize permission."""
        self.name = name
        self.description = description
    
    def __str__(self) -> str:
        """String representation of permission."""
        return self.name
    
    def __repr__(self) -> str:
        """Detailed representation of permission."""
        return f"Permission(name='{self.name}', description='{self.description}')"
    
    def __eq__(self, other: object) -> bool:
        """Check permission equality."""
        if isinstance(other, Permission):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False
    
    def __hash__(self) -> int:
        """Hash permission for use in sets."""
        return hash(self.name)


class PermissionChecker:
    """Permission checking utility."""
    
    @staticmethod
    def has_permission(
        user_permissions: Sequence[str | Permission],
        required_permission: str | Permission
    ) -> bool:
        """Check if user has required permission."""
        required_name = (
            required_permission.name
            if isinstance(required_permission, Permission)
            else required_permission
        )
        
        for perm in user_permissions:
            perm_name = perm.name if isinstance(perm, Permission) else perm
            if perm_name == required_name:
                return True
        
        return False
    
    @staticmethod
    def has_any_permission(
        user_permissions: Sequence[str | Permission],
        required_permissions: Sequence[str | Permission]
    ) -> bool:
        """Check if user has any of the required permissions."""
        for required_perm in required_permissions:
            if PermissionChecker.has_permission(user_permissions, required_perm):
                return True
        return False
    
    @staticmethod
    def has_all_permissions(
        user_permissions: Sequence[str | Permission],
        required_permissions: Sequence[str | Permission]
    ) -> bool:
        """Check if user has all required permissions."""
        for required_perm in required_permissions:
            if not PermissionChecker.has_permission(user_permissions, required_perm):
                return False
        return True


def require_permissions(
    permissions: str | Permission | Sequence[str | Permission],
    require_all: bool = True
) -> Callable:
    """Decorator to require specific permissions for endpoints."""
    
    if isinstance(permissions, (str, Permission)):
        permissions = [permissions]
    
    def decorator(func: Callable) -> Callable:
        """Permission decorator."""
        
        async def wrapper(*args, **kwargs):
            """Permission wrapper."""
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Look in kwargs
                request = kwargs.get('request')
            
            if not request:
                raise AuthorizationError("Request object not found")
            
            # Get current user from request
            user = getattr(request, 'user', None)
            if not user:
                raise AuthorizationError("User not authenticated")
            
            # Check permissions
            user_permissions = getattr(user, 'scopes', [])
            
            if require_all:
                if not PermissionChecker.has_all_permissions(
                    user_permissions, permissions
                ):
                    missing_perms = [
                        perm for perm in permissions
                        if not PermissionChecker.has_permission(user_permissions, perm)
                    ]
                    raise AuthorizationError(
                        f"Missing required permissions: {missing_perms}"
                    )
            else:
                if not PermissionChecker.has_any_permission(
                    user_permissions, permissions
                ):
                    raise AuthorizationError(
                        f"Missing any of required permissions: {list(permissions)}"
                    )
            
            return await func(*args, **kwargs)
        
        # Preserve original function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__annotations__ = func.__annotations__
        
        # Add permission metadata for introspection
        wrapper._required_permissions = permissions
        wrapper._require_all_permissions = require_all
        
        return wrapper
    
    return decorator


class PermissionDependency:
    """Permission dependency for use in endpoint parameters."""
    
    def __init__(
        self,
        permissions: str | Permission | Sequence[str | Permission],
        require_all: bool = True
    ):
        """Initialize permission dependency."""
        if isinstance(permissions, (str, Permission)):
            permissions = [permissions]
        
        self.permissions = permissions
        self.require_all = require_all
    
    async def __call__(self, request: Request) -> None:
        """Check permissions from request."""
        user = getattr(request, 'user', None)
        if not user:
            raise AuthorizationError("User not authenticated")
        
        user_permissions = getattr(user, 'scopes', [])
        
        if self.require_all:
            if not PermissionChecker.has_all_permissions(
                user_permissions, self.permissions
            ):
                missing_perms = [
                    perm for perm in self.permissions
                    if not PermissionChecker.has_permission(user_permissions, perm)
                ]
                raise AuthorizationError(
                    f"Missing required permissions: {missing_perms}"
                )
        else:
            if not PermissionChecker.has_any_permission(
                user_permissions, self.permissions
            ):
                raise AuthorizationError(
                    f"Missing any of required permissions: {list(self.permissions)}"
                )


# Common permission definitions
class CommonPermissions:
    """Common permission definitions."""
    
    # User management
    USER_READ = Permission("user:read", "Read user information")
    USER_WRITE = Permission("user:write", "Write user information")
    USER_DELETE = Permission("user:delete", "Delete users")
    
    # Admin permissions
    ADMIN_READ = Permission("admin:read", "Admin read access")
    ADMIN_WRITE = Permission("admin:write", "Admin write access")
    ADMIN_FULL = Permission("admin:full", "Full admin access")
    
    # API permissions
    API_READ = Permission("api:read", "API read access")
    API_WRITE = Permission("api:write", "API write access")
    
    # File permissions
    FILE_READ = Permission("file:read", "Read files")
    FILE_WRITE = Permission("file:write", "Write files")
    FILE_DELETE = Permission("file:delete", "Delete files")


def Depends(dependency: Any) -> Any:
    """Dependency injection marker (placeholder for Velithon's DI system)."""
    return dependency


def RequirePermissions(
    permissions: str | Permission | Sequence[str | Permission],
    require_all: bool = True
) -> PermissionDependency:
    """Create a permission dependency for endpoint parameters."""
    return PermissionDependency(permissions, require_all)


def require_permission(permission: str | Permission) -> Callable:
    """Create a permission dependency that requires a single permission.
    
    Args:
        permission: The permission required to access the endpoint.
        
    Returns:
        A dependency function that checks the user has the required permission.
    """
    async def check_permission(request: Request) -> None:
        """Check if current user has required permission."""
        # Get current user from request state (set by authentication middleware)
        user = getattr(request.state, 'user', None)
        if not user:
            raise AuthorizationError("User not authenticated")
        
        # Check if user has the required permission
        user_permissions = getattr(user, 'permissions', [])
        permission_name = permission.name if isinstance(permission, Permission) else permission
        
        if permission_name not in user_permissions:
            raise AuthorizationError(f"Missing required permission: {permission_name}")
    
    return check_permission
