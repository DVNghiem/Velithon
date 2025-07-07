# Routing API Reference

The `Router` class provides a way to organize and group related routes with common prefixes, middleware, and configuration.

## Class: Router

```python
from velithon.routing import Router

router = Router()
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `routes` | `Sequence[BaseRoute] \| None` | `None` | Initial routes to register |
| `on_startup` | `Sequence[Callable] \| None` | `None` | Startup callbacks |
| `on_shutdown` | `Sequence[Callable] \| None` | `None` | Shutdown callbacks |
| `validation_error_formatter` | `ValidationErrorFormatter \| None` | `None` | Custom validation error formatter for routes in this router |

**Example:**
```python
from velithon.routing import Router
from velithon.exceptions import SimpleValidationErrorFormatter

router = Router(
    validation_error_formatter=SimpleValidationErrorFormatter()
)
```

## HTTP Method Decorators

### GET

```python
@router.get(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define a GET route.

**Example:**
```python
@router.get("/users", tags=["Users"])
async def list_users():
    return {"users": []}
```

### POST

```python
@router.post(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define a POST route.

**Example:**
```python
@router.post("/users", validation_error_formatter=DetailedValidationErrorFormatter())
async def create_user(user: UserModel):
    return {"user": user.dict()}
```

### PUT

```python
@router.put(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define a PUT route.

### PATCH

```python
@router.patch(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define a PATCH route.

### DELETE

```python
@router.delete(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define a DELETE route.

### HEAD

```python
@router.head(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define a HEAD route.

### OPTIONS

```python
@router.options(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> Callable
```

Define an OPTIONS route.

## Methods

### add_route()

```python
def add_route(
    route: BaseRoute,
    *,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> None
```

Add a route to the router.

**Example:**
```python
from velithon.routing import Route

custom_route = Route(
    path="/custom",
    endpoint=my_endpoint,
    methods=["GET"]
)

router.add_route(custom_route)
```

### add_api_route()

```python
def add_api_route(
    path: str,
    endpoint: Callable,
    *,
    methods: list[str] | None = None,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None,
    validation_error_formatter: ValidationErrorFormatter | None = None
) -> None
```

Add an API route programmatically.

**Example:**
```python
async def my_endpoint():
    return {"message": "Hello World"}

router.add_api_route(
    "/hello",
    my_endpoint,
    methods=["GET"],
    tags=["Greetings"],
    validation_error_formatter=SimpleValidationErrorFormatter()
)
```

### include_router()

```python
def include_router(
    router: Router,
    *,
    prefix: str = "",
    tags: Sequence[str] | None = None
) -> None
```

Include another router with optional prefix and tags.

**Example:**
```python
api_router = Router()
auth_router = Router()

@auth_router.post("/login")
async def login():
    return {"token": "..."}

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
```

## Validation Error Formatter Hierarchy

The Router class supports a hierarchical validation error formatter system:

1. **Route-level formatter** (highest priority) - specified in individual route decorators
2. **Router-level formatter** - specified in the Router constructor
3. **Application-level formatter** - specified in the Velithon constructor

**Example:**
```python
from velithon import Velithon
from velithon.routing import Router
from velithon.exceptions import (
    DefaultValidationErrorFormatter,
    SimpleValidationErrorFormatter,
    DetailedValidationErrorFormatter
)

# Application-level formatter
app = Velithon(validation_error_formatter=DefaultValidationErrorFormatter())

# Router-level formatter (overrides app-level)
api_router = Router(validation_error_formatter=SimpleValidationErrorFormatter())

@api_router.post("/users")
async def create_user(user: UserModel):
    # Uses SimpleValidationErrorFormatter from router
    return {"user": user.dict()}

# Route-level formatter (overrides router-level)
@api_router.get("/users/{user_id}", 
                validation_error_formatter=DetailedValidationErrorFormatter())
async def get_user(user_id: int):
    # Uses DetailedValidationErrorFormatter for this route only
    return {"user_id": user_id}

app.include_router(api_router, prefix="/api")
```

## Usage Examples

### Basic Router Usage

```python
from velithon import Velithon
from velithon.routing import Router

app = Velithon()
api_router = Router()

@api_router.get("/users")
async def list_users():
    return {"users": []}

@api_router.post("/users")
async def create_user(user: dict):
    return {"user": user}

app.include_router(api_router, prefix="/api/v1")
```

### Router with Custom Validation Formatter

```python
from velithon.routing import Router
from velithon.exceptions import DetailedValidationErrorFormatter
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

# All routes in this router will use DetailedValidationErrorFormatter
user_router = Router(validation_error_formatter=DetailedValidationErrorFormatter())

@user_router.post("/")
async def create_user(user: User):
    return {"user": user.dict()}

@user_router.put("/{user_id}")
async def update_user(user_id: int, user: User):
    return {"user_id": user_id, "user": user.dict()}
```

### Multiple Routers with Different Formatters

```python
from velithon import Velithon
from velithon.routing import Router
from velithon.exceptions import SimpleValidationErrorFormatter, DetailedValidationErrorFormatter

app = Velithon()

# Public API with simple error messages
public_router = Router(validation_error_formatter=SimpleValidationErrorFormatter())

@public_router.post("/contact")
async def contact(message: str):
    return {"status": "received"}

# Admin API with detailed error messages
admin_router = Router(validation_error_formatter=DetailedValidationErrorFormatter())

@admin_router.post("/users")
async def create_user(user: UserModel):
    return {"user": user.dict()}

app.include_router(public_router, prefix="/public")
app.include_router(admin_router, prefix="/admin")
```
