# Routing

Velithon provides a powerful and flexible routing system that supports various patterns for organizing your API endpoints. This guide covers all routing capabilities including path parameters, decorators, routers, and advanced features.

## Route Decorators

The simplest way to define routes is using HTTP method decorators:

```python
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/users")
async def get_users():
    return JSONResponse({"users": []})

@app.post("/users")
async def create_user():
    return JSONResponse({"message": "User created"})

@app.put("/users/{user_id}")
async def update_user(user_id: int):
    return JSONResponse({"user_id": user_id, "message": "Updated"})

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    return JSONResponse({"message": "User deleted"})

@app.patch("/users/{user_id}")
async def patch_user(user_id: int):
    return JSONResponse({"user_id": user_id, "message": "Patched"})

@app.options("/users")
async def options_users():
    return PlainTextResponse("", headers={"Allow": "GET, POST, PUT, DELETE, PATCH, OPTIONS"})

@app.head("/users")
async def head_users():
    return JSONResponse({})
```

### Decorator Parameters

All HTTP method decorators support the following parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | URL path pattern (required) |
| `tags` | `List[str]` | Tags for OpenAPI documentation |
| `summary` | `str` | Summary for OpenAPI documentation |
| `description` | `str` | Description for OpenAPI documentation |
| `name` | `str` | Name for the route |
| `include_in_schema` | `bool` | Whether to include in OpenAPI schema (default: `True`) |
| `response_model` | `type` | Response model for validation and documentation |

Example with parameters:

```python
@app.get(
    "/users",
    tags=["users"],
    summary="List all users",
    description="Get a list of all users in the system",
    name="get_users",
    include_in_schema=True,
)
async def get_users():
    return JSONResponse({"users": []})
```

## Path Parameters

Define path parameters with type hints for automatic conversion and validation:

### Basic Path Parameters

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id, "type": type(user_id).__name__})

@app.get("/posts/{post_id}")
async def get_post(post_id: str):
    return JSONResponse({"post_id": post_id})

@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: int, post_id: str):
    return JSONResponse({"user_id": user_id, "post_id": post_id})
```

### Path Parameter Types

Velithon supports various path parameter types:

```python
# String (default)
@app.get("/items/{item_name}")
async def get_item(item_name: str):
    return JSONResponse({"item": item_name})

# Integer
@app.get("/items/{item_id}")
async def get_item_by_id(item_id: int):
    return JSONResponse({"item_id": item_id})

# Float
@app.get("/prices/{price}")
async def get_price(price: float):
    return JSONResponse({"price": price})

# UUID
from uuid import UUID

@app.get("/objects/{obj_id}")
async def get_object(obj_id: UUID):
    return JSONResponse({"object_id": str(obj_id)})

# Path (captures remaining path)
@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    return JSONResponse({"file_path": file_path})
```

### Path Parameter Validation

Use parameter annotations for validation:

```python
from typing import Annotated
from velithon.params import Path

@app.get("/users/{user_id}")
async def get_user(
    user_id: Annotated[int, Path(description="User ID", ge=1)]
):
    return JSONResponse({"user_id": user_id})

@app.get("/items/{item_code}")
async def get_item(
    item_code: Annotated[str, Path(description="Item code", min_length=3, max_length=10)]
):
    return JSONResponse({"item_code": item_code})
```

## Programmatic Route Registration

You can add routes programmatically using the `add_route` and `add_api_route` methods:

### Basic Route Registration

```python
from velithon.routing import Router
from velithon.requests import Request

async def user_handler(request: Request):
    return JSONResponse({"method": request.method, "path": request.url.path})

# Add to router
router = Router()
router.add_route("/users", user_handler, methods=["GET", "POST"])

# Add to application
app = Velithon()
app.add_route("/users", user_handler, methods=["GET", "POST"])
```

### API Route Registration

```python
async def get_users():
    return JSONResponse({"users": []})

async def create_user():
    return JSONResponse({"message": "User created"})

# Add API routes with automatic parameter parsing
app.add_api_route("/users", get_users, methods=["GET"])
app.add_api_route("/users", create_user, methods=["POST"])
```

## Router System

Velithon's router system allows you to organize routes into logical groups and create modular applications.

### Creating Routers

```python
from velithon.routing import Router

# Create a router
users_router = Router()

@users_router.get("/")
async def get_users():
    return JSONResponse({"users": []})

@users_router.get("/{user_id}")
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id})

@users_router.post("/")
async def create_user():
    return JSONResponse({"message": "User created"})
```

### Router with Path Prefix

```python
# Router with automatic path prefix
orders_router = Router(path="/orders")

@orders_router.get("/")  # Will be /orders/
async def get_orders():
    return JSONResponse({"orders": []})

@orders_router.get("/{order_id}")  # Will be /orders/{order_id}
async def get_order(order_id: int):
    return JSONResponse({"order_id": order_id})
```

### Adding Routers to Application

```python
app = Velithon()

# Method 1: Add router with existing prefix
app.add_router(orders_router)  # Uses /orders prefix

# Method 2: Add router with additional prefix
app.include_router(users_router, prefix="/users")  # Adds /users prefix

# Method 3: Add router without prefix
app.add_router(users_router)  # No prefix added
```

### Nested Routers

Create complex hierarchical routing structures:

```python
# Create sub-routers
products_router = Router(path="/products")
products_router.add_api_route("/", get_products, methods=["GET"])
products_router.add_api_route("/{product_id}", get_product, methods=["GET"])

categories_router = Router(path="/categories")
categories_router.add_api_route("/", get_categories, methods=["GET"])

# Create main shop router
shop_router = Router(path="/shop")
shop_router.add_router(products_router)  # /shop/products/
shop_router.add_router(categories_router)  # /shop/categories/

# Add info endpoint directly to shop router
@shop_router.get("/info")  # /shop/info
async def shop_info():
    return JSONResponse({"shop": "info"})

# Add to main application
app.add_router(shop_router)  # All routes prefixed with /shop
```

### API Versioning with Routers

```python
# Version 1 API
v1_router = Router(path="/v1")

@v1_router.get("/status")
async def v1_status():
    return JSONResponse({"version": "1.0", "status": "active"})

@v1_router.get("/users")
async def v1_users():
    return JSONResponse({"users": [], "version": "1.0"})

# Version 2 API
v2_router = Router(path="/v2")

@v2_router.get("/status")
async def v2_status():
    return JSONResponse({"version": "2.0", "status": "active"})

@v2_router.get("/users")
async def v2_users():
    return JSONResponse({"users": [], "version": "2.0", "features": ["pagination"]})

@v2_router.get("/features")
async def v2_features():
    return JSONResponse({"features": ["pagination", "filtering", "sorting"]})

# Main API router
api_router = Router(path="/api")
api_router.add_router(v1_router)  # /api/v1/*
api_router.add_router(v2_router)  # /api/v2/*

# Add to application
app.add_router(api_router)
```

## Route Matching and Performance

Velithon uses Rust-optimized route matching for high performance:

### Route Optimization

```python
# Simple routes (no parameters) are cached for fastest lookup
@app.get("/health")  # Optimized static route
async def health():
    return JSONResponse({"status": "ok"})

# Parameterized routes use compiled regex with caching
@app.get("/users/{user_id}")  # Optimized with parameter extraction
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id})
```

### Route Priority

Routes are matched in the order they are defined:

```python
# More specific routes should be defined first
@app.get("/users/admin")  # Match /users/admin exactly
async def admin_users():
    return JSONResponse({"admin": True})

@app.get("/users/{user_id}")  # Match /users/{anything_else}
async def get_user(user_id: str):
    return JSONResponse({"user_id": user_id})
```

## WebSocket Routing

Velithon supports WebSocket routing alongside HTTP routes:

```python
from velithon.websocket import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception:
        pass

# WebSocket with path parameters
@app.websocket("/ws/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    await websocket.send_text(f"Connected client: {client_id}")
```

## Route Middleware

Apply middleware to specific routes or routers:

```python
from velithon.middleware.cors import CORSMiddleware

# Middleware on specific router
api_router = Router(
    path="/api",
    middleware=[
        (CORSMiddleware, [], {"allow_origins": ["*"]})
    ]
)

# All routes in this router will have CORS middleware
@api_router.get("/data")
async def get_data():
    return JSONResponse({"data": "value"})
```

## Route Groups and Tags

Organize routes with tags for documentation and grouping:

```python
# Group user-related routes
@app.get("/users", tags=["users"])
async def get_users():
    return JSONResponse({"users": []})

@app.post("/users", tags=["users"])
async def create_user():
    return JSONResponse({"message": "Created"})

# Group admin routes
@app.get("/admin/stats", tags=["admin"])
async def admin_stats():
    return JSONResponse({"stats": {}})
```

## Route Dependencies

Use dependency injection with routes:

```python
from typing import Annotated

def get_current_user():
    return {"user_id": 123, "username": "john"}

@app.get("/profile")
async def get_profile(user: Annotated[dict, get_current_user]):
    return JSONResponse({"profile": user})
```

## Route Names and URL Generation

Assign names to routes for URL generation:

```python
@app.get("/users/{user_id}", name="get_user")
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id})

# Access route by name (useful for URL generation)
# route = app.router.get_route_by_name("get_user")
```

## Error Handling in Routes

Handle route-specific errors:

```python
from velithon.exceptions import HTTPException

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id < 1:
        raise HTTPException(
            status_code=400,
            detail="User ID must be positive"
        )
    
    if user_id > 1000:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return JSONResponse({"user_id": user_id})
```

This comprehensive routing system provides the flexibility to build everything from simple APIs to complex, hierarchical applications with proper organization and high performance.
