# OpenAPI Documentation

## Automatic Documentation

Velithon automatically generates OpenAPI documentation:

```python
app = Velithon(
    title="My API",
    description="A comprehensive API built with Velithon",
    version="1.0.0",
    openapi_url="/openapi.json",  # OpenAPI schema endpoint
    docs_url="/docs"  # Swagger UI endpoint
)
```

## Adding Metadata to Routes

```python
@app.get(
    "/users/{user_id}",
    summary="Get user by ID",
    description="Retrieve a specific user by their unique identifier",
    tags=["users"]
)
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id})

# For class-based endpoints
class UserEndpoint(HTTPEndpoint):
    async def get(self, user_id: int):
        """
        Get user by ID
        
        Retrieve a specific user by their unique identifier.
        """
        return JSONResponse({"user_id": user_id})

app.add_route(
    "/users/{user_id}",
    UserEndpoint,
    methods=["GET"],
    summary="Get user by ID",
    description="Retrieve a specific user by their unique identifier",
    tags=["users"]
)
```

## Response Models

Use Pydantic models for response documentation:

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

class UserResponse(BaseModel):
    user: User
    message: str

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    return JSONResponse({
        "user": {"id": user_id, "name": "John", "email": "john@example.com"},
        "message": "User retrieved successfully"
    })
```
