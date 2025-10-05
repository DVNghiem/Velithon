"""Test endpoint for function dependency injection."""

from typing import Annotated

from velithon.endpoint import HTTPEndpoint
from velithon.requests import Request
from velithon.responses import JSONResponse


def get_user_id(request: Request) -> str:
    """Extract user ID from request headers."""
    return request.headers.get('X-User-ID', 'anonymous')


async def get_user_permissions(request: Request) -> list[str]:
    """Get user permissions asynchronously."""
    user_id = request.headers.get('X-User-ID', 'anonymous')

    if user_id == 'admin':
        return ['read', 'write', 'delete']
    elif user_id == 'user':
        return ['read', 'write']
    else:
        return ['read']


def get_constant(_) -> str:
    """Return a constant value (no request needed)."""
    return 'constant_value'


class TestFunctionDependencyEndpoint(HTTPEndpoint):
    """Test endpoint for function dependency injection."""

    def get(
        self,
        user_id: Annotated[str, get_user_id],
        permissions: Annotated[list[str], get_user_permissions],
        constant: Annotated[str, get_constant],
    ) -> JSONResponse:
        """Handle GET request with function dependencies."""
        return JSONResponse(
            {
                'user_id': user_id,
                'permissions': permissions,
                'constant': constant,
            }
        )


class TestSimpleFunctionDependencyEndpoint(HTTPEndpoint):
    """Test endpoint for simple function dependency injection."""

    async def get(
        self,
        user_id: Annotated[str, get_user_id],
    ) -> JSONResponse:
        """Handle GET request with simple function dependency."""
        return JSONResponse({'user_id': user_id})
