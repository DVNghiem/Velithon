# Custom Documentation

Learn how to customize and extend the automatically generated OpenAPI documentation in Velithon.

## Overview

While Velithon provides excellent automatic documentation, you can customize and extend it to meet specific requirements or add additional information.

## Custom OpenAPI Schema

```python
from velithon import Velithon

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = {
        "openapi": "3.0.2",
        "info": {
            "title": "My Custom API",
            "version": "2.0.0",
            "description": "A customized API documentation",
            "termsOfService": "https://example.com/terms/",
            "contact": {
                "name": "API Support",
                "url": "https://example.com/contact/",
                "email": "support@example.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "https://api.example.com/v1",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.example.com/v1", 
                "description": "Staging server"
            }
        ]
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = Velithon()
app.openapi = custom_openapi
```

## Custom Response Examples

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int = Field(example=1)
    name: str = Field(example="John Doe")
    email: str = Field(example="john@example.com")
    created_at: str = Field(example="2025-01-01T00:00:00Z")

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """
    Get user by ID.
    
    Example responses are defined in the User model using Field(example=...).
    """
    return User(
        id=user_id,
        name="John Doe",
        email="john@example.com",
        created_at="2025-01-01T00:00:00Z"
    )
```

## Multiple Response Examples

```python
from typing import Union

class UserResponse(BaseModel):
    user: User
    message: str = Field(example="User retrieved successfully")

class NotFoundResponse(BaseModel):
    error: str = Field(example="User not found")
    code: int = Field(example=404)

@app.get("/users/{user_id}")
async def get_user_with_examples(user_id: int) -> Union[UserResponse, NotFoundResponse]:
    """
    Get user by ID with multiple response examples.
    
    Responses:
    - 200: User found and returned
    - 404: User not found
    """
    if user_id > 0:
        return UserResponse(
            user=User(id=user_id, name="John", email="john@example.com", created_at="2025-01-01T00:00:00Z"),
            message="User retrieved successfully"
        )
    else:
        return NotFoundResponse(error="User not found", code=404)
```

## Custom Parameter Documentation

```python
from typing import Optional
from enum import Enum

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"

@app.get("/users")
async def get_users_with_custom_params(
    page: int = Field(1, ge=1, description="Page number starting from 1"),
    per_page: int = Field(10, ge=1, le=100, description="Number of items per page (1-100)"),
    sort_by: Optional[str] = Field(None, description="Field to sort by (name, email, created_at)"),
    sort_order: SortOrder = Field(SortOrder.asc, description="Sort order"),
    status: Optional[UserStatus] = Field(None, description="Filter by user status"),
    search: Optional[str] = Field(None, min_length=3, description="Search term (minimum 3 characters)")
):
    """
    Get users with advanced filtering and pagination.
    
    This endpoint demonstrates custom parameter documentation with:
    - Validation constraints
    - Enum values
    - Detailed descriptions
    """
    return {"users": [], "page": page, "per_page": per_page}
```

## Custom Security Documentation

```python
from velithon.security import SecurityBase

class CustomAPIKeyAuth(SecurityBase):
    def __init__(self, name: str = "X-API-Key"):
        self.scheme_name = name
        self.auto_error = True

api_key_auth = CustomAPIKeyAuth()

@app.get("/admin/users")
async def admin_get_users(api_key: str = api_key_auth):
    """
    Admin endpoint to get users.
    
    Requires API key authentication via X-API-Key header.
    """
    return {"users": [], "admin": True}

# Add security scheme to documentation
app.openapi_security_schemes = {
    "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key for administrative access"
    }
}
```

## Custom Tags and Metadata

```python
# Define detailed tag information
app.openapi_tags = [
    {
        "name": "users",
        "description": "User management operations",
        "externalDocs": {
            "description": "User guide",
            "url": "https://docs.example.com/users"
        }
    },
    {
        "name": "admin",
        "description": "Administrative operations (requires API key)",
        "externalDocs": {
            "description": "Admin guide", 
            "url": "https://docs.example.com/admin"
        }
    }
]

@app.get("/users", tags=["users"])
async def get_users():
    """Get all users"""
    pass

@app.delete("/admin/users/{user_id}", tags=["admin"])
async def admin_delete_user(user_id: int):
    """Delete user (admin only)"""
    pass
```

## Custom Documentation UI

```python
from velithon.openapi import get_swagger_ui_html, get_redoc_html

@app.get("/custom-docs", include_in_schema=False)
async def custom_documentation():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Custom API Documentation",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.js",
        custom_css="""
        .swagger-ui .topbar { background-color: #2c3e50; }
        .swagger-ui .topbar .download-url-wrapper { display: none; }
        """
    )

@app.get("/custom-redoc", include_in_schema=False)
async def custom_redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Custom API Reference",
        redoc_css_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.css",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"
    )
```

## External Documentation Links

```python
@app.get("/complex-operation")
async def complex_operation():
    """
    Perform a complex operation.
    
    This operation has detailed documentation available externally.
    See: https://docs.example.com/complex-operations
    
    For implementation details, refer to:
    https://github.com/example/api/wiki/Complex-Operations
    """
    return {"status": "completed"}

# Add external docs to OpenAPI schema
def add_external_docs():
    schema = app.openapi_schema
    if schema:
        schema["externalDocs"] = {
            "description": "Complete API Documentation",
            "url": "https://docs.example.com"
        }
```

## Conditional Documentation

```python
import os

# Hide internal endpoints in production
@app.get("/internal/debug", include_in_schema=os.getenv("ENV") != "production")
async def debug_endpoint():
    """Internal debug endpoint (development only)"""
    return {"debug": True, "env": os.getenv("ENV")}

# Different documentation for different environments
def get_environment_specific_openapi():
    base_schema = app.openapi_schema
    
    if os.getenv("ENV") == "production":
        # Remove development-specific information
        base_schema["info"]["description"] += " (Production API)"
        base_schema["servers"] = [{"url": "https://api.example.com"}]
    else:
        # Add development information
        base_schema["info"]["description"] += " (Development API)"
        base_schema["servers"] = [{"url": "http://localhost:8000"}]
    
    return base_schema
```

## Best Practices

1. **Use Field descriptions** for detailed parameter documentation
2. **Provide multiple examples** for complex responses
3. **Document security requirements** clearly
4. **Group related endpoints** with meaningful tags
5. **Include external documentation links** when helpful
6. **Customize UI styling** to match your brand
7. **Hide internal endpoints** in production documentation
