# Automatic Documentation

Velithon automatically generates OpenAPI documentation based on your route definitions and type hints.

## Overview

Velithon uses Python type hints and docstrings to automatically generate comprehensive OpenAPI documentation without requiring additional configuration.

## Basic Setup

```python
from velithon import Velithon
from typing import List, Optional
from pydantic import BaseModel

app = Velithon(
    title="My API",
    description="A sample API built with Velithon",
    version="1.0.0"
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
```

## Route Documentation

```python
@app.get("/users", response_model=List[User])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
):
    """
    Get a list of users.
    
    Parameters:
    - skip: Number of users to skip
    - limit: Maximum number of users to return
    - search: Optional search term to filter users
    
    Returns:
    - List of users matching the criteria
    """
    # Implementation here
    return []

@app.post("/users", response_model=User)
async def create_user(user: UserCreate):
    """
    Create a new user.
    
    Parameters:
    - user: User data for creation
    
    Returns:
    - Created user with assigned ID
    """
    # Implementation here
    return User(id=1, **user.dict())

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """
    Get a specific user by ID.
    
    Parameters:
    - user_id: The ID of the user to retrieve
    
    Returns:
    - User information
    
    Raises:
    - 404: User not found
    """
    # Implementation here
    return User(id=user_id, name="John Doe", email="john@example.com")
```

## Response Documentation

```python
from velithon import JSONResponse

@app.get("/users/{user_id}/status")
async def get_user_status(user_id: int):
    """
    Get user status information.
    
    Returns different response formats based on user state.
    """
    if user_id == 1:
        return JSONResponse(
            {"status": "active", "last_login": "2025-01-01"},
            status_code=200
        )
    elif user_id == 2:
        return JSONResponse(
            {"status": "inactive", "reason": "account_suspended"},
            status_code=200
        )
    else:
        return JSONResponse(
            {"error": "User not found"},
            status_code=404
        )
```

## Tags and Grouping

```python
# Group related endpoints with tags
@app.get("/users", tags=["users"])
async def get_users():
    """Get all users"""
    pass

@app.post("/users", tags=["users"])
async def create_user(user: UserCreate):
    """Create a new user"""
    pass

@app.get("/posts", tags=["posts"])
async def get_posts():
    """Get all posts"""
    pass

# Configure tag metadata
app.openapi_tags = [
    {
        "name": "users",
        "description": "User management operations",
    },
    {
        "name": "posts",
        "description": "Blog post operations",
    }
]
```

## Security Documentation

```python
from velithon.security import HTTPBearer, HTTPBasic

security = HTTPBearer()

@app.get("/protected", dependencies=[security])
async def protected_endpoint():
    """
    Protected endpoint requiring bearer token authentication.
    
    Security:
    - Bearer token required in Authorization header
    """
    return {"message": "Access granted"}

# Document security schemes
app.openapi_security_schemes = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    },
    "basicAuth": {
        "type": "http",
        "scheme": "basic"
    }
}
```

## Custom Response Models

```python
from pydantic import BaseModel, Field
from typing import Union

class SuccessResponse(BaseModel):
    status: str = Field(example="success")
    message: str = Field(example="Operation completed successfully")
    data: dict = Field(default={})

class ErrorResponse(BaseModel):
    status: str = Field(example="error")
    message: str = Field(example="An error occurred")
    error_code: str = Field(example="VALIDATION_ERROR")

@app.post("/process", response_model=Union[SuccessResponse, ErrorResponse])
async def process_data(data: dict):
    """
    Process submitted data.
    
    Returns either success or error response based on processing result.
    """
    try:
        # Process data
        return SuccessResponse(
            message="Data processed successfully",
            data={"processed_items": len(data)}
        )
    except Exception as e:
        return ErrorResponse(
            message=str(e),
            error_code="PROCESSING_ERROR"
        )
```

## Accessing Documentation

```python
# Documentation endpoints are automatically available:
# GET /docs - Swagger UI
# GET /redoc - ReDoc UI  
# GET /openapi.json - OpenAPI JSON schema

@app.get("/")
async def root():
    return {
        "message": "Welcome to the API",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        }
    }
```

## Configuration Options

```python
app = Velithon(
    title="My API",
    description="API built with Velithon framework",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",  # Custom OpenAPI URL
    docs_url="/documentation",           # Custom Swagger UI URL
    redoc_url="/redoc-ui"               # Custom ReDoc URL
)
```

## Best Practices

1. **Use descriptive docstrings** for all endpoints
2. **Define proper response models** with Pydantic
3. **Include parameter descriptions** in docstrings
4. **Use meaningful tags** to organize endpoints
5. **Document error responses** and status codes
6. **Provide example values** in model fields
7. **Keep security documentation** up to date
