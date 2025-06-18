# Router Path Parameter Feature

## Overview

The Velithon framework now supports router path parameters, allowing you to create routers with path prefixes and easily organize your API endpoints in a hierarchical manner.

## Features

### 1. Router with Path Parameter

You can now create a router with a path prefix:

```python
from velithon.routing import Router

# Create a router with a path prefix
orders_router = Router(path="/orders")

# All routes added to this router will be prefixed with "/orders"
orders_router.add_api_route("/", get_orders, methods=["GET"])  # -> /orders/
orders_router.add_api_route("/{order_id}", get_order, methods=["GET"])  # -> /orders/{order_id}
```

### 2. Adding Routers to Application

The Velithon application now supports adding routers with two new methods:

#### `app.add_router()`

```python
from velithon import Velithon
from velithon.routing import Router

app = Velithon()

# Router with existing path prefix
orders_router = Router(path="/orders")
orders_router.add_api_route("/", get_orders, methods=["GET"])

# Add router to application (uses existing prefix)
app.add_router(orders_router)
# Result: GET /orders/
```

#### `app.include_router()` 

```python
# Router without path prefix
users_router = Router()
users_router.add_api_route("/", get_users, methods=["GET"])

# Include router with additional prefix
app.include_router(users_router, prefix="/users")
# Result: GET /users/
```

### 3. Router with Additional Prefix

You can add additional prefixes when including routers:

```python
# Router with existing prefix
api_router = Router(path="/api")
api_router.add_api_route("/health", health_check, methods=["GET"])

# Add with additional prefix
app.include_router(api_router, prefix="/v1")
# Result: GET /v1/api/health
```

### 4. Nested Routers

Routers can contain other routers, enabling complex hierarchical structures:

```python
# Create nested structure
products_router = Router(path="/products")
products_router.add_api_route("/", get_products, methods=["GET"])

shop_router = Router(path="/shop")
shop_router.add_router(products_router)

app.add_router(shop_router)
# Result: GET /shop/products/
```

## Complete Example

```python
from velithon import Velithon
from velithon.routing import Router
from velithon.responses import JSONResponse

# Create handlers
def get_orders():
    return JSONResponse({"orders": []})

def get_users():
    return JSONResponse({"users": []})

# Create routers
orders_router = Router(path="/orders")
orders_router.add_api_route("/", get_orders, methods=["GET"])

users_router = Router()
users_router.add_api_route("/", get_users, methods=["GET"])

# Create application
app = Velithon()

# Add routers
app.add_router(orders_router)  # -> GET /orders/
app.include_router(users_router, prefix="/users")  # -> GET /users/

if __name__ == "__main__":
    # Available endpoints:
    # GET /orders/ - Get orders
    # GET /users/  - Get users
    # GET /docs    - API documentation
    pass
```

## API Reference

### Router Class

```python
class Router:
    def __init__(
        self,
        routes: Sequence[BaseRoute] | None = None,
        *,
        path: str = "",  # NEW: Path prefix for all routes
        redirect_slashes: bool = True,
        default: RSGIApp | None = None,
        on_startup: Sequence[Callable[[], Any]] | None = None,
        on_shutdown: Sequence[Callable[[], Any]] | None = None,
        middleware: Sequence[Middleware] | None = None,
        route_class: type[BaseRoute] = Route,
    )
```

**Parameters:**
- `path`: Path prefix to add to all routes in this router
- All other parameters remain the same

### Router Methods

#### `add_router()`

```python
def add_router(
    self,
    router: Router,
    *,
    prefix: str = "",
    tags: Sequence[str] | None = None,
    dependencies: Sequence[Any] | None = None,
) -> None
```

Add a sub-router to this router.

**Parameters:**
- `router`: The Router instance to add
- `prefix`: Additional path prefix to add to all routes
- `tags`: Tags to add to all routes in the router
- `dependencies`: Dependencies to add to all routes

### Velithon Application Methods

#### `add_router()`

```python
def add_router(
    self,
    router: Router,
    *,
    prefix: str = "",
    tags: Sequence[str] | None = None,
    dependencies: Sequence[Any] | None = None,
) -> None
```

Add a router to the application.

#### `include_router()`

```python
def include_router(
    self,
    router: Router,
    *,
    prefix: str = "",
    tags: Sequence[str] | None = None,
    dependencies: Sequence[Any] | None = None,
) -> None
```

Include a router in the application (alias for `add_router`).

## Benefits

1. **Better Organization**: Group related routes using router prefixes
2. **Modular Design**: Create reusable router modules
3. **API Versioning**: Easy to implement versioned APIs
4. **Hierarchical Structure**: Support complex nested routing patterns
5. **FastAPI Compatibility**: Similar API to FastAPI's router system

## Migration Notes

This feature is fully backward compatible. Existing code will continue to work without any changes. The `path` parameter is optional and defaults to an empty string.
