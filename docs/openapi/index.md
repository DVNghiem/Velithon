# OpenAPI & Documentation

Velithon provides automatic OpenAPI documentation generation with customizable Swagger UI integration.

## Overview

Velithon automatically generates OpenAPI 3.0 documentation based on your route definitions, type hints, and docstrings. The documentation is available through multiple formats including Swagger UI, ReDoc, and JSON/YAML export.

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

@app.post("/users", response_model=User, tags=["users"], status_code=201)
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
from velithon.openapi import OpenAPIMetadata, Tag, ExternalDocs

# Define tags for better organization
tags_metadata = [
    Tag(
        name="users",
        description="Operations with users",
        external_docs=ExternalDocs(
            description="User management guide",
            url="https://docs.example.com/users"
        )
    ),
    Tag(
        name="auth",
        description="Authentication and authorization",
    ),
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
    },
    servers=[
        {"url": "https://api.example.com", "description": "Production server"},
        {"url": "https://staging-api.example.com", "description": "Staging server"},
        {"url": "http://localhost:8000", "description": "Development server"}
    ]
)
```

## Request/Response Documentation

### Parameter Documentation

```python
from typing import Annotated
from velithon.params import Query, Path, Header, Cookie

@app.get("/users/{user_id}")
async def get_user(
    user_id: Annotated[int, Path(description="The ID of the user to retrieve", gt=0)],
    include_posts: Annotated[bool, Query(description="Include user's posts in response")] = False,
    api_version: Annotated[str, Header(description="API version", alias="X-API-Version")] = "v1",
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

@app.post("/users", responses={
    201: {"model": User, "description": "User created successfully"},
    400: {"model": ErrorResponse, "description": "Invalid input data"},
    409: {"model": ErrorResponse, "description": "User already exists"},
    422: {"model": ErrorResponse, "description": "Validation error"}
})
async def create_user(user: UserCreate) -> User:
    """Create a new user with comprehensive error handling"""
    try:
        return create_new_user(user)
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

@app.get("/protected", dependencies=[Depends(bearer_auth)])
async def protected_endpoint():
    """Protected endpoint requiring JWT authentication"""
    return {"message": "This is a protected endpoint"}

@app.get("/api-data", dependencies=[Depends(api_key_auth)])
async def api_data():
    """API endpoint requiring API key"""
    return {"data": "sensitive information"}
```

### Security Requirements

```python
from velithon.dependencies import Security

@app.get("/admin/users", 
         dependencies=[Security(bearer_auth, scopes=["admin"])])
async def admin_users():
    """
    Admin-only endpoint
    
    Requires JWT authentication with admin scope.
    """
    return get_all_users_admin()
```

## Custom Documentation

### Custom OpenAPI Schema

```python
from velithon.openapi import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Custom API",
        version="2.0.0",
        description="This is a custom OpenAPI schema",
        routes=app.routes,
    )
    
    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    # Add custom paths
    openapi_schema["paths"]["/health"] = {
        "get": {
            "summary": "Health Check",
            "responses": {
                "200": {
                    "description": "Service is healthy",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "timestamp": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
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
import yaml
from pathlib import Path

@app.get("/export/openapi.json", include_in_schema=False)
async def export_openapi_json():
    """Export OpenAPI schema as JSON"""
    schema = app.openapi()
    return OptimizedJSONResponse(schema)

@app.get("/export/openapi.yaml", include_in_schema=False)
async def export_openapi_yaml():
    """Export OpenAPI schema as YAML"""
    schema = app.openapi()
    yaml_content = yaml.dump(schema, default_flow_style=False)
    return Response(yaml_content, media_type="application/x-yaml")

# Command-line export
def export_docs():
    """Export documentation to files"""
    schema = app.openapi()
    
    # Export JSON
    with open("openapi.json", "w") as f:
        json.dump(schema, f, indent=2)
    
    # Export YAML
    with open("openapi.yaml", "w") as f:
        yaml.dump(schema, f, default_flow_style=False)
    
    print("Documentation exported successfully!")

if __name__ == "__main__":
    export_docs()
```

### CLI Export

```bash
# Export OpenAPI documentation
velithon export-docs --app myapp:app --format json --output docs/
velithon export-docs --app myapp:app --format yaml --output docs/
velithon export-docs --app myapp:app --format html --output docs/
```

## Swagger UI Customization

### Custom Swagger UI

```python
from velithon.openapi.docs import get_swagger_ui_html

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui.css",
        swagger_ui_parameters={
            "deepLinking": True,
            "defaultModelsExpandDepth": 2,
            "defaultModelExpandDepth": 2,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True
        }
    )
```

### ReDoc Customization

```python
from velithon.openapi.docs import get_redoc_html

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
        redoc_favicon_url="https://example.com/favicon.ico"
    )
```

## Documentation Testing

### Testing Documentation Generation

```python
import pytest
from velithon.testing import TestClient

def test_openapi_schema():
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    assert schema["info"]["title"] == "My API"
    assert schema["info"]["version"] == "1.0.0"
    assert "/users" in schema["paths"]

def test_swagger_ui():
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text

def test_redoc():
    client = TestClient(app)
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text
```

### Schema Validation

```python
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename

def test_openapi_spec_validity():
    """Test that the generated OpenAPI spec is valid"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    spec = response.json()
    
    # This will raise an exception if the spec is invalid
    validate_spec(spec)

def test_exported_spec_validity():
    """Test that exported OpenAPI files are valid"""
    # Export the spec
    export_docs()
    
    # Validate exported JSON
    spec = read_from_filename("openapi.json")
    validate_spec(spec)
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
    status_code=201,
    tags=["users"],
    summary="Create a new user",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data"},
        409: {"description": "User already exists"}
    }
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
