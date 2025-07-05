# Requests API Reference

The `Request` object provides access to incoming HTTP request data including headers, query parameters, path parameters, body content, and connection information.

## Class: Request

```python
from velithon.requests import Request

# Request objects are automatically provided to route handlers
@app.get("/example")
async def handler(request: Request):
    # Access request data
    pass
```

## Properties

### method

```python
@property
def method() -> str
```

The HTTP method of the request (GET, POST, PUT, DELETE, etc.).

**Example:**
```python
@app.route("/items", methods=["GET", "POST"])
async def item_handler(request: Request):
    if request.method == "GET":
        return {"action": "list"}
    elif request.method == "POST":
        return {"action": "create"}
```

### url

```python
@property
def url() -> URL
```

The complete URL of the request including scheme, host, port, path, and query string.

**Example:**
```python
@app.get("/info")
async def get_url_info(request: Request):
    return {
        "url": str(request.url),
        "scheme": request.url.scheme,
        "hostname": request.url.hostname,
        "port": request.url.port,
        "path": request.url.path,
        "query": request.url.query
    }
```

### headers

```python
@property
def headers() -> Headers
```

Case-insensitive dictionary-like object containing request headers.

**Example:**
```python
@app.get("/headers")
async def get_headers(request: Request):
    auth_header = request.headers.get("authorization")
    content_type = request.headers.get("content-type")
    user_agent = request.headers.get("user-agent")
    
    # Check if header exists
    has_api_key = "x-api-key" in request.headers
    
    # Get all headers
    all_headers = dict(request.headers)
    
    return {
        "auth": auth_header,
        "content_type": content_type,
        "user_agent": user_agent,
        "has_api_key": has_api_key,
        "all_headers": all_headers
    }
```

### query_params

```python
@property
def query_params() -> QueryParams
```

Dictionary-like object containing query string parameters.

**Example:**
```python
@app.get("/search")
async def search(request: Request):
    # Get single parameter
    query = request.query_params.get("q", "")
    
    # Get with default value
    limit = int(request.query_params.get("limit", "10"))
    
    # Get multiple values for same parameter
    tags = request.query_params.getlist("tag")
    
    # Get all parameters
    all_params = dict(request.query_params)
    
    return {
        "query": query,
        "limit": limit,
        "tags": tags,
        "all_params": all_params
    }
```

### path_params

```python
@property
def path_params() -> dict[str, Any]
```

Dictionary containing path parameters extracted from the URL pattern.

**Example:**
```python
@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(request: Request):
    user_id = request.path_params["user_id"]
    post_id = request.path_params["post_id"]
    
    return {
        "user_id": user_id,
        "post_id": post_id
    }

# With type conversion
@app.get("/items/{item_id:int}")
async def get_item(request: Request):
    item_id: int = request.path_params["item_id"]  # Already converted to int
    return {"item_id": item_id, "type": type(item_id).__name__}
```

### cookies

```python
@property
def cookies() -> dict[str, str]
```

Dictionary containing request cookies.

**Example:**
```python
@app.get("/profile")
async def get_profile(request: Request):
    session_id = request.cookies.get("session_id")
    user_preference = request.cookies.get("theme", "light")
    
    # Get all cookies
    all_cookies = request.cookies
    
    return {
        "session_id": session_id,
        "theme": user_preference,
        "all_cookies": all_cookies
    }
```

### client

```python
@property
def client() -> Address
```

Client connection information including host and port.

**Example:**
```python
@app.get("/client-info")
async def get_client_info(request: Request):
    return {
        "client_host": request.client.host,
        "client_port": request.client.port,
        "client_address": str(request.client)
    }
```

### state

```python
@property
def state() -> object
```

A state object for storing arbitrary data during request processing. Useful for middleware to store information.

**Example:**
```python
# In middleware
class TimingMiddleware:
    async def process_request(self, request: Request):
        request.state.start_time = time.time()
        return request

# In route handler
@app.get("/timing")
async def get_timing(request: Request):
    start_time = getattr(request.state, "start_time", None)
    if start_time:
        duration = time.time() - start_time
        return {"duration": duration}
    return {"duration": None}
```

## Body Methods

### body()

```python
async def body() -> bytes
```

Get the raw request body as bytes.

**Example:**
```python
@app.post("/raw-data")
async def handle_raw_data(request: Request):
    raw_body = await request.body()
    body_size = len(raw_body)
    
    return {
        "body_size": body_size,
        "content_type": request.headers.get("content-type")
    }
```

### json()

```python
async def json() -> Any
```

Parse the request body as JSON and return the parsed data.

**Example:**
```python
@app.post("/users")
async def create_user(request: Request):
    try:
        user_data = await request.json()
        
        # Validate required fields
        if "name" not in user_data:
            return {"error": "Name is required"}, 400
        
        return {"user": user_data}
    
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}, 400
```

### form()

```python
async def form() -> FormData
```

Parse form data from the request body.

**Example:**
```python
@app.post("/submit-form")
async def handle_form(request: Request):
    form_data = await request.form()
    
    # Get individual fields
    name = form_data.get("name")
    email = form_data.get("email")
    
    # Get all form fields
    all_fields = dict(form_data)
    
    return {
        "name": name,
        "email": email,
        "all_fields": all_fields
    }
```

### stream()

```python
async def stream() -> AsyncGenerator[bytes, None]
```

Stream the request body in chunks.

**Example:**
```python
@app.post("/upload-stream")
async def handle_stream(request: Request):
    total_size = 0
    chunk_count = 0
    
    async for chunk in request.stream():
        total_size += len(chunk)
        chunk_count += 1
        # Process chunk
    
    return {
        "total_size": total_size,
        "chunk_count": chunk_count
    }
```

## File Upload Handling

### Handling Single File Upload

```python
from velithon.datastructures import UploadFile

@app.post("/upload")
async def upload_file(request: Request):
    form = await request.form()
    file: UploadFile = form.get("file")
    
    if not file:
        return {"error": "No file uploaded"}, 400
    
    # Read file content
    content = await file.read()
    
    # Or save to disk
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(content)
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content)
    }
```

### Handling Multiple File Uploads

```python
@app.post("/upload-multiple")
async def upload_multiple(request: Request):
    form = await request.form()
    uploaded_files = []
    
    # Get all files
    for key, value in form.items():
        if isinstance(value, UploadFile):
            content = await value.read()
            uploaded_files.append({
                "field_name": key,
                "filename": value.filename,
                "content_type": value.content_type,
                "size": len(content)
            })
    
    return {"uploaded_files": uploaded_files}
```

## Advanced Usage

### Content Type Detection

```python
@app.post("/auto-parse")
async def auto_parse(request: Request):
    content_type = request.headers.get("content-type", "")
    
    if content_type.startswith("application/json"):
        data = await request.json()
        return {"type": "json", "data": data}
    
    elif content_type.startswith("application/x-www-form-urlencoded"):
        data = await request.form()
        return {"type": "form", "data": dict(data)}
    
    elif content_type.startswith("multipart/form-data"):
        data = await request.form()
        files = []
        fields = {}
        
        for key, value in data.items():
            if isinstance(value, UploadFile):
                files.append(key)
            else:
                fields[key] = value
        
        return {"type": "multipart", "fields": fields, "files": files}
    
    else:
        body = await request.body()
        return {"type": "raw", "size": len(body)}
```

### Request Validation

```python
from pydantic import BaseModel, ValidationError

class UserCreateRequest(BaseModel):
    name: str
    email: str
    age: int

@app.post("/users-validated")
async def create_user_validated(request: Request):
    try:
        # Parse JSON and validate
        raw_data = await request.json()
        user_data = UserCreateRequest(**raw_data)
        
        # Use validated data
        return {"user": user_data.dict()}
    
    except ValidationError as e:
        return {"error": "Validation failed", "details": e.errors()}, 400
    
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}, 400
```

### Request Context and Middleware

```python
class AuthMiddleware:
    async def process_request(self, request: Request):
        token = request.headers.get("authorization")
        
        if token and token.startswith("Bearer "):
            # Validate token and set user
            user = validate_token(token[7:])
            request.state.user = user
        
        return request

@app.get("/protected")
async def protected_route(request: Request):
    user = getattr(request.state, "user", None)
    
    if not user:
        return {"error": "Unauthorized"}, 401
    
    return {"message": f"Hello, {user.name}!"}
```

### Request Scope Access

```python
@app.get("/scope-info")
async def get_scope_info(request: Request):
    # Access raw RSGI scope
    scope = request.scope
    
    return {
        "type": scope["type"],
        "method": scope["method"],
        "path": scope["path"],
        "query_string": scope["query_string"].decode(),
        "headers": dict(scope["headers"]),
        "server": scope.get("server"),
        "client": scope.get("client")
    }
```

## Helper Classes

### URL

```python
from velithon.datastructures import URL

url = request.url
# Properties: scheme, hostname, port, path, query, fragment
# Methods: replace(), include_query_params(), exclude_query_params()
```

### Headers

```python
from velithon.datastructures import Headers

headers = request.headers
# Case-insensitive dictionary-like access
# Methods: get(), getlist(), items(), keys(), values()
```

### QueryParams

```python
from velithon.datastructures import QueryParams

params = request.query_params
# Methods: get(), getlist(), items(), keys(), values()
```

### FormData

```python
from velithon.datastructures import FormData

form = await request.form()
# Dictionary-like access with file upload support
# Methods: get(), getlist(), items(), keys(), values()
```

### UploadFile

```python
from velithon.datastructures import UploadFile

# Properties: filename, content_type, file, size
# Methods: read(), seek(), close()
```

## Complete Example

```python
from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse
from velithon.datastructures import UploadFile
import json

app = Velithon()

@app.post("/comprehensive-handler")
async def comprehensive_handler(request: Request):
    """Comprehensive request handling example."""
    
    # Basic request info
    info = {
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "client": str(request.client)
    }
    
    # Headers
    info["headers"] = {
        "content_type": request.headers.get("content-type"),
        "user_agent": request.headers.get("user-agent"),
        "authorization": request.headers.get("authorization") is not None
    }
    
    # Query parameters
    info["query_params"] = dict(request.query_params)
    
    # Path parameters
    info["path_params"] = request.path_params
    
    # Cookies
    info["cookies"] = dict(request.cookies)
    
    # Body handling based on content type
    content_type = request.headers.get("content-type", "")
    
    try:
        if content_type.startswith("application/json"):
            info["body"] = await request.json()
            info["body_type"] = "json"
        
        elif content_type.startswith("application/x-www-form-urlencoded"):
            form_data = await request.form()
            info["body"] = dict(form_data)
            info["body_type"] = "form"
        
        elif content_type.startswith("multipart/form-data"):
            form_data = await request.form()
            
            files_info = []
            form_fields = {}
            
            for key, value in form_data.items():
                if isinstance(value, UploadFile):
                    files_info.append({
                        "field": key,
                        "filename": value.filename,
                        "content_type": value.content_type,
                        "size": len(await value.read())
                    })
                else:
                    form_fields[key] = value
            
            info["body"] = {
                "fields": form_fields,
                "files": files_info
            }
            info["body_type"] = "multipart"
        
        else:
            body = await request.body()
            info["body"] = {
                "size": len(body),
                "content": body.decode("utf-8", errors="ignore")[:100] + "..." if body else ""
            }
            info["body_type"] = "raw"
    
    except Exception as e:
        info["body_error"] = str(e)
    
    return JSONResponse(info)

# Path parameters example
@app.get("/users/{user_id}/posts/{post_id:int}")
async def get_user_post(request: Request):
    return {
        "user_id": request.path_params["user_id"],
        "post_id": request.path_params["post_id"],
        "post_id_type": type(request.path_params["post_id"]).__name__
    }

if __name__ == "__main__":
    app.run()
```

## See Also

- [Application API](application.md) - Main application class
- [Responses API](responses.md) - Response handling
- [File Uploads Guide](../user-guide/file-uploads.md) - File upload handling
