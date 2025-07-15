# Responses API Reference

Velithon provides a comprehensive set of response types for different use cases, from simple JSON responses to streaming and file downloads. All response types are optimized for performance and provide a consistent API.

## Base Response Class

### Response

```python
from velithon.responses import Response

Response(
    content: Any = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str | None = None
)
```

Base response class that all other responses inherit from.

**Example:**
```python
@app.get("/custom")
async def custom_response():
    return Response(
        content="Custom content",
        status_code=200,
        headers={"X-Custom": "header"},
        media_type="text/plain"
    )
```

## JSON Responses

### JSONResponse

```python
from velithon.responses import JSONResponse

JSONResponse(
    content: Any,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str = "application/json"
)
```

Standard JSON response using Python's built-in JSON encoder.

**Example:**
```python
@app.get("/users")
async def list_users():
    return JSONResponse({
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ],
        "total": 2
    })

@app.post("/users")
async def create_user(request: Request):
    user_data = await request.json()
    return JSONResponse(
        {"user": user_data, "id": 123},
        status_code=201,
        headers={"Location": "/users/123"}
    )
```

### JSONResponse

```python
from velithon.responses import JSONResponse

JSONResponse(
    content: Any,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

High-performance JSON response using Rust-based `orjson` for faster serialization.

**Example:**
```python
@app.get("/large-dataset")
async def get_large_dataset():
    # For large datasets, use optimized JSON
    large_data = {"items": list(range(10000))}
    return JSONResponse(large_data)

@app.get("/performance-critical")
async def performance_endpoint():
    # Use for performance-critical endpoints
    data = {
        "timestamp": datetime.utcnow(),
        "data": complex_computation(),
        "metadata": {"version": "1.0"}
    }
    return JSONResponse(data)
```

## HTML Responses

### HTMLResponse

```python
from velithon.responses import HTMLResponse

HTMLResponse(
    content: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

HTML response for serving web pages.

**Example:**
```python
@app.get("/page")
async def serve_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Page</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Welcome to Velithon!</h1>
        <p>This is an HTML response.</p>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.get("/error-page")
async def error_page():
    return HTMLResponse(
        "<h1>404 - Page Not Found</h1>",
        status_code=404
    )
```

## Plain Text Responses

### PlainTextResponse

```python
from velithon.responses import PlainTextResponse

PlainTextResponse(
    content: str,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

Plain text response.

**Example:**
```python
@app.get("/health")
async def health_check():
    return PlainTextResponse("OK")

@app.get("/robots.txt")
async def robots_txt():
    content = """
User-agent: *
Disallow: /admin/
Allow: /
    """.strip()
    return PlainTextResponse(content)
```

## File Responses

### FileResponse

```python
from velithon.responses import FileResponse

FileResponse(
    path: str | PathLike,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str | None = None,
    filename: str | None = None
)
```

Serve files from disk with proper headers and MIME type detection.

**Example:**
```python
@app.get("/download/{filename}")
async def download_file(request: Request):
    filename = request.path_params["filename"]
    file_path = f"downloads/{filename}"
    
    # Check if file exists
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    
    return FileResponse(
        path=file_path,
        filename=filename,  # Sets Content-Disposition header
        media_type="application/octet-stream"
    )

@app.get("/images/{image_name}")
async def serve_image(request: Request):
    image_name = request.path_params["image_name"]
    return FileResponse(
        path=f"static/images/{image_name}",
        media_type="image/jpeg"
    )

@app.get("/pdf/{doc_id}")
async def serve_pdf(request: Request):
    doc_id = request.path_params["doc_id"]
    return FileResponse(
        path=f"documents/{doc_id}.pdf",
        filename=f"document-{doc_id}.pdf",
        media_type="application/pdf"
    )
```

## Streaming Responses

### StreamingResponse

```python
from velithon.responses import StreamingResponse

StreamingResponse(
    content: Iterable[str] | Iterable[bytes] | AsyncIterable[str] | AsyncIterable[bytes],
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str | None = None
)
```

Stream content to the client, useful for large responses or real-time data.

**Example:**
```python
import asyncio

@app.get("/stream-data")
async def stream_data():
    async def generate_data():
        for i in range(100):
            yield f"data chunk {i}\n"
            await asyncio.sleep(0.1)  # Simulate processing time
    
    return StreamingResponse(
        generate_data(),
        media_type="text/plain"
    )

@app.get("/csv-export")
async def export_csv():
    async def generate_csv():
        # CSV header
        yield "id,name,email,created_at\n"
        
        # Data rows (could be from database)
        for i in range(1000):
            yield f"{i},User {i},user{i}@example.com,2024-01-01\n"
            await asyncio.sleep(0.001)  # Non-blocking
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )

@app.get("/log-stream")
async def stream_logs():
    async def read_logs():
        with open("app.log", "r") as f:
            # Stream existing content
            for line in f:
                yield line
            
            # Continue streaming new content
            while True:
                line = f.readline()
                if line:
                    yield line
                else:
                    await asyncio.sleep(0.1)
    
    return StreamingResponse(
        read_logs(),
        media_type="text/plain"
    )
```

## Redirect Responses

### RedirectResponse

```python
from velithon.responses import RedirectResponse

RedirectResponse(
    url: str,
    status_code: int = 307,
    headers: dict[str, str] | None = None
)
```

Redirect responses with various status codes.

**Example:**
```python
@app.get("/old-path")
async def old_endpoint():
    # Permanent redirect
    return RedirectResponse("/new-path", status_code=301)

@app.post("/login")
async def login(request: Request):
    credentials = await request.json()
    
    if authenticate(credentials):
        # Redirect after successful login
        return RedirectResponse("/dashboard", status_code=303)
    else:
        return JSONResponse(
            {"error": "Invalid credentials"}, 
            status_code=401
        )

@app.get("/external-redirect")
async def external_redirect():
    return RedirectResponse("https://example.com", status_code=302)

@app.get("/conditional-redirect")
async def conditional_redirect(request: Request):
    user_agent = request.headers.get("user-agent", "")
    
    if "mobile" in user_agent.lower():
        return RedirectResponse("/mobile-version")
    else:
        return RedirectResponse("/desktop-version")
```

## Server-Sent Events

### SSEResponse

```python
from velithon.responses import SSEResponse

SSEResponse(
    content: AsyncIterable[str],
    status_code: int = 200,
    headers: dict[str, str] | None = None,
    ping_interval: float = 30.0
)
```

Server-Sent Events for real-time updates to web clients.

**Example:**
```python
@app.get("/events")
async def event_stream():
    async def generate_events():
        counter = 0
        while True:
            # Send data event
            yield f"data: {{'counter': {counter}, 'timestamp': '{datetime.utcnow().isoformat()}'}}\n\n"
            
            counter += 1
            await asyncio.sleep(1)
    
    return SSEResponse(generate_events())

@app.get("/notifications")
async def notification_stream():
    async def send_notifications():
        # Send initial connection event
        yield "event: connected\ndata: {\"message\": \"Connected to notifications\"}\n\n"
        
        # Send periodic updates
        while True:
            notification = await get_user_notifications()
            if notification:
                yield f"event: notification\ndata: {json.dumps(notification)}\n\n"
            
            await asyncio.sleep(5)
    
    return SSEResponse(send_notifications())

@app.get("/live-data")
async def live_data_stream():
    async def stream_live_data():
        while True:
            data = await fetch_live_data()
            
            # Send structured SSE event
            yield f"event: update\n"
            yield f"data: {json.dumps(data)}\n"
            yield f"id: {int(time.time())}\n\n"
            
            await asyncio.sleep(2)
    
    return SSEResponse(stream_live_data(), ping_interval=15.0)
```

## Template Responses

### TemplateResponse

```python
from velithon.templates import TemplateResponse

TemplateResponse(
    template: str,
    context: dict = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None
)
```

Render templates with context data (requires template engine setup).

**Example:**
```python
from velithon.templates import TemplateEngine

# Set up template engine
template_engine = TemplateEngine("templates/")

@app.get("/profile/{user_id}")
async def user_profile(request: Request):
    user_id = request.path_params["user_id"]
    user = await get_user(user_id)
    
    if not user:
        return HTMLResponse("<h1>User not found</h1>", status_code=404)
    
    return template_engine.render_response(
        "user_profile.html",
        {
            "user": user,
            "title": f"Profile - {user.name}",
            "current_year": datetime.now().year
        }
    )

@app.get("/dashboard")
async def dashboard(request: Request):
    # Get user from session/auth
    user = request.state.user
    
    context = {
        "user": user,
        "stats": await get_user_stats(user.id),
        "recent_activity": await get_recent_activity(user.id)
    }
    
    return template_engine.render_response("dashboard.html", context)
```

## Response Headers and Cookies

### Setting Headers

```python
@app.get("/with-headers")
async def response_with_headers():
    response = JSONResponse({"message": "Hello"})
    
    # Set individual headers
    response.headers["X-Custom-Header"] = "Custom Value"
    response.headers["Cache-Control"] = "max-age=3600"
    
    return response

@app.get("/api-info")
async def api_info():
    return JSONResponse(
        {"version": "1.0.0", "status": "running"},
        headers={
            "X-API-Version": "1.0.0",
            "X-Rate-Limit": "1000",
            "Access-Control-Allow-Origin": "*"
        }
    )
```

### Setting Cookies

```python
@app.post("/login")
async def login(request: Request):
    # Authenticate user
    credentials = await request.json()
    user = authenticate(credentials)
    
    if user:
        response = JSONResponse({"message": "Login successful"})
        
        # Set session cookie
        response.set_cookie(
            "session_id",
            generate_session_id(),
            max_age=86400,  # 1 day
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        # Set user preference cookie
        response.set_cookie(
            "theme",
            "dark",
            max_age=86400 * 30,  # 30 days
            path="/"
        )
        
        return response
    
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)

@app.post("/logout")
async def logout():
    response = JSONResponse({"message": "Logged out"})
    
    # Delete cookies
    response.delete_cookie("session_id")
    response.delete_cookie("theme")
    
    return response
```

## Error Responses

### Error Response Patterns

```python
from velithon.exceptions import HTTPException

@app.get("/users/{user_id}")
async def get_user(request: Request):
    user_id = request.path_params["user_id"]
    user = await fetch_user(user_id)
    
    if not user:
        return JSONResponse(
            {"error": "User not found", "user_id": user_id},
            status_code=404
        )
    
    return JSONResponse({"user": user})

@app.post("/validate-data")
async def validate_data(request: Request):
    try:
        data = await request.json()
        validated_data = validate(data)
        return JSONResponse({"data": validated_data})
    
    except ValidationError as e:
        return JSONResponse(
            {
                "error": "Validation failed",
                "details": e.errors(),
                "invalid_fields": [error["loc"][0] for error in e.errors()]
            },
            status_code=422
        )
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"error": "Invalid JSON format"},
            status_code=400
        )
```

## Custom Response Types

### Creating Custom Responses

```python
class XMLResponse(Response):
    def __init__(self, content: dict, status_code: int = 200, headers: dict = None):
        # Convert dict to XML
        xml_content = self.dict_to_xml(content)
        super().__init__(
            content=xml_content,
            status_code=status_code,
            headers=headers,
            media_type="application/xml"
        )
    
    def dict_to_xml(self, data: dict, root_tag: str = "response") -> str:
        # Simple XML conversion (use a proper library in production)
        xml_parts = [f"<{root_tag}>"]
        for key, value in data.items():
            xml_parts.append(f"  <{key}>{value}</{key}>")
        xml_parts.append(f"</{root_tag}>")
        return "\n".join(xml_parts)

@app.get("/xml-data")
async def get_xml_data():
    data = {"message": "Hello", "timestamp": datetime.utcnow().isoformat()}
    return XMLResponse(data)

class CSVResponse(Response):
    def __init__(self, data: list[dict], filename: str = "data.csv", status_code: int = 200):
        csv_content = self.dict_list_to_csv(data)
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv"
        }
        super().__init__(
            content=csv_content,
            status_code=status_code,
            headers=headers,
            media_type="text/csv"
        )
    
    def dict_list_to_csv(self, data: list[dict]) -> str:
        if not data:
            return ""
        
        # Get headers from first row
        headers = list(data[0].keys())
        csv_lines = [",".join(headers)]
        
        # Add data rows
        for row in data:
            csv_lines.append(",".join(str(row.get(header, "")) for header in headers))
        
        return "\n".join(csv_lines)

@app.get("/export-users")
async def export_users():
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"}
    ]
    return CSVResponse(users, "users.csv")
```

## Complete Example

```python
from velithon import Velithon
from velithon.responses import (
    JSONResponse, HTMLResponse, FileResponse, 
    StreamingResponse, RedirectResponse, PlainTextResponse
)
import asyncio
import os

app = Velithon()

@app.get("/")
async def root():
    return JSONResponse({
        "message": "Welcome to Velithon API",
        "version": "1.0.0",
        "endpoints": ["/users", "/files", "/stream", "/health"]
    })

@app.get("/users/{user_id}")
async def get_user(request: Request):
    user_id = request.path_params["user_id"]
    
    # Simulate user lookup
    if user_id == "404":
        return JSONResponse(
            {"error": "User not found"}, 
            status_code=404
        )
    
    return JSONResponse({
        "user_id": user_id,
        "name": f"User {user_id}",
        "created_at": "2024-01-01T00:00:00Z"
    })

@app.get("/files/{filename}")
async def serve_file(request: Request):
    filename = request.path_params["filename"]
    file_path = f"static/{filename}"
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return JSONResponse(
            {"error": "File not found"}, 
            status_code=404
        )

@app.get("/stream")
async def stream_data():
    async def generate():
        for i in range(10):
            yield f"Chunk {i}\n"
            await asyncio.sleep(0.5)
    
    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/health")
async def health_check():
    return PlainTextResponse("OK")

@app.get("/redirect")
async def redirect_example():
    return RedirectResponse("/")

@app.get("/page")
async def html_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>Velithon Page</title></head>
    <body>
        <h1>Hello from Velithon!</h1>
        <p>This is an HTML response.</p>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run()
```

## See Also

- [Application API](application.md) - Main application class
- [Requests API](requests.md) - Request handling
- [Template Engine](../user-guide/templates.md) - Template responses
- [File Uploads](../user-guide/file-uploads.md) - File handling
- [Server-Sent Events](../user-guide/sse.md) - Real-time responses

## Automatic Response Serialization

Velithon automatically detects and serializes common Python objects to JSON responses, eliminating the need to manually wrap objects in `JSONResponse` or `JSONResponse`.

### Supported Objects

The framework automatically serializes:
- **Pydantic models** - Uses `JSONResponse` for better performance
- **Dataclasses** - Uses `JSONResponse` for structured data
- **Dictionaries and lists** - Uses `JSONResponse` for large collections (>50 items), `JSONResponse` for smaller ones
- **Basic types** - `str`, `int`, `float`, `bool`, `None`
- **Custom objects** - With `__json__()`, `model_dump()`, `dict()`, or `__dict__` methods

### Examples

```python
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel

@dataclass
class UserData:
    id: int
    name: str
    created_at: datetime

class User(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True

@app.get("/user/{user_id}")
async def get_user(user_id: int):
    # Returns Pydantic model - automatically uses JSONResponse
    return User(id=user_id, name="John Doe", email="john@example.com")

@app.get("/user-data/{user_id}")
async def get_user_data(user_id: int):
    # Returns dataclass - automatically uses JSONResponse
    return UserData(id=user_id, name="Jane Doe", created_at=datetime.utcnow())

@app.get("/simple-data")
async def get_simple_data():
    # Returns dict - automatically uses JSONResponse (small size)
    return {"message": "Hello", "status": "success"}

@app.get("/large-data")
async def get_large_data():
    # Returns large dict - automatically uses JSONResponse
    return {"items": [{"id": i, "name": f"Item {i}"} for i in range(100)]}

@app.get("/mixed-data")
async def get_mixed_data():
    # Returns list of mixed objects - automatically serialized
    return [
        {"type": "dict", "data": {"key": "value"}},
        User(id=1, name="Alice", email="alice@example.com"),
        UserData(id=2, name="Bob", created_at=datetime.utcnow())
    ]
```

### Custom Serialization

Objects can provide custom serialization methods:

```python
class CustomObject:
    def __init__(self, value: str):
        self.value = value
    
    def __json__(self):
        return {"custom_value": self.value, "type": "custom"}

@app.get("/custom")
async def get_custom():
    # Uses custom __json__ method
    return CustomObject("example")
```

### Backward Compatibility

Existing code continues to work unchanged:

```python
@app.get("/explicit-response")
async def explicit_response():
    # Still works - response objects are returned as-is
    return JSONResponse({"message": "explicit"})

@app.get("/mixed-return")
async def mixed_return():
    if some_condition:
        return JSONResponse({"type": "explicit"})
    else:
        return {"type": "automatic"}  # Auto-serialized
```

### Performance Optimization

The framework automatically chooses the optimal response type:
- **Simple objects** (dicts <50 items, basic types) → `JSONResponse`
- **Complex objects** (Pydantic models, dataclasses, large collections) → `JSONResponse`
- **Response objects** → Returned unchanged
