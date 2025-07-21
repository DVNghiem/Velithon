# Custom Request ID Generation

Velithon allows you to customize how request IDs are generated for your application. By default, Velithon uses an efficient built-in request ID generator, but you can provide your own custom function to generate request IDs based on your specific requirements.

## Overview

Request IDs are unique identifiers assigned to each incoming HTTP request. They are useful for:
- Request tracing and logging
- Correlation across distributed systems
- Debugging and monitoring
- Audit trails

## Default Request ID Generation

By default, Velithon generates request IDs using an efficient generator that creates IDs in the format:
```
{prefix}-{timestamp}-{counter}
```

Example: `377-1753029395336-00001`

Where:
- `prefix`: Random 3-digit number generated at startup
- `timestamp`: Current timestamp in milliseconds
- `counter`: Sequential counter (resets every 100,000 requests)

## Custom Request ID Generation

You can provide a custom request ID generator function when creating your Velithon application:

### Basic Usage

```python
from velithon import Velithon, Request, JSONResponse

def custom_request_id_generator(request):
    """Custom request ID generator."""
    return f"custom-{request.method.lower()}-{hash(request.path) % 10000}"

app = Velithon(request_id_generator=custom_request_id_generator)

@app.get("/users/{user_id}")
async def get_user(request: Request):
    return JSONResponse({
        "request_id": request.request_id,
        "user_id": request.path_params["user_id"]
    })
```

### Using Header-Based Request IDs

A common pattern is to use correlation IDs from request headers:

```python
def header_based_request_id(request):
    """Generate request ID based on correlation header."""
    correlation_id = request.headers.get('x-correlation-id')
    if correlation_id:
        return f"corr-{correlation_id}"
    
    # Fallback to a custom format
    return f"req-{request.method.lower()}-{hash(request.path) % 100000}"

app = Velithon(request_id_generator=header_based_request_id)
```

### Advanced Custom Generator

```python
import uuid
import time

def advanced_request_id_generator(request):
    """Advanced request ID generator with multiple strategies."""
    
    # Strategy 1: Use trace ID from distributed tracing headers
    trace_id = request.headers.get('x-trace-id')
    if trace_id:
        return f"trace-{trace_id}"
    
    # Strategy 2: Use client-provided request ID
    client_request_id = request.headers.get('x-request-id')
    if client_request_id:
        return f"client-{client_request_id}"
    
    # Strategy 3: Generate UUID-based ID for specific paths
    if request.path.startswith('/api/v1/'):
        return f"api-{str(uuid.uuid4())[:8]}"
    
    # Strategy 4: Time-based ID with client info
    timestamp = int(time.time() * 1000)
    client_hash = hash(request.client) % 1000
    return f"req-{timestamp}-{client_hash}"

app = Velithon(request_id_generator=advanced_request_id_generator)
```

## Request Context Object

The request context object passed to your custom generator provides access to:

### Properties

- `request.headers`: Dictionary-like access to request headers
- `request.method`: HTTP method (GET, POST, etc.)
- `request.path`: Request path
- `request.client`: Client IP address
- `request.query_params`: Query parameters

### Example Usage

```python
def detailed_request_id_generator(request):
    """Generate detailed request ID using multiple request properties."""
    
    # Extract information from the request
    method = request.method.upper()
    path_hash = abs(hash(request.path)) % 10000
    client_hash = abs(hash(request.client)) % 1000
    
    # Check for special headers
    service_name = request.headers.get('x-service-name', 'unknown')
    version = request.headers.get('x-api-version', 'v1')
    
    return f"{service_name}-{version}-{method}-{path_hash}-{client_hash}"

app = Velithon(request_id_generator=detailed_request_id_generator)
```

## Context Management System

Velithon provides a Flask-style context management system for accessing application and request contexts:

### Application Context

```python
from velithon.ctx import current_app, has_app_context

# Check if we're in an application context
if has_app_context():
    app_title = current_app.title
    print(f"Current app: {app_title}")
```

### Request Context

```python
from velithon.ctx import request, g, has_request_context

# Access current request (only available during request processing)
if has_request_context():
    request_id = request.request_id
    method = request.method
    
    # Store data in the request context
    g.user_id = 123
    g.start_time = time.time()
```

### Context Proxies

Velithon provides convenient proxy objects that automatically resolve to the current context:

```python
from velithon.ctx import current_app, request, g

# These work automatically within the appropriate contexts
print(current_app.title)  # Current application
print(request.request_id)  # Current request
g.custom_data = "value"   # Request-local storage
```

## Middleware Integration

If you need more complex request ID logic, you can create custom middleware:

```python
from velithon.middleware.base import BaseHTTPMiddleware

class CustomRequestIDMiddleware(BaseHTTPMiddleware):
    async def process_http_request(self, scope, protocol):
        # Custom logic before request processing
        if scope._request_id.startswith('default-'):
            # Override default request ID
            scope._request_id = f"override-{int(time.time())}"
        
        await self.app(scope, protocol)

app = Velithon(
    middleware=[
        Middleware(CustomRequestIDMiddleware)
    ]
)
```

## Performance Considerations

- **Function Overhead**: Custom request ID generators are called for every request. Keep the logic fast and simple.
- **Memory Usage**: Avoid creating large objects or storing state in the generator function.
- **Thread Safety**: The generator function should be thread-safe if you're using multiple workers.
- **Error Handling**: If your generator raises an exception, Velithon will fall back to the default generator.

### Performance Best Practices

```python
import threading

# Pre-compile regex patterns
CORRELATION_PATTERN = re.compile(r'^[a-f0-9-]{36}$')

# Use thread-local storage for expensive operations
_local = threading.local()

def optimized_request_id_generator(request):
    """Performance-optimized request ID generator."""
    
    # Fast path: check for correlation ID
    correlation_id = request.headers.get('x-correlation-id')
    if correlation_id and CORRELATION_PATTERN.match(correlation_id):
        return f"corr-{correlation_id}"
    
    # Fallback: use cached generator
    if not hasattr(_local, 'counter'):
        _local.counter = 0
        _local.prefix = random.randint(100, 999)
    
    _local.counter = (_local.counter + 1) % 100000
    return f"opt-{_local.prefix}-{_local.counter:05d}"

app = Velithon(request_id_generator=optimized_request_id_generator)
```

## Error Handling

If your custom request ID generator raises an exception, Velithon will automatically fall back to the default generator and log the error:

```python
def failing_request_id_generator(request):
    """Example of a generator that might fail."""
    
    # This might raise an exception
    external_id = request.headers['required-header']  # KeyError if missing
    return f"ext-{external_id}"

# Velithon will handle the exception gracefully
app = Velithon(request_id_generator=failing_request_id_generator)
```

## Complete Example

Here's a complete example showing a production-ready custom request ID system:

```python
import re
import time
import uuid
from velithon import Velithon, Request, JSONResponse
from velithon.ctx import request, g

# Compile regex patterns once
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
CORRELATION_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')

def production_request_id_generator(req):
    """Production-ready request ID generator with multiple fallbacks."""
    
    try:
        # Priority 1: Distributed tracing ID
        trace_id = req.headers.get('x-trace-id')
        if trace_id and UUID_PATTERN.match(trace_id):
            return f"trace-{trace_id}"
        
        # Priority 2: Client correlation ID
        correlation_id = req.headers.get('x-correlation-id')
        if correlation_id and CORRELATION_PATTERN.match(correlation_id) and len(correlation_id) <= 64:
            return f"corr-{correlation_id}"
        
        # Priority 3: Generate UUID for API endpoints
        if req.path.startswith('/api/'):
            return f"api-{str(uuid.uuid4())}"
        
        # Fallback: Custom format
        timestamp = int(time.time() * 1000)
        path_hash = abs(hash(req.path)) % 10000
        return f"req-{timestamp}-{path_hash}"
        
    except Exception:
        # Ultimate fallback: simple timestamp
        return f"fallback-{int(time.time() * 1000)}"

# Create application with custom request ID generator
app = Velithon(
    title="Production API",
    request_id_generator=production_request_id_generator
)

@app.get("/api/users/{user_id}")
async def get_user(req: Request):
    """Get user endpoint with request tracing."""
    
    # Access request ID through the request object
    request_id = req.request_id
    user_id = req.path_params["user_id"]
    
    # Store request info in context for later use
    g.request_start = time.time()
    g.user_id = user_id
    
    return JSONResponse({
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": time.time()
    })

@app.middleware("http")
async def logging_middleware(req: Request, call_next):
    """Middleware to log requests with custom request IDs."""
    
    start_time = time.time()
    response = await call_next(req)
    duration = time.time() - start_time
    
    print(f"Request {req.request_id}: {req.method} {req.url.path} - {duration:.3f}s")
    return response

if __name__ == "__main__":
    app.run()
```

This system provides robust, production-ready request ID generation with proper fallbacks and error handling.
