# Application API Reference

The `Velithon` class is the main application instance that handles routing, middleware, dependency injection, and server lifecycle management.

## Class: Velithon

```python
from velithon import Velithon

app = Velithon(
    title="My API",
    description="API built with Velithon",
    version="1.0.0"
)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `routes` | `Sequence[BaseRoute] \| None` | `None` | Initial routes to register |
| `middleware` | `Sequence[Middleware] \| None` | `None` | Middleware stack |
| `on_startup` | `Sequence[Callable] \| None` | `None` | Startup callbacks |
| `on_shutdown` | `Sequence[Callable] \| None` | `None` | Shutdown callbacks |
| `title` | `str` | `"Velithon"` | API title for documentation |
| `summary` | `str \| None` | `None` | Short API summary |
| `description` | `str` | `""` | API description (supports Markdown) |
| `version` | `str` | `"1.0.0"` | API version |
| `openapi_version` | `str` | `"3.0.0"` | OpenAPI specification version |
| `openapi_url` | `str \| None` | `"/openapi.json"` | OpenAPI schema URL |
| `docs_url` | `str \| None` | `"/docs"` | Swagger UI documentation URL |
| `swagger_ui_oauth2_redirect_url` | `str \| None` | `None` | OAuth2 redirect URL for Swagger UI |
| `swagger_ui_init_oauth` | `dict \| None` | `None` | OAuth2 configuration for Swagger UI |
| `servers` | `list[dict] \| None` | `None` | Server information for OpenAPI |
| `tags` | `Sequence[dict] \| None` | `None` | Tag metadata for OpenAPI |
| `openapi_tags` | `Sequence[dict] \| None` | `None` | OpenAPI tag configuration |
| `terms_of_service` | `str \| None` | `None` | Terms of service URL |
| `contact` | `dict \| None` | `None` | Contact information |
| `license_info` | `dict \| None` | `None` | License information |
| `include_security_middleware` | `bool` | `False` | Enable default security middleware |

## HTTP Method Decorators

### GET

```python
@app.get(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define a GET endpoint.

**Example:**
```python
@app.get("/users", tags=["Users"], summary="List all users")
async def list_users():
    return {"users": []}
```

### POST

```python
@app.post(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define a POST endpoint.

**Example:**
```python
@app.post("/users", tags=["Users"], summary="Create a new user")
async def create_user(request: Request):
    user_data = await request.json()
    return {"user": user_data}
```

### PUT

```python
@app.put(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define a PUT endpoint.

### PATCH

```python
@app.patch(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define a PATCH endpoint.

### DELETE

```python
@app.delete(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define a DELETE endpoint.

### HEAD

```python
@app.head(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define a HEAD endpoint.

### OPTIONS

```python
@app.options(
    path: str,
    *,
    tags: Sequence[str] | None = None,
    summary: str | None = None,
    description: str | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    response_model: type | None = None
) -> Callable
```

Define an OPTIONS endpoint.

## WebSocket Support

### websocket()

```python
@app.websocket(
    path: str,
    *,
    name: str | None = None
) -> Callable
```

Define a WebSocket endpoint.

**Example:**
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

## Route Management

### add_route()

```python
def add_route(
    path: str,
    route: Callable,
    *,
    methods: list[str] | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None
) -> None
```

Manually add a route.

**Example:**
```python
async def user_handler(request: Request):
    return {"method": request.method}

app.add_route("/users", user_handler, methods=["GET", "POST"])
```

### route()

```python
@app.route(
    path: str,
    *,
    methods: list[str] | None = None,
    name: str | None = None,
    include_in_schema: bool = True,
    summary: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None
) -> Callable
```

Generic route decorator for multiple methods.

**Example:**
```python
@app.route("/items/{item_id}", methods=["GET", "PUT", "DELETE"])
async def item_handler(request: Request):
    method = request.method
    item_id = request.path_params["item_id"]
    return {"method": method, "item_id": item_id}
```

### include_router()

```python
def include_router(
    router: Router,
    *,
    prefix: str = "",
    tags: Sequence[str] | None = None,
    dependencies: Sequence[Any] | None = None
) -> None
```

Include a router with optional prefix and tags.

**Example:**
```python
from velithon.routing import Router

api_router = Router()

@api_router.get("/users")
async def list_users():
    return {"users": []}

app.include_router(api_router, prefix="/api/v1", tags=["API"])
```

## Dependency Injection

### register_container()

```python
def register_container(container: ServiceContainer) -> None
```

Register a dependency injection container.

**Example:**
```python
from velithon.di import ServiceContainer

container = ServiceContainer()
container.register("database", "postgresql://localhost/db")
app.register_container(container)
```

## VSP Integration

### register_vsp()

```python
def register_vsp(vsp_manager: VSPManager) -> None
```

Register a VSP (Velithon Service Protocol) manager.

**Example:**
```python
from velithon.vsp import VSPManager

vsp_manager = VSPManager(
    service_name="my-service",
    host="0.0.0.0",
    port=9090
)
app.register_vsp(vsp_manager)
```

## Lifecycle Events

### on_startup()

```python
@app.on_startup(priority: int = 0)
def decorator(func: Callable) -> Callable
```

Register a startup event handler.

**Example:**
```python
@app.on_startup()
async def startup_handler():
    print("Application starting...")
    # Initialize database, cache, etc.
```

### on_shutdown()

```python
@app.on_shutdown(priority: int = 0)
def decorator(func: Callable) -> Callable
```

Register a shutdown event handler.

**Example:**
```python
@app.on_shutdown()
async def shutdown_handler():
    print("Application shutting down...")
    # Cleanup resources
```

## OpenAPI Documentation

### get_openapi()

```python
def get_openapi() -> dict[str, Any]
```

Generate the OpenAPI schema.

**Example:**
```python
openapi_schema = app.get_openapi()
print(openapi_schema)
```

### setup()

```python
def setup() -> None
```

Set up automatic OpenAPI and Swagger UI routes. Called automatically when needed.

## Server Management

### run()

```python
def run(
    host: str = "127.0.0.1",
    port: int = 8000,
    workers: int = 1,
    log_file: str = "velithon.log",
    log_level: str = "INFO",
    log_format: str = "text",
    log_to_file: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 7,
    reload: bool = False,
    blocking_threads: int | None = None,
    blocking_threads_idle_timeout: int = 30,
    runtime_threads: int = 1,
    runtime_blocking_threads: int | None = None,
    runtime_mode: str = "st",
    loop: str = "auto",
    task_impl: str = "asyncio",
    http: str = "auto",
    http1_buffer_size: int | None = None,
    http1_header_read_timeout: int | None = None,
    http1_keep_alive: bool | None = None,
    http1_pipeline_flush: bool | None = None,
    http2_adaptive_window: bool | None = None,
    http2_initial_connection_window_size: int | None = None,
    http2_initial_stream_window_size: int | None = None,
    http2_keep_alive_interval: int | None = None,
    http2_keep_alive_timeout: int | None = None,
    http2_max_concurrent_streams: int | None = None,
    http2_max_frame_size: int | None = None,
    http2_max_headers_size: int | None = None,
    http2_max_send_buffer_size: int | None = None,
    ssl_certificate: str | None = None,
    ssl_keyfile: str | None = None,
    ssl_keyfile_password: str | None = None,
    backpressure: int | None = None,
    vsp_host: str | None = None,
    vsp_port: int | None = None
) -> None
```

Run the application server using Granian (RSGI server).

**Example:**
```python
app.run(
    host="0.0.0.0",
    port=8000,
    workers=4,
    log_level="INFO"
)
```

### Server Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `host` | `str` | Host to bind to |
| `port` | `int` | Port to bind to |
| `workers` | `int` | Number of worker processes |
| `log_level` | `str` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `reload` | `bool` | Enable auto-reload on file changes |
| `runtime_mode` | `str` | Runtime mode (`st` for single-threaded, `mt` for multi-threaded) |
| `loop` | `str` | Event loop (`auto`, `asyncio`, `uvloop`, `rloop`) |
| `http` | `str` | HTTP version (`auto`, `1`, `2`) |
| `ssl_certificate` | `str \| None` | Path to SSL certificate file |
| `ssl_keyfile` | `str \| None` | Path to SSL private key file |

## Middleware Management

### build_middleware_stack()

```python
def build_middleware_stack() -> RSGIApp
```

Build the middleware stack. Called automatically when the application starts.

## Exception Handling

### add_exception_handler()

```python
def add_exception_handler(
    exc_class_or_status_code: type[Exception] | int,
    handler: Callable[[Request, Exception], Response]
) -> None
```

Add a custom exception handler.

**Example:**
```python
async def validation_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        {"error": "Validation failed", "detail": str(exc)},
        status_code=400
    )

app.add_exception_handler(ValueError, validation_exception_handler)
```

## Properties

### router

```python
@property
def router() -> Router
```

Access the application's router instance.

### middleware_stack

```python
@property
def middleware_stack() -> RSGIApp | None
```

Access the built middleware stack.

### container

```python
@property
def container() -> ServiceContainer | None
```

Access the registered dependency injection container.

## RSGI Protocol Methods

### \_\_call\_\_()

```python
async def __call__(scope: Scope, protocol: Protocol) -> None
```

RSGI application callable. Handles incoming requests through the RSGI protocol.

### \_\_rsgi_init\_\_()

```python
def __rsgi_init__(loop: asyncio.AbstractEventLoop) -> None
```

Called when the RSGI server initializes.

### \_\_rsgi_del\_\_()

```python
def __rsgi_del__(loop: asyncio.AbstractEventLoop) -> None
```

Called when the RSGI server shuts down.

## Complete Example

```python
from velithon import Velithon
from velithon.middleware import CORSMiddleware, LoggingMiddleware, Middleware
from velithon.responses import JSONResponse
from velithon.di import ServiceContainer

# Create application with configuration
app = Velithon(
    title="My API",
    description="A comprehensive API built with Velithon",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"]),
        Middleware(LoggingMiddleware)
    ],
    include_security_middleware=True
)

# Set up dependency injection
container = ServiceContainer()
container.register("database_url", "postgresql://localhost/db")
app.register_container(container)

# Routes
@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to my API"}

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(request: Request):
    user_id = request.path_params["user_id"]
    return {"user_id": user_id}

@app.post("/users", tags=["Users"])
async def create_user(request: Request):
    user_data = await request.json()
    return {"user": user_data}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")

# Lifecycle events
@app.on_startup()
async def startup():
    print("Application starting up...")

@app.on_shutdown()
async def shutdown():
    print("Application shutting down...")

# Run the application
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level="INFO"
    )
```

## See Also

- [Routing API](routing.md) - Router and route management
- [Requests API](requests.md) - Request handling
- [Responses API](responses.md) - Response types
- [Middleware API](middleware.md) - Middleware system
- [DI Container API](di.md) - Dependency injection
