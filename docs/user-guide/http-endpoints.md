# HTTP Endpoints

Velithon provides a comprehensive system for handling HTTP requests and responses with type safety, validation, and automatic OpenAPI documentation generation.

## HTTP Methods

Velithon supports all standard HTTP methods with dedicated decorators:

```python
from velithon import Velithon
from velithon.requests import Request
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/items")
async def list_items():
    return {"items": []}

@app.post("/items")
async def create_item(request: Request):
    item_data = await request.json()
    return {"item": item_data}

@app.put("/items/{item_id}")
async def update_item(request: Request):
    item_id = request.path_params["item_id"]
    item_data = await request.json()
    return {"item_id": item_id, "item": item_data}

@app.patch("/items/{item_id}")
async def partial_update_item(request: Request):
    item_id = request.path_params["item_id"]
    updates = await request.json()
    return {"item_id": item_id, "updates": updates}

@app.delete("/items/{item_id}")
async def delete_item(request: Request):
    item_id = request.path_params["item_id"]
    return {"deleted": item_id}

@app.head("/items/{item_id}")
async def check_item_exists(request: Request):
    # HEAD requests should return headers only (no body)
    return JSONResponse({}, headers={"X-Item-Exists": "true"})

@app.options("/items")
async def item_options():
    return JSONResponse({}, headers={
        "Allow": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    })
```

## Route Parameters

### Path Parameters

Velithon supports typed path parameters with automatic conversion:

```python
@app.get("/users/{user_id:int}")
async def get_user(request: Request):
    user_id: int = request.path_params["user_id"]  # Already converted to int
    return {"user_id": user_id}

@app.get("/files/{file_path:path}")
async def get_file(request: Request):
    file_path: str = request.path_params["file_path"]  # Preserves slashes
    return {"file_path": file_path}

@app.get("/products/{product_id:uuid}")
async def get_product(request: Request):
    product_id = request.path_params["product_id"]  # UUID object
    return {"product_id": str(product_id)}

# Custom converters
@app.get("/categories/{slug:slug}")
async def get_category(request: Request):
    slug: str = request.path_params["slug"]  # Validates slug format
    return {"category": slug}
```

### Query Parameters

Access query parameters through the request object:

```python
@app.get("/search")
async def search_items(request: Request):
    # Get single query parameter
    query = request.query_params.get("q", "")
    
    # Get with type conversion
    limit = int(request.query_params.get("limit", "10"))
    offset = int(request.query_params.get("offset", "0"))
    
    # Get multiple values for same parameter
    tags = request.query_params.getlist("tag")
    
    # Get all query parameters
    all_params = dict(request.query_params)
    
    return {
        "query": query,
        "limit": limit,
        "offset": offset,
        "tags": tags,
        "all_params": all_params
    }
```

### Header Parameters

Access request headers:

```python
@app.get("/protected")
async def protected_endpoint(request: Request):
    # Get authorization header
    auth_header = request.headers.get("authorization")
    
    # Get custom headers
    api_key = request.headers.get("x-api-key")
    
    # Get with default value
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Check if header exists
    has_custom_header = "x-custom-header" in request.headers
    
    return {
        "auth_header": auth_header,
        "api_key": api_key,
        "user_agent": user_agent,
        "has_custom_header": has_custom_header
    }
```

## Request Body Handling

### JSON Requests

Handle JSON request bodies with automatic parsing:

```python
@app.post("/users")
async def create_user(request: Request):
    try:
        user_data = await request.json()
        
        # Validate required fields
        if "name" not in user_data:
            raise ValueError("Name is required")
        
        # Process the user data
        return {"user": user_data, "id": 123}
    
    except ValueError as e:
        return JSONResponse(
            {"error": str(e)}, 
            status_code=400
        )
```

### Form Data

Handle form submissions:

```python
@app.post("/submit-form")
async def handle_form(request: Request):
    # Parse form data
    form_data = await request.form()
    
    # Get individual fields
    name = form_data.get("name")
    email = form_data.get("email")
    
    # Get all form fields
    all_fields = dict(form_data)
    
    return {"name": name, "email": email, "all_fields": all_fields}
```

### File Uploads

Handle file uploads with multipart forms:

```python
from velithon.datastructures import UploadFile

@app.post("/upload")
async def upload_file(request: Request):
    form_data = await request.form()
    
    # Get uploaded file
    file: UploadFile = form_data.get("file")
    
    if file:
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
    
    return {"error": "No file uploaded"}, 400
```

### Raw Body

Access raw request body:

```python
@app.post("/webhook")
async def webhook_handler(request: Request):
    # Get raw bytes
    raw_body = await request.body()
    
    # Get as string
    body_str = (await request.body()).decode("utf-8")
    
    # Process webhook payload
    return {"received": len(raw_body)}
```

## Response Types

Velithon provides multiple response types for different use cases:

### JSON Responses

```python
from velithon.responses import JSONResponse, JSONResponse

@app.get("/data")
async def get_data():
    # Standard JSON response
    return JSONResponse({"message": "Hello, World!"})

@app.get("/optimized-data")
async def get_optimized_data():
    # Rust-optimized JSON for better performance
    return JSONResponse({"large": "dataset", "items": list(range(1000))})

@app.get("/custom-status")
async def custom_status():
    return JSONResponse(
        {"error": "Not found"}, 
        status_code=404,
        headers={"X-Custom": "value"}
    )
```

### HTML Responses

```python
from velithon.responses import HTMLResponse

@app.get("/page")
async def get_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>My Page</title></head>
    <body><h1>Hello, World!</h1></body>
    </html>
    """
    return HTMLResponse(html_content)

@app.get("/template")
async def render_template():
    # Using template engine
    from velithon.templates import TemplateEngine
    
    engine = TemplateEngine("templates/")
    return engine.render_response("page.html", {"title": "My Page"})
```

### File Responses

```python
from velithon.responses import FileResponse

@app.get("/download/{filename}")
async def download_file(request: Request):
    filename = request.path_params["filename"]
    
    return FileResponse(
        f"files/{filename}",
        media_type="application/octet-stream",
        filename=filename
    )

@app.get("/image/{image_id}")
async def get_image(request: Request):
    image_id = request.path_params["image_id"]
    
    return FileResponse(
        f"images/{image_id}.jpg",
        media_type="image/jpeg"
    )
```

### Streaming Responses

```python
from velithon.responses import StreamingResponse
import asyncio

@app.get("/stream")
async def stream_data():
    async def generate_data():
        for i in range(100):
            yield f"data chunk {i}\n"
            await asyncio.sleep(0.1)  # Simulate processing
    
    return StreamingResponse(
        generate_data(),
        media_type="text/plain"
    )

@app.get("/csv-export")
async def export_csv():
    async def generate_csv():
        yield "id,name,email\n"
        for i in range(1000):
            yield f"{i},User {i},user{i}@example.com\n"
            await asyncio.sleep(0.001)
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )
```

### Redirect Responses

```python
from velithon.responses import RedirectResponse

@app.get("/old-path")
async def old_endpoint():
    return RedirectResponse("/new-path", status_code=301)

@app.post("/login")
async def login(request: Request):
    # Login logic here
    login_data = await request.json()
    
    if login_successful:
        return RedirectResponse("/dashboard", status_code=303)
    else:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)
```

## Response Headers and Status Codes

### Custom Headers

```python
@app.get("/api-info")
async def api_info():
    return JSONResponse(
        {"version": "1.0.0"},
        headers={
            "X-API-Version": "1.0.0",
            "X-Rate-Limit": "1000",
            "Cache-Control": "max-age=3600"
        }
    )
```

### Status Codes

```python
from velithon.status import HTTP_201_CREATED, HTTP_404_NOT_FOUND

@app.post("/items")
async def create_item(request: Request):
    item_data = await request.json()
    # Create item logic
    return JSONResponse({"item": item_data}, status_code=HTTP_201_CREATED)

@app.get("/items/{item_id}")
async def get_item(request: Request):
    item_id = request.path_params["item_id"]
    # Fetch item logic
    item = None
    
    if not item:
        return JSONResponse(
            {"error": "Item not found"}, 
            status_code=HTTP_404_NOT_FOUND
        )
    
    return {"item": item}
```

## Request Validation

### Basic Validation

```python
@app.post("/users")
async def create_user(request: Request):
    try:
        user_data = await request.json()
        
        # Required field validation
        required_fields = ["name", "email"]
        for field in required_fields:
            if field not in user_data:
                return JSONResponse(
                    {"error": f"Missing required field: {field}"}, 
                    status_code=400
                )
        
        # Email validation
        email = user_data["email"]
        if "@" not in email:
            return JSONResponse(
                {"error": "Invalid email format"}, 
                status_code=400
            )
        
        return {"user": user_data}
    
    except Exception as e:
        return JSONResponse(
            {"error": "Invalid JSON"}, 
            status_code=400
        )
```

### Using Pydantic Models

```python
from pydantic import BaseModel, EmailStr, validator

class User(BaseModel):
    name: str
    email: EmailStr
    age: int
    
    @validator("age")
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError("Age must be between 0 and 150")
        return v

@app.post("/users")
async def create_user(request: Request):
    try:
        user_data = await request.json()
        user = User(**user_data)  # Automatic validation
        
        return {"user": user.dict()}
    
    except ValidationError as e:
        return JSONResponse(
            {"error": "Validation failed", "details": e.errors()}, 
            status_code=400
        )
```

## Content Negotiation

Handle different content types:

```python
@app.get("/data")
async def get_data(request: Request):
    accept_header = request.headers.get("accept", "application/json")
    
    data = {"message": "Hello, World!", "timestamp": "2025-01-01T00:00:00Z"}
    
    if "application/xml" in accept_header:
        xml_content = f"<data><message>{data['message']}</message></data>"
        return Response(xml_content, media_type="application/xml")
    
    elif "text/csv" in accept_header:
        csv_content = "field,value\nmessage,Hello World\n"
        return Response(csv_content, media_type="text/csv")
    
    else:
        return JSONResponse(data)
```

## Cookies

### Setting Cookies

```python
@app.post("/login")
async def login(request: Request):
    # Login logic
    response = JSONResponse({"message": "Logged in"})
    
    # Set simple cookie
    response.set_cookie("session_id", "abc123")
    
    # Set cookie with options
    response.set_cookie(
        "user_preference",
        "dark_mode",
        max_age=86400,  # 1 day
        secure=True,
        httponly=True,
        samesite="strict"
    )
    
    return response
```

### Reading Cookies

```python
@app.get("/profile")
async def get_profile(request: Request):
    # Get cookie value
    session_id = request.cookies.get("session_id")
    user_preference = request.cookies.get("user_preference", "light_mode")
    
    if not session_id:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    
    return {
        "session_id": session_id,
        "preference": user_preference
    }
```

## OpenAPI Documentation

Velithon automatically generates OpenAPI documentation for your endpoints:

```python
@app.get(
    "/users/{user_id}",
    summary="Get user by ID",
    description="Retrieve detailed information about a specific user",
    tags=["Users"],
    response_model=dict  # You can specify Pydantic models here
)
async def get_user(request: Request):
    """
    Get a user by their unique identifier.
    
    This endpoint returns detailed user information including:
    - Basic profile data
    - Account settings
    - Last login information
    """
    user_id = request.path_params["user_id"]
    return {"user_id": user_id, "name": "John Doe"}
```

The documentation will be automatically available at `/docs` (Swagger UI) and the OpenAPI schema at `/openapi.json`.

## Next Steps

- **[Request & Response](request-response.md)** - Deep dive into request/response handling
- **[Routing](routing.md)** - Advanced routing patterns
- **[File Uploads](file-uploads.md)** - Comprehensive file handling
- **[Error Handling](error-handling.md)** - Advanced error handling patterns
