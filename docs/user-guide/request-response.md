# Request & Response

This guide covers the request and response handling capabilities in Velithon, including parameter injection, data access, and response formatting.

## Request Object

The `Request` object provides access to all incoming HTTP request data. It's automatically available through dependency injection or can be accessed directly in endpoints.

### Basic Request Properties

```python
from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/info")
async def request_info(request: Request):
    return JSONResponse({
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query_string": request.url.query,
        "scheme": request.url.scheme,
        "headers": dict(request.headers),
        "client": request.client,
        "request_id": request.request_id,
    })
```

### Accessing Request Data

#### JSON Body

```python
@app.post("/users")
async def create_user(request: Request):
    # Get JSON data from request body
    user_data = await request.json()
    
    # Process the data
    return JSONResponse({
        "message": "User created",
        "data": user_data
    })
```

#### Form Data

```python
@app.post("/forms")
async def handle_form(request: Request):
    # Get form data (both URL-encoded and multipart)
    form = await request.form()
    
    # Access specific fields
    name = form.get("name")
    email = form.get("email")
    
    return JSONResponse({
        "name": name,
        "email": email
    })
```

#### Raw Body

```python
@app.post("/raw")
async def handle_raw(request: Request):
    # Get raw body bytes
    body = await request.body()
    
    # Process raw data
    return JSONResponse({
        "size": len(body),
        "content_type": request.headers.get("content-type")
    })
```

#### Streaming Body

```python
@app.post("/stream")
async def handle_stream(request: Request):
    chunks = []
    async for chunk in request.stream():
        chunks.append(chunk)
    
    total_size = sum(len(chunk) for chunk in chunks)
    return JSONResponse({"chunks": len(chunks), "total_size": total_size})
```

### Query Parameters

```python
@app.get("/search")
async def search(request: Request):
    # Get query parameters
    query = request.query_params.get("q", "")
    page = int(request.query_params.get("page", "1"))
    limit = int(request.query_params.get("limit", "10"))
    
    # Multiple values for same parameter
    tags = request.query_params.getlist("tag")
    
    return JSONResponse({
        "query": query,
        "page": page,
        "limit": limit,
        "tags": tags
    })
```

### Path Parameters

```python
@app.get("/users/{user_id}")
async def get_user(request: Request):
    user_id = request.path_params["user_id"]
    
    return JSONResponse({
        "user_id": user_id,
        "type": type(user_id).__name__
    })
```

### Headers

```python
@app.get("/headers")
async def get_headers(request: Request):
    # Get specific header
    user_agent = request.headers.get("user-agent")
    authorization = request.headers.get("authorization")
    
    # Get all headers
    all_headers = dict(request.headers)
    
    return JSONResponse({
        "user_agent": user_agent,
        "authorization": authorization,
        "all_headers": all_headers
    })
```

### Cookies

```python
@app.get("/cookies")
async def get_cookies(request: Request):
    # Get specific cookie
    session_id = request.cookies.get("session_id")
    
    # Get all cookies
    all_cookies = dict(request.cookies)
    
    return JSONResponse({
        "session_id": session_id,
        "all_cookies": all_cookies
    })
```

### Session Data

```python
from velithon.middleware.session import SessionMiddleware
from velithon.middleware import Middleware

# Initialize app with session middleware
app = Velithon(middleware=[
    Middleware(SessionMiddleware, secret_key="your-secret-key")
])

@app.get("/session")
async def get_session(request: Request):
    # Access session data
    user_id = request.session.get("user_id")
    username = request.session.get("username")
    
    return JSONResponse({
        "user_id": user_id,
        "username": username,
        "is_authenticated": user_id is not None
    })
```

## Parameter Injection

Velithon provides powerful parameter injection capabilities that automatically parse and validate request data based on type hints.

### Query Parameters

```python
from typing import Annotated
from velithon.params import Query

@app.get("/search")
async def search(
    q: Annotated[str, Query(description="Search query")] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    tags: Annotated[list[str], Query()] = None
):
    return JSONResponse({
        "query": q,
        "page": page,
        "limit": limit,
        "tags": tags or []
    })
```

### Path Parameters

```python
from velithon.params import Path

@app.get("/users/{user_id}")
async def get_user(
    user_id: Annotated[int, Path(description="User ID")]
):
    return JSONResponse({"user_id": user_id})

@app.get("/files/{file_path:path}")
async def get_file(
    file_path: Annotated[str, Path(description="File path")]
):
    return JSONResponse({"file_path": file_path})
```

### Header Parameters

```python
from velithon.params import Header

@app.get("/protected")
async def protected_endpoint(
    authorization: Annotated[str, Header(description="Bearer token")],
    user_agent: Annotated[str, Header(alias="User-Agent")] = "Unknown"
):
    return JSONResponse({
        "auth": authorization,
        "user_agent": user_agent
    })
```

### Body Parameters

```python
from pydantic import BaseModel
from velithon.params import Body

class User(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users")
async def create_user(
    user: Annotated[User, Body(description="User data")]
):
    return JSONResponse({
        "message": "User created",
        "user": user.model_dump()
    })
```

### Form Parameters

```python
from velithon.params import Form

@app.post("/forms")
async def handle_form(
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    age: Annotated[int, Form()] = 0
):
    return JSONResponse({
        "name": name,
        "email": email,
        "age": age
    })
```

### File Parameters

```python
from velithon.params import File
from velithon.datastructures import UploadFile

@app.post("/upload")
async def upload_file(
    file: Annotated[UploadFile, File(description="File to upload")]
):
    content = await file.read()
    
    return JSONResponse({
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content)
    })

@app.post("/multiple-files")
async def upload_multiple(
    files: Annotated[list[UploadFile], File()]
):
    results = []
    for file in files:
        content = await file.read()
        results.append({
            "filename": file.filename,
            "size": len(content)
        })
    
    return JSONResponse({"files": results})
```

## Response Types

Velithon provides various response types for different use cases.

### JSON Response

```python
from velithon.responses import JSONResponse

@app.get("/json")
async def json_response():
    return JSONResponse({
        "message": "Hello, World!",
        "data": [1, 2, 3],
        "status": "success"
    })

# With custom status and headers
@app.post("/created")
async def create_resource():
    return JSONResponse(
        content={"id": 123, "message": "Created"},
        status_code=201,
        headers={"Location": "/resources/123"}
    )
```

### HTML Response

```python
from velithon.responses import HTMLResponse

@app.get("/html")
async def html_response():
    html_content = """
    <html>
        <head><title>Velithon</title></head>
        <body><h1>Hello, World!</h1></body>
    </html>
    """
    return HTMLResponse(content=html_content)
```

### Plain Text Response

```python
from velithon.responses import PlainTextResponse

@app.get("/text")
async def text_response():
    return PlainTextResponse("Hello, World!")
```

### File Response

```python
from velithon.responses import FileResponse

@app.get("/download")
async def download_file():
    return FileResponse(
        path="/path/to/file.pdf",
        filename="document.pdf",
        headers={"X-Custom": "value"}
    )
```

### Streaming Response

```python
from velithon.responses import StreamingResponse

@app.get("/stream")
async def stream_response():
    def generate():
        for i in range(100):
            yield f"chunk {i}\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
```

### Server-Sent Events (SSE)

```python
from velithon.responses import SSEResponse

@app.get("/events")
async def sse_endpoint():
    async def event_generator():
        for i in range(10):
            yield {"data": f"Event {i}", "event": "message"}
            await asyncio.sleep(1)
    
    return SSEResponse(event_generator())
```

### Redirect Response

```python
from velithon.responses import RedirectResponse

@app.get("/redirect")
async def redirect():
    return RedirectResponse(url="/new-location")

@app.get("/permanent-redirect")
async def permanent_redirect():
    return RedirectResponse(url="/new-location", status_code=301)
```

## Response Headers and Cookies

### Setting Headers

```python
@app.get("/headers")
async def with_headers():
    response = JSONResponse({"message": "Hello"})
    response.headers["X-Custom-Header"] = "custom-value"
    response.headers["X-API-Version"] = "1.0"
    return response

# Or in constructor
@app.get("/headers2")
async def with_headers2():
    return JSONResponse(
        content={"message": "Hello"},
        headers={
            "X-Custom-Header": "custom-value",
            "X-API-Version": "1.0"
        }
    )
```

### Setting Cookies

```python
@app.get("/login")
async def login():
    response = JSONResponse({"message": "Logged in"})
    response.set_cookie(
        key="session_id",
        value="abc123",
        max_age=3600,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return response

@app.get("/logout")
async def logout():
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("session_id")
    return response
```

### Security Headers

```python
@app.get("/secure")
async def secure_endpoint():
    response = JSONResponse({"data": "sensitive"})
    
    # Add security headers
    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'"
    })
    
    return response
```

## Error Handling

### Custom Error Responses

```python
from velithon.exceptions import HTTPException

@app.get("/error")
async def error_endpoint():
    raise HTTPException(
        status_code=400,
        detail="Invalid request",
        headers={"X-Error": "validation-failed"}
    )

# Handle errors within the endpoint function
@app.get("/safe-divide/{a}/{b}")
async def safe_divide(a: int, b: int):
    try:
        result = a / b
        return {"result": result}
    except ZeroDivisionError:
        return JSONResponse(
            content={"error": "Division by zero", "detail": "Cannot divide by zero"},
            status_code=400
        )
    except ValueError as e:
        return JSONResponse(
            content={"error": "Invalid value", "detail": str(e)},
            status_code=400
        )
```

### Validation Errors

```python
from pydantic import ValidationError
from velithon.exceptions import ValidationException

@app.post("/users")
async def create_user(user_data: dict):
    try:
        # Validate the user data
        user = UserCreate(**user_data)
        return create_new_user(user)
    except ValidationError as e:
        # Handle validation errors manually
        raise ValidationException(
            detail="Validation failed",
            errors=e.errors()
        )
```
```

## Background Tasks

Execute tasks after returning a response:

```python
from velithon.background import BackgroundTask

def write_log(message: str):
    with open("log.txt", "a") as f:
        f.write(f"{message}\n")

@app.post("/users")
async def create_user(user: User):
    # Create user logic here
    
    task = BackgroundTask(write_log, f"User created: {user.name}")
    return JSONResponse(
        content={"message": "User created"},
        background=task
    )
```

## Advanced Request Features

### Request Context and State

```python
from velithon.middleware import Middleware
import uuid

class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        scope.state.request_id = str(uuid.uuid4())
        
        async def add_request_id_header(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"X-Request-ID"] = scope.state.request_id.encode()
                message["headers"] = list(headers.items())
            await send(message)
        
        await self.app(scope, receive, add_request_id_header)

app = Velithon(
    middleware=[
        Middleware(RequestIDMiddleware)
    ]
)

@app.get("/info")
async def get_info(request: Request):
    return JSONResponse({
        "request_id": request.state.request_id
    })
```

### File Upload with Progress

```python
@app.post("/upload-progress")
async def upload_with_progress(request: Request):
    total_size = 0
    chunks = []
    
    async for chunk in request.stream():
        chunks.append(chunk)
        total_size += len(chunk)
        
        # Could send progress updates here
        print(f"Received {total_size} bytes")
    
    return JSONResponse({
        "total_size": total_size,
        "chunks": len(chunks)
    })
```

This comprehensive guide covers the main request and response handling patterns in Velithon. The framework's parameter injection system provides type safety and automatic validation, while the response system offers flexibility for various content types and formats.
