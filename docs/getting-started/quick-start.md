# Quick Start

<div class="performance-box">
🚀 <strong>Fast Track to Velithon Mastery!</strong><br>
Let's build your first Velithon application! This guide will take you from zero to a running RSGI web server in just a few minutes.
</div>

## 🎯 What We'll Build

<div class="grid cards">
<div markdown>
**🌐 Welcome Endpoint**
- Simple GET route
- JSON response handling
- Basic application structure
</div>
<div markdown>
**👤 User Information**
- Path parameters
- Dynamic responses
- Error handling
</div>
<div markdown>
**📊 JSON Optimization**
- Optimized responses
- Performance features
- Real-world examples
</div>
<div markdown>
**🔧 Error Handling**
- HTTP exceptions
- Custom error responses
- Best practices
</div>
</div>

!!! tip "Interactive Features"
    This page includes enhanced code blocks with:
    
    - **Copy to clipboard** buttons
    - **Syntax highlighting** with enhanced colors
    - **Line numbers** for longer code blocks
    - **Expand/collapse** for better readability

## 📝 Step 1: Create Your First App

Create a new file called `main.py`:

```python title="main.py" hl_lines="4 11 18"
from velithon import Velithon
from velithon.responses import JSONResponse

# Create the Velithon application instance
app = Velithon(
    title="My First Velithon App",
    description="A sample application built with Velithon RSGI framework",
    version="1.0.0"
)

# Define a simple GET endpoint
@app.get("/")
async def root():
    """Welcome endpoint with enhanced JSON response."""
    return JSONResponse({
        "message": "Welcome to Velithon!",
        "version": "1.0.0",
        "features": [
            "High Performance RSGI",
            "Rust-powered JSON serialization",
            "Async/await support",
            "Type safety"
        ]
    })

# Define an endpoint with path parameters
@app.get("/hello/{name}")
async def say_hello(name: str):
    """Personalized greeting endpoint with validation."""
    if not name.isalpha():
        return JSONResponse(
            {"error": "Name must contain only letters"},
            status_code=400
        )
    
    return JSONResponse({
        "message": f"Hello, {name}!",
        "timestamp": "2025-07-04T12:00:00Z",
        "greeting_id": hash(name) % 10000
    })

# Define a POST endpoint with request body
@app.post("/items")
async def create_item(item: dict):
    """Create a new item with enhanced response."""
    # Basic validation
    if not item.get("name"):
        return JSONResponse(
            {"error": "Item name is required"},
            status_code=400
        )
    
    # Simulate item creation
    created_item = {
        "id": hash(str(item)) % 100000,
        "name": item["name"],
        "description": item.get("description", "No description"),
        "created_at": "2025-07-04T12:00:00Z",
        "status": "active"
    }
    
    return JSONResponse({
        "message": "Item created successfully",
        "item": created_item
    }, status_code=201)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check with system information."""
    return JSONResponse({"status": "healthy", "service": "velithon-app"})
```

That's it! You've created a complete Velithon RSGI application with multiple endpoints.

## 🚀 Step 2: Run Your Application

Now let's run your application using the Velithon CLI with Granian RSGI server:

```bash
velithon run --app main:app --host 127.0.0.1 --port 8000
```

You should see output similar to:

```
INFO:     Started Velithon application
INFO:     Granian RSGI server running on http://127.0.0.1:8000
INFO:     Press CTRL+C to quit
```

!!! note "RSGI vs ASGI"
    Velithon uses RSGI (Rust Server Gateway Interface) protocol through Granian, not ASGI. This provides superior performance compared to traditional ASGI servers like uvicorn.

## 🧪 Step 3: Test Your Endpoints

Let's test each endpoint to make sure everything works:

### Test the root endpoint

Open your browser and visit: `http://127.0.0.1:8000`

You should see:
```json
{
  "message": "Welcome to Velithon!", 
  "version": "1.0.0"
}
```

### Test the personalized greeting

Visit: `http://127.0.0.1:8000/hello/John`

You should see:
```json
{
  "message": "Hello, John!"
}
```

### Test the health check

Visit: `http://127.0.0.1:8000/health`

You should see:
```json
{
  "status": "healthy", 
  "service": "velithon-app"
}
```

### Test the POST endpoint

Using curl:

```bash
curl -X POST "http://127.0.0.1:8000/items" \
     -H "Content-Type: application/json" \
     -d '{"name": "laptop", "price": 999.99}'
```

You should see:
```json
{
  "message": "Item created successfully",
  "item": {
    "name": "laptop",
    "price": 999.99
  }
}
```

## 📊 Step 4: Add Request Validation with Pydantic

Let's improve our application by adding proper request validation using Pydantic models:

```python title="main.py"
from velithon import Velithon
from velithon.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

app = Velithon(
    title="My First Velithon App",
    description="A sample application built with Velithon RSGI framework",
    version="1.0.0"
)

# Define Pydantic models for request/response validation
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    total_price: float

@app.get("/")
async def root():
    """Welcome endpoint."""
    return JSONResponse({"message": "Welcome to Velithon!", "version": "1.0.0"})

@app.get("/hello/{name}")
async def say_hello(name: str):
    """Personalized greeting endpoint."""
    return JSONResponse({"message": f"Hello, {name}!"})

@app.post("/items")
async def create_item(item: Item):
    """Create a new item with validation."""
    # Calculate total price
    total_price = item.price
    if item.tax:
        total_price += item.price * (item.tax / 100)
    
    # Simulate item creation with auto-generated ID
    item_id = 12345
    
    response_data = ItemResponse(
        id=item_id,
        name=item.name,
        price=item.price,
        total_price=total_price
    )
    
    return JSONResponse(response_data.dict())

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "velithon-app"})
```

Now test the improved POST endpoint:

```bash
curl -X POST "http://127.0.0.1:8000/items" \
     -H "Content-Type: application/json" \
     -d '{"name": "laptop", "price": 999.99, "tax": 8.5}'
```

Response:
```json
{
  "id": 12345,
  "name": "laptop", 
  "price": 999.99,
  "total_price": 1084.99
}
```

## 🎨 Step 5: Add Error Handling

Let's add proper error handling to make our API more robust:

```python title="main.py"
from velithon import Velithon
from velithon.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import Optional

app = Velithon(
    title="My First Velithon App", 
    description="A sample application built with Velithon RSGI framework",
    version="1.0.0"
)

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
    
    @validator('tax')
    def tax_must_be_valid(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Tax must be between 0 and 100')
        return v

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    total_price: float

@app.get("/")
async def root():
    """Welcome endpoint."""
    return JSONResponse({"message": "Welcome to Velithon!", "version": "1.0.0"})

@app.get("/hello/{name}")
async def say_hello(name: str):
    """Personalized greeting endpoint."""
    if len(name) < 2:
        return JSONResponse(
            content={"error": "Name must be at least 2 characters long"},
            status_code=400
        )
    return JSONResponse({"message": f"Hello, {name}!"})

@app.post("/items")
async def create_item(item: Item):
    """Create a new item with validation."""
    try:
        # Calculate total price
        total_price = item.price
        if item.tax:
            total_price += item.price * (item.tax / 100)
        
        # Simulate item creation
        item_id = 12345
        
        response_data = ItemResponse(
            id=item_id,
            name=item.name,
            price=item.price,
            total_price=total_price
        )
        
        return JSONResponse(response_data.dict())
    except Exception as e:
        return JSONResponse(
            content={"error": "Failed to create item", "detail": str(e)},
            status_code=500
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "velithon-app"})
```

## 🔧 Step 6: Velithon CLI Options

Explore different ways to run your Velithon application with the powerful CLI:

```bash
# Basic run with Granian RSGI server
velithon run --app main:app

# With custom host and port
velithon run --app main:app --host 0.0.0.0 --port 8080

# With multiple workers for production
velithon run --app main:app --workers 4

# With debug logging
velithon run --app main:app --log-level DEBUG

# With custom log file
velithon run --app main:app --log-file myapp.log --log-to-file

# Enable auto-reload for development
velithon run --app main:app --reload

# Advanced RSGI/Granian options
velithon run --app main:app --http 2 --runtime-mode mt --loop rloop

# With SSL/TLS support
velithon run --app main:app --ssl-certificate cert.pem --ssl-keyfile key.pem
```

Key CLI features:
- Built-in **Granian RSGI server** (faster than ASGI)
- HTTP/1.1 and **HTTP/2 support**
- **Multi-threading** and **async event loops** (asyncio, uvloop, rloop)
- **Auto-reload** for development
- **SSL/TLS termination**
- **Comprehensive logging** options

## 📈 Performance Test

Let's see how fast your Velithon RSGI app is! Install a simple benchmarking tool:

```bash
pip install httpx
```

Create a quick performance test:

```python title="test_performance.py"
import asyncio
import httpx
import time

async def test_performance():
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        
        # Send 1000 concurrent requests to test RSGI performance
        tasks = []
        for _ in range(1000):
            task = client.get("http://127.0.0.1:8000/")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"1000 requests completed in {duration:.2f} seconds")
        print(f"Requests per second: {1000/duration:.2f}")
        print(f"All responses successful: {all(r.status_code == 200 for r in responses)}")
        print("Velithon RSGI performance test completed!")

if __name__ == "__main__":
    asyncio.run(test_performance())
```

Run the performance test:

```bash
python test_performance.py
```

!!! success "RSGI Performance"
    Velithon with Granian RSGI typically achieves **~70,000 requests/second** for simple endpoints, significantly outperforming traditional ASGI frameworks.

## 🎉 Congratulations!

You've successfully created your first Velithon application! You now know how to:

- ✅ Create a Velithon application
- ✅ Define HTTP endpoints with different methods
- ✅ Handle path parameters
- ✅ Use Pydantic models for validation
- ✅ Add error handling
- ✅ Run your application with the CLI
- ✅ Test your endpoints

## 🔄 What's Next?

Ready to dive deeper? Here are your next steps:

<div class="grid cards" markdown>

-   **[Core Concepts](../user-guide/core-concepts.md)**
    
    Understand Velithon's architecture and design principles

-   **[HTTP Features](../user-guide/http-endpoints.md)**
    
    Master advanced HTTP features like file uploads, middleware, and response types

-   **[Examples](../examples/index.md)**
    
    Explore real-world application examples

</div>

**[Build Your First Real Application →](../user-guide/core-concepts.md)**
