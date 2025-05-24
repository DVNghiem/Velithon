# Velithon Framework - Complete User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [Routing](#routing)
6. [HTTP Endpoints](#http-endpoints)
7. [WebSocket Support](#websocket-support)
8. [Dependency Injection](#dependency-injection)
9. [Request Handling](#request-handling)
10. [Response Types](#response-types)
11. [File Uploads and Form Handling](#file-uploads-and-form-handling)
12. [Background Tasks](#background-tasks)
13. [Middleware](#middleware)
14. [CLI and Server Configuration](#cli-and-server-configuration)
15. [Error Handling](#error-handling)
16. [OpenAPI Documentation](#openapi-documentation)
17. [Performance and Best Practices](#performance-and-best-practices)
18. [Examples](#examples)

## Introduction

Velithon is a lightweight, high-performance, asynchronous web framework for Python built on top of the RSGI protocol and powered by [Granian](https://github.com/emmett-framework/granian). It provides a simple yet powerful way to build web applications with features like Dependency Injection (DI), input handling, middleware, and lifecycle management.

### Key Features

- **High Performance**: Optimized for speed with Granian and RSGI, delivering ~110,000-115,000 req/s
- **Dependency Injection (DI)**: Seamless DI with `Provide` and `inject` for managing dependencies
- **Input Handling**: Robust handling of path and query parameters
- **File Uploads**: Comprehensive file upload and form parsing with configurable limits
- **Background Tasks**: Execute tasks asynchronously after response with concurrency control
- **WebSocket Support**: Full WebSocket support with connection management and routing integration
- **Middleware**: Built-in middleware for logging, CORS, and custom middleware support
- **Lifecycle Management**: Application startup and shutdown hooks
- **Command Line Interface**: Flexible CLI for running applications
- **OpenAPI Support**: Automatic API documentation generation

## Installation

### Prerequisites

- Python 3.10 or higher
- `pip` for installing dependencies

### Install Velithon

```bash
pip install velithon
```

## Quick Start

### Basic Application

Create a simple web application:

```python
from velithon import Velithon
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/")
async def root():
    return JSONResponse({"message": "Hello, World!"})

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return JSONResponse({"item_id": item_id})


```

### Run with CLI

```bash
velithon run --app main:app --host 0.0.0.0 --port 8000
```

## Core Concepts

### Application Instance

The `Velithon` class is the main application instance:

```python
from velithon import Velithon

app = Velithon(
    title="My API",
    description="A sample API built with Velithon",
    version="1.0.0"
)
```

### Router

Velithon uses a router to manage routes:

```python
from velithon.routing import Router

router = Router()
router.add_route("/users", UserEndpoint, methods=["GET", "POST"])

app = Velithon(routes=router.routes)
```

## Routing

### Route Decorators

Use decorators to define routes:

```python
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
```

### Path Parameters

Define path parameters with type hints:

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return JSONResponse({"user_id": user_id})

@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(user_id: int, post_id: str):
    return JSONResponse({"user_id": user_id, "post_id": post_id})
```

### Adding Routes Programmatically

```python
from velithon.routing import Router

router = Router()

async def user_handler(request):
    return JSONResponse({"message": "User handler"})

router.add_route("/users", user_handler, methods=["GET"])
app = Velithon(routes=router.routes)
```

## HTTP Endpoints

### Class-Based Endpoints

Create reusable endpoint classes:

```python
from velithon.endpoint import HTTPEndpoint
from velithon.responses import JSONResponse, PlainTextResponse
from velithon.requests import Request

class UserEndpoint(HTTPEndpoint):
    async def get(self, request: Request):
        """Get all users"""
        return JSONResponse({"users": []})
    
    async def post(self, request: Request):
        """Create a new user"""
        body = await request.json()
        return JSONResponse({"message": "User created", "data": body})
    
    async def put(self, request: Request):
        """Update a user"""
        return JSONResponse({"message": "User updated"})
    
    async def delete(self, request: Request):
        """Delete a user"""
        return PlainTextResponse("User deleted")

# Register the endpoint
app.add_route("/users", UserEndpoint, methods=["GET", "POST", "PUT", "DELETE"])
```

### Method-Specific Endpoints

```python
class ProductEndpoint(HTTPEndpoint):
    async def get(self, request: Request):
        product_id = request.path_params.get("product_id")
        return JSONResponse({"product_id": product_id})

app.add_route("/products/{product_id}", ProductEndpoint, methods=["GET"])
```

## WebSocket Support

### Function-Based WebSocket Handlers

```python
from velithon import WebSocket
from velithon.websocket import WebSocketDisconnect

@app.websocket("/echo")
async def echo_handler(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"Echo: {message}")
    except WebSocketDisconnect:
        print("Client disconnected")
```

### Class-Based WebSocket Endpoints

```python
from velithon.websocket import WebSocketEndpoint

class ChatEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        print(f"Client connected: {websocket.client}")
        await websocket.accept()
    
    async def on_receive(self, websocket: WebSocket, data: str):
        # Echo the message back
        await websocket.send_text(f"You said: {data}")
    
    async def on_disconnect(self, websocket: WebSocket):
        print(f"Client disconnected: {websocket.client}")

app.add_websocket_route("/chat", ChatEndpoint)
```

### WebSocket with Path Parameters

```python
@app.websocket("/chat/{room_id}")
async def chat_room(websocket: WebSocket):
    room_id = websocket.path_params["room_id"]
    await websocket.accept()
    
    try:
        while True:
            message = await websocket.receive_text()
            # Broadcast to room
            await websocket.send_text(f"[Room {room_id}] {message}")
    except WebSocketDisconnect:
        pass
```

## Dependency Injection

Velithon provides a powerful dependency injection system.

### Setting Up a Container

```python
from velithon.di import ServiceContainer, SingletonProvider, FactoryProvider, AsyncFactoryProvider

class Database:
    async def query(self, sql: str):
        return {"result": f"Data for: {sql}"}

class UserRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def find_user(self, user_id: int):
        return await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

class UserService:
    def __init__(self, user_repository: UserRepository, api_key: str):
        self.user_repository = user_repository
        self.api_key = api_key
    
    async def get_user(self, user_id: int):
        return await self.user_repository.find_user(user_id)

async def create_user_service(user_repository: UserRepository, api_key: str = "default-key") -> UserService:
    return UserService(user_repository, api_key)

class Container(ServiceContainer):
    db = SingletonProvider(Database)
    user_repository = FactoryProvider(UserRepository, db=db)
    user_service = AsyncFactoryProvider(create_user_service, user_repository=user_repository, api_key="my-api-key")

container = Container()
app.register_container(container)
```

### Using Dependency Injection

```python
from velithon.di import inject, Provide

class UserEndpoint(HTTPEndpoint):
    @inject
    async def get(self, user_service: UserService = Provide[container.user_service]):
        user_data = await user_service.get_user(123)
        return JSONResponse(user_data)

# Function-based endpoint with DI
@inject
@app.get("/users/{user_id}")
async def get_user(user_id: int, user_service: UserService = Provide[container.user_service]):
    user_data = await user_service.get_user(user_id)
    return JSONResponse(user_data)
```

### Provider Types

1. **SingletonProvider**: Creates and reuses a single instance
2. **FactoryProvider**: Creates a new instance each time
3. **AsyncFactoryProvider**: Uses an async function to create instances

```python
class Container(ServiceContainer):
    # Singleton - one instance for the entire application
    db = SingletonProvider(Database)
    
    # Factory - new instance per request
    user_repo = FactoryProvider(UserRepository, db=db)
    
    # Async Factory - for complex async initialization
    user_service = AsyncFactoryProvider(create_user_service, user_repository=user_repo)
```

## Request Handling

### Request Object

```python
from velithon.requests import Request

@app.post("/users")
async def create_user(request: Request):
    # Get JSON body
    body = await request.json()
    
    # Get form data
    form = await request.form()
    
    # Get query parameters
    page = request.query_params.get("page", "1")
    
    # Get path parameters
    user_id = request.path_params.get("user_id")
    
    # Get headers
    auth_header = request.headers.get("authorization")
    
    # Get cookies
    session_id = request.cookies.get("session_id")
    
    return JSONResponse({"message": "User created"})
```

### Parameter Injection

Use type hints and parameter annotations for automatic injection:

```python
from typing import Annotated
from velithon.params import Query, Path, Body
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

class UserEndpoint(HTTPEndpoint):
    async def get(self, user_id: Annotated[int, Path()], 
                  page: Annotated[int, Query()] = 1):
        return JSONResponse({"user_id": user_id, "page": page})
    
    async def post(self, user: Annotated[User, Body()]):
        return JSONResponse({"message": "User created", "user": user.dict()})

app.add_route("/users/{user_id}", UserEndpoint, methods=["GET", "POST"])
```

### Headers and Request Context

```python
from velithon.datastructures import Headers

class UserEndpoint(HTTPEndpoint):
    async def get(self, request: Request, headers: Headers):
        user_agent = headers.get("user-agent")
        return JSONResponse({"user_agent": user_agent})
```

## Response Types

### Built-in Response Types

```python
from velithon.responses import (
    JSONResponse,
    PlainTextResponse,
    HTMLResponse,
    RedirectResponse,
    FileResponse,
    StreamingResponse
)

@app.get("/json")
async def json_response():
    return JSONResponse({"message": "Hello JSON"})

@app.get("/text")
async def text_response():
    return PlainTextResponse("Hello Text")

@app.get("/html")
async def html_response():
    return HTMLResponse("<h1>Hello HTML</h1>")

@app.get("/redirect")
async def redirect_response():
    return RedirectResponse("/json")

@app.get("/file")
async def file_response():
    return FileResponse("path/to/file.pdf")

@app.get("/stream")
async def streaming_response():
    def generate():
        for i in range(100):
            yield f"data chunk {i}\n"
    
    return StreamingResponse(generate(), media_type="text/plain")
```

### Custom Response Status and Headers

```python
@app.get("/custom")
async def custom_response():
    return JSONResponse(
        content={"message": "Created"},
        status_code=201,
        headers={"X-Custom-Header": "value"}
    )
```

## File Uploads and Form Handling

Velithon provides comprehensive support for handling file uploads and form data through its built-in form parsing capabilities.

### Basic File Upload

```python
from velithon import Velithon
from velithon.params import File
from velithon.datastructures import UploadFile

app = Velithon()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Read file content
    content = await file.read()
    
    # Get file information
    filename = file.filename
    content_type = file.content_type
    size = file.size
    
    # Process the file
    with open(f"uploads/{filename}", "wb") as f:
        f.write(content)
    
    return {"filename": filename, "size": size}
```

### Multiple File Uploads

```python
from typing import List

@app.post("/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    uploaded_files = []
    
    for file in files:
        content = await file.read()
        with open(f"uploads/{file.filename}", "wb") as f:
            f.write(content)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": file.size,
            "content_type": file.content_type
        })
    
    return {"uploaded_files": uploaded_files}
```

### Form Data with Files

```python
from velithon.params import Form

@app.post("/upload-with-data")
async def upload_with_data(
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...)
):
    # Process form data
    await file.read()
    
    return {
        "title": title,
        "description": description,
        "filename": file.filename
    }
```

### Advanced File Handling

```python
@app.post("/upload-advanced")
async def upload_advanced(file: UploadFile = File(...)):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files allowed")
    
    # Validate file size (limit to 5MB)
    if file.size > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large")
    
    # Stream file to disk for large files
    with open(f"uploads/{file.filename}", "wb") as f:
        while chunk := await file.read(1024):  # Read in chunks
            f.write(chunk)
    
    return {"message": "File uploaded successfully"}
```

### Form Parsing Configuration

The framework automatically handles multipart form parsing with configurable limits:

```python
# Form parsing happens automatically with these default limits:
# - max_files: 1000
# - max_fields: 1000  
# - max_part_size: 1MB per part

# These limits protect against malicious uploads
```

### File Upload Best Practices

1. **Validate file types**: Always check `content_type` and file extensions
2. **Limit file sizes**: Set reasonable size limits to prevent abuse
3. **Use streaming**: For large files, read in chunks to avoid memory issues
4. **Sanitize filenames**: Clean filename inputs to prevent directory traversal
5. **Store securely**: Don't store uploads in web-accessible directories

```python
import os
import uuid
from pathlib import Path

@app.post("/secure-upload")
async def secure_upload(file: UploadFile = File(...)):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, "File type not allowed")
    
    # Generate secure filename
    file_extension = Path(file.filename).suffix
    secure_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Ensure upload directory exists
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Save file
    file_path = upload_dir / secure_filename
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024):
            f.write(chunk)
    
    return {
        "filename": secure_filename,
        "original_name": file.filename,
        "size": file.size
    }
```

## Background Tasks

Background tasks allow you to execute functions after returning a response to the client. This is useful for operations like sending emails, processing uploads, or logging.

### Basic Background Task

```python
from velithon import Velithon
from velithon.background import BackgroundTask

app = Velithon()

def send_email(email: str, message: str):
    # Simulate email sending
    print(f"Sending email to {email}: {message}")

@app.post("/send-notification")
async def send_notification(email: str, message: str):
    # Create and add background task
    task = BackgroundTask(send_email, email, message)
    
    # Return response immediately
    return {"message": "Notification queued"}
```

### Multiple Background Tasks

```python
from velithon.background import BackgroundTasks

def log_action(action: str, user_id: int):
    print(f"User {user_id} performed: {action}")

def update_analytics(action: str):
    print(f"Analytics updated for: {action}")

@app.post("/user-action")
async def user_action(action: str, user_id: int):
    # Create background tasks collection
    background_tasks = BackgroundTasks()
    
    # Add multiple tasks
    background_tasks.add_task(log_action, action, user_id)
    background_tasks.add_task(update_analytics, action)
    
    # Execute all tasks in background
    await background_tasks()
    
    return {"message": "Action completed"}
```

### Async Background Tasks

```python
import asyncio

async def async_process_data(data: dict):
    await asyncio.sleep(1)  # Simulate async work
    print(f"Processed data: {data}")

@app.post("/process")
async def process_data(data: dict):
    # Background tasks work with both sync and async functions
    task = BackgroundTask(async_process_data, data)
    
    return {"message": "Processing started"}
```

### Background Tasks with Response

You can include background tasks directly in responses:

```python
from velithon.responses import JSONResponse

@app.post("/order")
async def create_order(order_data: dict):
    # Create the order
    order_id = "12345"
    
    # Prepare background tasks
    background_tasks = BackgroundTasks()
    background_tasks.add_task(send_order_confirmation, order_data["email"], order_id)
    background_tasks.add_task(update_inventory, order_data["items"])
    
    # Return response with background tasks
    return JSONResponse(
        content={"order_id": order_id, "status": "created"},
        background=background_tasks
    )
```

### Concurrent Background Tasks

Control how many background tasks run concurrently:

```python
@app.post("/batch-process")
async def batch_process(items: list):
    # Limit concurrent tasks to avoid overwhelming resources
    background_tasks = BackgroundTasks(max_concurrent=5)
    
    for item in items:
        background_tasks.add_task(process_item, item)
    
    # Execute with concurrency control
    await background_tasks()
    
    return {"message": f"Processing {len(items)} items"}
```

### Error Handling in Background Tasks

```python
def risky_task(data: str):
    if not data:
        raise ValueError("Data cannot be empty")
    print(f"Processing: {data}")

@app.post("/risky-operation")
async def risky_operation(data: str):
    background_tasks = BackgroundTasks()
    background_tasks.add_task(risky_task, data)
    
    # Control error behavior
    try:
        await background_tasks(continue_on_error=False)  # Stop on first error
    except RuntimeError as e:
        return {"error": "Background task failed"}
    
    return {"message": "Operation completed"}
```

### Background Task Best Practices

1. **Keep tasks lightweight**: Background tasks should be quick operations
2. **Handle errors gracefully**: Always consider what happens if a task fails
3. **Use for non-critical operations**: Don't rely on background tasks for essential functionality
4. **Monitor resource usage**: Limit concurrent tasks to prevent system overload
5. **Consider task queues**: For complex workflows, use dedicated task queues like Celery

## Middleware

### Built-in Middleware

#### Logging Middleware

Automatically logs requests and responses:

```python
from velithon.middleware import Middleware
from velithon.middleware.logging import LoggingMiddleware

app = Velithon(
    middleware=[
        Middleware(LoggingMiddleware)
    ]
)
```

#### CORS Middleware

Handle Cross-Origin Resource Sharing:

```python
from velithon.middleware.cors import CORSMiddleware

app = Velithon(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
            allow_credentials=True
        )
    ]
)
```

### Custom Middleware

Create custom middleware classes:

```python
from velithon.datastructures import Scope, Protocol

class AuthMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope: Scope, protocol: Protocol):
        # Check authorization
        auth_header = scope.headers.get("authorization")
        
        if not auth_header and scope.path.startswith("/api/"):
            from velithon.responses import JSONResponse
            response = JSONResponse(
                content={"error": "Unauthorized"},
                status_code=401
            )
            await response(scope, protocol)
            return
        
        # Continue to next middleware/application
        await self.app(scope, protocol)

# Add to application
app = Velithon(
    middleware=[
        Middleware(AuthMiddleware),
        Middleware(LoggingMiddleware)
    ]
)
```

### Middleware Order

Middleware is executed in reverse order (last added is executed first):

```python
app = Velithon(
    middleware=[
        Middleware(LoggingMiddleware),    # Executed second
        Middleware(AuthMiddleware),      # Executed first
    ]
)
```

## CLI and Server Configuration

### Command Line Interface

The Velithon CLI provides comprehensive server configuration:

```bash
velithon run --help
```

### Basic Usage

```bash
# Basic run
velithon run --app main:app

# With custom host and port
velithon run --app main:app --host 0.0.0.0 --port 8080

# With multiple workers
velithon run --app main:app --workers 4

# Development mode with auto-reload
velithon run --app main:app --reload --log-level DEBUG
```

### Logging Configuration

```bash
# Enable file logging
velithon run --app main:app --log-to-file --log-file app.log

# JSON format logging
velithon run --app main:app --log-format json --log-level INFO

# Log rotation
velithon run --app main:app --log-to-file --max-bytes 10485760 --backup-count 7
```

### SSL Configuration

```bash
# Enable HTTPS
velithon run --app main:app \
    --ssl-certificate cert.pem \
    --ssl-keyfile key.pem \
    --ssl-keyfile-password mypassword
```

### HTTP Configuration

```bash
# HTTP/2 support
velithon run --app main:app --http 2

# HTTP/1 settings
velithon run --app main:app \
    --http1-keep-alive \
    --http1-header-read-timeout 30000

# HTTP/2 settings
velithon run --app main:app \
    --http2-max-concurrent-streams 100 \
    --http2-initial-connection-window-size 1048576
```

### Performance Tuning

```bash
# Threading configuration
velithon run --app main:app \
    --runtime-threads 4 \
    --blocking-threads 10 \
    --runtime-mode mt

# Event loop selection
velithon run --app main:app --loop uvloop

# Backpressure control
velithon run --app main:app --backpressure 1000
```

## Error Handling

### HTTP Exceptions

```python
from velithon.exceptions import HTTPException

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    if user_id < 1:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Simulate user not found
    if user_id == 999:
        raise HTTPException(status_code=404, detail="User not found")
    
    return JSONResponse({"user_id": user_id})
```

### Custom Exception Handlers

```python
from velithon.requests import Request
from velithon.responses import JSONResponse

async def custom_404_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        content={"error": "Resource not found", "path": request.url.path},
        status_code=404
    )

# Register exception handler
app.add_exception_handler(404, custom_404_handler)
```

### Global Exception Handling

```python
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        content={"error": "Internal server error", "type": type(exc).__name__},
        status_code=500
    )

app.add_exception_handler(Exception, global_exception_handler)
```

## OpenAPI Documentation

### Automatic Documentation

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

### Adding Metadata to Routes

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

### Response Models

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

## Performance and Best Practices

### Application Structure

Organize your application for maintainability:

```
project/
├── main.py                 # Application entry point
├── config.py              # Configuration
├── containers.py          # Dependency injection containers
├── routes/
│   ├── __init__.py
│   ├── users.py           # User routes
│   └── products.py        # Product routes
├── endpoints/
│   ├── __init__.py
│   ├── users.py           # User endpoints
│   └── products.py        # Product endpoints
├── services/
│   ├── __init__.py
│   ├── user_service.py    # Business logic
│   └── email_service.py
├── models/
│   ├── __init__.py
│   └── user.py            # Pydantic models
└── middleware/
    ├── __init__.py
    └── auth.py            # Custom middleware
```

### Performance Tips

1. **Use Async/Await**: Always use async functions for I/O operations
2. **Connection Pooling**: Use connection pools for databases
3. **Caching**: Implement caching for frequently accessed data
4. **Dependency Injection**: Use singletons for expensive resources
5. **Streaming**: Use streaming responses for large data sets

```python
# Good: Async database operations
class UserService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def get_user(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

# Good: Streaming large responses
@app.get("/export/users")
async def export_users():
    async def generate_csv():
        yield "id,name,email\n"
        async for user in get_all_users():
            yield f"{user.id},{user.name},{user.email}\n"
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )
```

### Security Best Practices

1. **Input Validation**: Always validate input data
2. **Authentication**: Implement proper authentication middleware
3. **HTTPS**: Use SSL/TLS in production
4. **CORS**: Configure CORS properly
5. **Rate Limiting**: Implement rate limiting for public APIs

```python
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

@app.post("/users")
async def create_user(user: UserCreate):
    # User data is automatically validated
    return JSONResponse({"message": "User created", "email": user.email})
```

### File Upload Best Practices

1. **File Validation**: Always validate file types, sizes, and content
2. **Secure Storage**: Store files outside the web root directory
3. **Filename Sanitization**: Use UUID or secure naming schemes
4. **Memory Management**: Stream large files to avoid memory issues
5. **Cleanup**: Remove temporary files after processing

```python
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_upload(file: UploadFile) -> bool:
    # Check file extension
    if Path(file.filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed")
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # Optional: Check file content/magic bytes
    content_start = await file.read(1024)
    await file.seek(0)  # Reset file pointer
    
    return True
```

### Background Task Best Practices

1. **Task Scope**: Keep background tasks lightweight and focused
2. **Error Handling**: Always handle exceptions in background tasks
3. **Resource Limits**: Use concurrency limits to prevent system overload
4. **Monitoring**: Log background task execution and failures
5. **Idempotency**: Make tasks idempotent when possible

```python
import logging
from velithon.background import BackgroundTasks

logger = logging.getLogger(__name__)

def safe_background_task(func, *args, **kwargs):
    """Wrapper for safe background task execution"""
    try:
        result = func(*args, **kwargs)
        logger.info(f"Task {func.__name__} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Task {func.__name__} failed: {str(e)}")
        # Don't re-raise to prevent stopping other tasks
        return None

@app.post("/process-order")
async def process_order(order_data: dict):
    background_tasks = BackgroundTasks(max_concurrent=3)
    
    # Wrap tasks for safe execution
    background_tasks.add_task(safe_background_task, send_email, order_data["email"])
    background_tasks.add_task(safe_background_task, update_inventory, order_data["items"])
    background_tasks.add_task(safe_background_task, log_order, order_data)
    
    await background_tasks(continue_on_error=True)
    
    return {"message": "Order processed"}
```

## Examples

### Complete REST API Example

```python
from velithon import Velithon
from velithon.endpoint import HTTPEndpoint
from velithon.responses import JSONResponse
from velithon.requests import Request
from velithon.di import ServiceContainer, SingletonProvider, inject, Provide
from velithon.middleware import Middleware
from velithon.middleware.cors import CORSMiddleware
from velithon.middleware.logging import LoggingMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Models
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

# Services
class UserService:
    def __init__(self):
        self.users = []
        self.next_id = 1
    
    async def create_user(self, user_data: dict) -> User:
        user = User(id=self.next_id, **user_data)
        self.users.append(user)
        self.next_id += 1
        return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        return next((u for u in self.users if u.id == user_id), None)
    
    async def get_all_users(self) -> List[User]:
        return self.users
    
    async def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        user = await self.get_user(user_id)
        if user:
            for key, value in user_data.items():
                setattr(user, key, value)
        return user
    
    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if user:
            self.users.remove(user)
            return True
        return False

# Container
class Container(ServiceContainer):
    user_service = SingletonProvider(UserService)

container = Container()

# Endpoints
class UserEndpoint(HTTPEndpoint):
    @inject
    async def get(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Get all users"""
        users = await user_service.get_all_users()
        return JSONResponse([user.dict() for user in users])
    
    @inject
    async def post(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Create a new user"""
        user_data = await request.json()
        user = await user_service.create_user(user_data)
        return JSONResponse(user.dict(), status_code=201)

class UserDetailEndpoint(HTTPEndpoint):
    @inject
    async def get(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Get user by ID"""
        user_id = int(request.path_params["user_id"])
        user = await user_service.get_user(user_id)
        
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        return JSONResponse(user.dict())
    
    @inject
    async def put(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Update user"""
        user_id = int(request.path_params["user_id"])
        user_data = await request.json()
        user = await user_service.update_user(user_id, user_data)
        
        if not user:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        return JSONResponse(user.dict())
    
    @inject
    async def delete(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Delete user"""
        user_id = int(request.path_params["user_id"])
        success = await user_service.delete_user(user_id)
        
        if not success:
            return JSONResponse({"error": "User not found"}, status_code=404)
        
        return JSONResponse({"message": "User deleted"})

# Application
app = Velithon(
    title="User API",
    description="A simple user management API",
    version="1.0.0",
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"]),
        Middleware(LoggingMiddleware)
    ]
)

# Register container
app.register_container(container)

# Routes
app.add_route("/users", UserEndpoint, methods=["GET", "POST"])
app.add_route("/users/{user_id}", UserDetailEndpoint, methods=["GET", "PUT", "DELETE"])

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})

```

### WebSocket Chat Example

```python
from velithon import Velithon, WebSocket
from velithon.websocket import WebSocketDisconnect, WebSocketEndpoint
from velithon.responses import HTMLResponse
import json
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

app = Velithon()

class ChatEndpoint(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket):
        await manager.connect(websocket)
        await manager.broadcast(json.dumps({
            "type": "user_joined",
            "message": f"User {websocket.client} joined the chat"
        }))
    
    async def on_receive(self, websocket: WebSocket, data: str):
        message_data = json.loads(data)
        response = {
            "type": "message",
            "user": str(websocket.client),
            "message": message_data.get("message", "")
        }
        await manager.broadcast(json.dumps(response))
    
    async def on_disconnect(self, websocket: WebSocket):
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({
            "type": "user_left",
            "message": f"User {websocket.client} left the chat"
        }))

app.add_websocket_route("/ws/chat", ChatEndpoint)

@app.get("/")
async def chat_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velithon Chat</title>
    </head>
    <body>
        <div id="messages"></div>
        <input type="text" id="messageInput" placeholder="Type a message...">
        <button onclick="sendMessage()">Send</button>
        
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws/chat");
            const messages = document.getElementById("messages");
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const div = document.createElement("div");
                div.innerHTML = `<strong>${data.type}:</strong> ${data.message}`;
                messages.appendChild(div);
            };
            
            function sendMessage() {
                const input = document.getElementById("messageInput");
                ws.send(JSON.stringify({message: input.value}));
                input.value = "";
            }
            
            document.getElementById("messageInput").addEventListener("keypress", function(e) {
                if (e.key === "Enter") {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """)

```

### File Upload and Processing Service

```python
from velithon import Velithon
from velithon.params import File, Form
from velithon.datastructures import UploadFile
from velithon.responses import JSONResponse, HTMLResponse
from velithon.background import BackgroundTasks
from velithon.middleware import Middleware
from velithon.middleware.cors import CORSMiddleware
from pathlib import Path
import uuid
import asyncio
from typing import List

app = Velithon(
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"])
    ]
)

# Create upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Background task functions
def process_image(file_path: str, processing_type: str):
    """Simulate image processing (resize, compress, etc.)"""
    print(f"Processing {file_path} with {processing_type}")
    # Simulate processing time
    import time
    time.sleep(2)
    print(f"Finished processing {file_path}")

def send_notification(email: str, filename: str):
    """Simulate sending email notification"""
    print(f"Sending notification to {email} about {filename}")

async def log_upload(filename: str, size: int, user_id: str):
    """Async logging function"""
    await asyncio.sleep(0.1)  # Simulate async database write
    print(f"Logged upload: {filename} ({size} bytes) by user {user_id}")

# Routes
@app.get("/")
async def upload_form():
    """Upload form page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload Service</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            form { margin: 20px 0; }
            input, select { margin: 10px 0; display: block; }
            button { background: #007cba; color: white; padding: 10px; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>File Upload Service</h1>
        
        <h2>Single File Upload</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="text" name="user_email" placeholder="Your email" required>
            <input type="text" name="user_id" placeholder="User ID" required>
            <select name="processing_type">
                <option value="resize">Resize</option>
                <option value="compress">Compress</option>
                <option value="thumbnail">Create Thumbnail</option>
            </select>
            <input type="file" name="file" required>
            <button type="submit">Upload File</button>
        </form>
        
        <h2>Multiple Files Upload</h2>
        <form action="/upload-multiple" method="post" enctype="multipart/form-data">
            <input type="text" name="user_email" placeholder="Your email" required>
            <input type="text" name="user_id" placeholder="User ID" required>
            <input type="file" name="files" multiple required>
            <button type="submit">Upload Files</button>
        </form>
    </body>
    </html>
    """)

@app.post("/upload")
async def upload_file(
    user_email: str = Form(...),
    user_id: str = Form(...),
    processing_type: str = Form("resize"),
    file: UploadFile = File(...)
):
    """Handle single file upload with background processing"""
    
    # Validate file
    if not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)
    
    # Validate file size (max 10MB)
    if file.size > 10 * 1024 * 1024:
        return JSONResponse({"error": "File too large (max 10MB)"}, status_code=400)
    
    # Generate secure filename
    file_extension = Path(file.filename).suffix
    secure_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / secure_filename
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Set up background tasks
    background_tasks = BackgroundTasks(max_concurrent=3)
    background_tasks.add_task(process_image, str(file_path), processing_type)
    background_tasks.add_task(send_notification, user_email, file.filename)
    background_tasks.add_task(log_upload, file.filename, file.size, user_id)
    
    # Execute background tasks
    await background_tasks(continue_on_error=True)
    
    return JSONResponse({
        "message": "File uploaded successfully",
        "filename": secure_filename,
        "original_name": file.filename,
        "size": file.size,
        "processing_type": processing_type,
        "status": "processing_started"
    })

@app.post("/upload-multiple")
async def upload_multiple_files(
    user_email: str = Form(...),
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Handle multiple file uploads with batch processing"""
    
    if not files:
        return JSONResponse({"error": "No files provided"}, status_code=400)
    
    uploaded_files = []
    background_tasks = BackgroundTasks(max_concurrent=5)
    
    for file in files:
        # Validate each file
        if file.size > 10 * 1024 * 1024:
            continue  # Skip files that are too large
        
        # Generate secure filename
        file_extension = Path(file.filename).suffix
        secure_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / secure_filename
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Add to background processing
        background_tasks.add_task(process_image, str(file_path), "batch_resize")
        background_tasks.add_task(log_upload, file.filename, file.size, user_id)
        
        uploaded_files.append({
            "filename": secure_filename,
            "original_name": file.filename,
            "size": file.size
        })
    
    # Send single notification for batch upload
    background_tasks.add_task(
        send_notification, 
        user_email, 
        f"Batch upload of {len(uploaded_files)} files"
    )
    
    # Execute all background tasks
    await background_tasks(continue_on_error=True)
    
    return JSONResponse({
        "message": f"Uploaded {len(uploaded_files)} files successfully",
        "files": uploaded_files,
        "status": "batch_processing_started"
    })

@app.get("/status/{filename}")
async def get_processing_status(filename: str):
    """Check if a file exists (simple status check)"""
    file_path = UPLOAD_DIR / filename
    
    if file_path.exists():
        return JSONResponse({
            "filename": filename,
            "status": "completed",
            "size": file_path.stat().st_size
        })
    else:
        return JSONResponse({
            "filename": filename,
            "status": "not_found"
        }, status_code=404)

if __name__ == "__main__":
    print("Starting File Upload Service...")
    print("Upload directory:", UPLOAD_DIR.absolute())
```

## Quick Reference

### File Upload Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `File(...)` | Required file upload | `file: UploadFile = File(...)` |
| `File(None)` | Optional file upload | `file: UploadFile = File(None)` |
| `List[UploadFile]` | Multiple files | `files: List[UploadFile] = File(...)` |

### Background Task Functions

| Function | Description | Example |
|----------|-------------|---------|
| `BackgroundTask(func, *args, **kwargs)` | Single task | `BackgroundTask(send_email, email, message)` |
| `BackgroundTasks(max_concurrent=10)` | Task collection | `tasks = BackgroundTasks(max_concurrent=5)` |
| `tasks.add_task(func, *args, **kwargs)` | Add task | `tasks.add_task(process_data, data)` |
| `await tasks(continue_on_error=True)` | Execute tasks | `await tasks(continue_on_error=False)` |

### File Upload Properties

| Property | Type | Description |
|----------|------|-------------|
| `file.filename` | `str` | Original filename |
| `file.content_type` | `str` | MIME type |
| `file.size` | `int` | File size in bytes |
| `await file.read()` | `bytes` | Read entire file |
| `await file.read(size)` | `bytes` | Read chunk |
| `await file.seek(position)` | `None` | Set file position |

### Form Data Limits

| Setting | Default | Description |
|---------|---------|-------------|
| `max_files` | 1000 | Maximum number of files |
| `max_fields` | 1000 | Maximum form fields |
| `max_part_size` | 1MB | Maximum size per part |

This comprehensive guide covers all major aspects of the Velithon framework. Use it as a reference for building high-performance web applications with Velithon's powerful features.
