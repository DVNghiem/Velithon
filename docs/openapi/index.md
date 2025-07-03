# OpenAPI & Documentation

Velithon provides automatic OpenAPI documentation generation with built-in Swagger UI integration.

## Overview

Velithon automatically generates OpenAPI 3.0 documentation based on your route definitions, type hints, and docstrings. The documentation is available through Swagger UI at the `/docs` endpoint.

**Note**: Velithon has its own implementation of OpenAPI documentation that differs from FastAPI. It uses `Annotated` type hints for dependency injection rather than `Depends`, and some parameters like `status_code` and `responses` in route decorators are handled differently.

## Automatic Documentation

### Basic Setup

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = Velithon(
    title="My API",
    description="A comprehensive API built with Velithon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

class User(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None

class UserCreate(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

@app.get("/users", response_model=List[User], tags=["users"])
async def get_users() -> List[User]:
    """
    Get all users
    
    Returns a list of all users in the system.
    """
    return get_all_users()

@app.post("/users", response_model=User, tags=["users"])
async def create_user(user: UserCreate) -> User:
    """
    Create a new user
    
    Creates a new user with the provided information.
    
    Args:
        user: User information to create
        
    Returns:
        The created user with assigned ID
        
    Raises:
        400: Invalid user data
        409: User already exists
    """
    return create_new_user(user)
```

### Custom OpenAPI Metadata

```python
# Define tags for better organization
tags_metadata = [
    {
        "name": "users",
        "description": "Operations with users"
    },
    {
        "name": "auth", 
        "description": "Authentication and authorization"
    },
]

app = Velithon(
    title="My API",
    description="A comprehensive API built with Velithon",
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "API Support",
        "url": "https://example.com/contact",
        "email": "support@example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)
```

## Request/Response Documentation

### Parameter Documentation

```python
from typing import Annotated
from velithon.params import Query, Path, Header, Cookie

@app.get("/users/{user_id}")
async def get_user(
    user_id: Annotated[int, Path(description="The ID of the user to retrieve")],
    include_posts: Annotated[bool, Query(description="Include user's posts in response")] = False,
    api_version: Annotated[str, Header(description="API version")] = "v1",
    session_id: Annotated[str, Cookie(description="Session identifier")] = None
) -> User:
    """
    Get a specific user by ID
    
    Retrieves detailed information about a user.
    """
    return get_user_by_id(user_id, include_posts=include_posts)
```

### Response Documentation

```python
from velithon.responses import OptimizedJSONResponse
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None

class SuccessResponse(BaseModel):
    success: bool
    data: dict

@app.post("/users", response_model=User, status_code=201, tags=["users"])
async def create_user(user: UserCreate) -> User:
    """
    Create a new user with comprehensive error handling
    
    This endpoint creates a new user with the provided information.
    
    Returns:
        User: The created user with assigned ID
        
    Raises:
        400: Invalid input data
        409: User already exists  
        422: Validation error
    """
    try:
        new_user = create_new_user(user)
        # In Velithon, status codes are set in the response, not the decorator
        return OptimizedJSONResponse(new_user.dict(), status_code=201)
    except ValidationError as e:
        return OptimizedJSONResponse(
            ErrorResponse(
                error="validation_error",
                message="Invalid input data",
                details=e.errors()
            ).dict(),
            status_code=422
        )
    except UserExistsError as e:
        return OptimizedJSONResponse(
            ErrorResponse(
                error="user_exists",
                message=str(e)
            ).dict(),
            status_code=409
        )
```

## Security Documentation

### Authentication Schemes

```python
from velithon.security import HTTPBearer, APIKeyHeader, OAuth2PasswordBearer
from velithon.di import inject, Provide

# JWT Bearer token
bearer_auth = HTTPBearer(
    scheme_name="JWT",
    description="JWT token authentication"
)

# API Key in header
api_key_auth = APIKeyHeader(
    name="X-API-Key",
    scheme_name="API Key",
    description="API key authentication"
)

# OAuth2 Password flow
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scheme_name="OAuth2",
    description="OAuth2 password flow"
)

@app.get("/protected")
@inject
async def protected_endpoint(auth: Provide[HTTPBearer] = bearer_auth):
    """Protected endpoint requiring JWT authentication"""
    return {"message": "This is a protected endpoint"}

@app.get("/api-data")
@inject
async def api_data(api_key: Provide[APIKeyHeader] = api_key_auth):
    """API endpoint requiring API key"""
    return {"data": "sensitive information"}
```

### Security Requirements

```python
from velithon.security import Security
from velithon.di import inject, Provide

@app.get("/admin/users")
@inject
async def admin_users(auth: Provide[Security] = Security(bearer_auth, scopes=["admin"])):
    """
    Admin-only endpoint
    
    Requires JWT authentication with admin scope.
    """
    return get_all_users_admin()
```

## Custom Documentation

### Custom OpenAPI Schema

```python
# Note: Velithon uses automatic OpenAPI generation through its built-in swagger_generate function
# Custom schema modification is available through the application configuration

def custom_openapi_config():
    """Configure custom OpenAPI settings"""
    app.title = "Custom API"
    app.version = "2.0.0" 
    app.description = "This is a custom OpenAPI schema"
    
    # Custom logo and branding can be set through Swagger UI parameters
    app.docs_url = "/docs"
    app.redoc_url = None  # Velithon primarily supports Swagger UI
    
    return app

# Apply custom configuration
custom_openapi_config()
```

### Custom Documentation Pages

```python
from velithon.responses import HTMLResponse

@app.get("/docs/custom", include_in_schema=False)
async def custom_docs():
    """Custom documentation page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Custom API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
            .method { color: #fff; padding: 5px 10px; border-radius: 3px; }
            .get { background-color: #61affe; }
            .post { background-color: #49cc90; }
            .put { background-color: #fca130; }
            .delete { background-color: #f93e3e; }
        </style>
    </head>
    <body>
        <h1>API Documentation</h1>
        <div class="endpoint">
            <span class="method get">GET</span>
            <strong>/users</strong>
            <p>Get all users in the system</p>
        </div>
        <div class="endpoint">
            <span class="method post">POST</span>
            <strong>/users</strong>
            <p>Create a new user</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html_content)
```

## Export Documentation

### Export to Files

```python
import json
from pathlib import Path

@app.get("/export/openapi.json", include_in_schema=False)
async def export_openapi_json():
    """Export OpenAPI schema as JSON"""
    # Note: Access to OpenAPI schema in Velithon is handled internally
    # You can access the generated documentation at /docs or create custom endpoints
    return OptimizedJSONResponse({"message": "Use /docs for Swagger UI documentation"})

# File export functionality would need to be implemented using
# Velithon's internal documentation generation system
def export_docs():
    """Export documentation to files"""
    print("Documentation is available at the /docs endpoint")
    print("For programmatic access, implement custom endpoints")

if __name__ == "__main__":
    export_docs()
```

### CLI Documentation Access

```bash
# Access OpenAPI documentation through the web interface
# Start your Velithon application and visit:
# http://localhost:8000/docs for Swagger UI

# For custom documentation endpoints, implement them in your application:
curl http://localhost:8000/docs  # Swagger UI
```

## Swagger UI Customization

### Custom Swagger UI

```python
from velithon.openapi.ui import get_swagger_ui_html

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui.css"
    )
```

### Documentation Access

```python
# Velithon primarily supports Swagger UI for API documentation
# ReDoc support would need to be implemented as a custom endpoint

@app.get("/redoc", include_in_schema=False)
async def redoc_docs():
    """Custom ReDoc implementation (not built-in)"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Documentation - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <redoc spec-url="/openapi.json"></redoc>
        <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(html_content)
```

## Documentation Testing

### Testing Documentation Generation

```python
import pytest
import httpx

@pytest.mark.asyncio
async def test_openapi_schema():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/docs")  # Test Swagger UI availability
        assert response.status_code == 200
        
        # Note: Direct OpenAPI JSON access may need custom implementation
        # The schema is generated internally by Velithon

def test_swagger_ui():
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text
```

### Schema Validation

```python
# Note: Velithon doesn't have a built-in TestClient
# Use httpx or similar HTTP client libraries for testing

import pytest
import httpx

@pytest.mark.asyncio
async def test_swagger_ui_availability():
    """Test that the Swagger UI documentation is accessible"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()

@pytest.mark.asyncio
async def test_documentation_endpoints():
    """Test that documentation endpoints are working"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test main docs endpoint
        docs_response = await client.get("/docs")
        assert docs_response.status_code == 200
```

## Best Practices

### Documentation Standards

1. **Comprehensive Descriptions**: Always provide clear descriptions for endpoints, parameters, and responses
2. **Type Hints**: Use proper type hints for automatic schema generation
3. **Examples**: Include examples in your Pydantic models
4. **Error Documentation**: Document all possible error responses
5. **Security Documentation**: Clearly document authentication requirements

### Example with All Best Practices

```python
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse

class UserBase(BaseModel):
    """Base user model with common fields"""
    name: str = Field(..., description="User's full name", min_length=1, max_length=100)
    email: EmailStr = Field(..., description="User's email address")
    age: Optional[int] = Field(None, description="User's age", ge=0, le=150)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30
            }
        }

class User(UserBase):
    """Complete user model including ID"""
    id: int = Field(..., description="Unique user identifier")
    created_at: str = Field(..., description="User creation timestamp")

class UserCreate(UserBase):
    """Model for creating a new user"""
    password: str = Field(..., description="User password", min_length=8)

@app.post(
    "/users",
    response_model=User,
    tags=["users"],
    summary="Create a new user"
)
async def create_user(user: UserCreate) -> User:
    """
    Create a new user in the system
    
    This endpoint creates a new user with the provided information.
    The password will be hashed before storage.
    
    - **name**: Required. User's full name (1-100 characters)
    - **email**: Required. Valid email address
    - **age**: Optional. Age between 0 and 150
    - **password**: Required. Password (minimum 8 characters)
    
    Returns the created user with assigned ID and creation timestamp.
    """
    return create_new_user(user)
```

## Next Steps

- [Swagger UI Configuration →](swagger-ui.md)
- [Custom Documentation →](custom.md)
- [Export Documentation →](export.md)
