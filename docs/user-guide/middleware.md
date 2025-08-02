# Middleware

Middleware in Velithon provides a way to process requests and responses as they flow through your application. It's a powerful mechanism for cross-cutting concerns like logging, authentication, CORS, compression, and more.

## Overview

Middleware in Velithon follows a simple pattern:

1. **Request Phase**: Process incoming requests
2. **Handler Phase**: Execute the route handler
3. **Response Phase**: Process outgoing responses

```mermaid
graph LR
    A[Request] --> B[Middleware 1] --> C[Middleware 2] --> D[Route Handler]
    D --> E[Middleware 2] --> F[Middleware 1] --> G[Response]
```

## Built-in Middleware

Velithon provides several built-in middleware components for common use cases:

### LoggingMiddleware

Logs all requests and responses with configurable options:

```python
from velithon.middleware import LoggingMiddleware

app = Velithon(
    middleware=[
        LoggingMiddleware(
            logger_name="velithon.access",
            log_format="json",
            include_headers=True,
            include_body=False
        )
    ]
)
```

**Configuration Options:**
- `logger_name`: Name of the logger to use
- `log_format`: Format for logs ("text" or "json")
- `include_headers`: Whether to log request headers
- `include_body`: Whether to log request/response bodies
- `exclude_paths`: List of paths to exclude from logging

### CORSMiddleware

Handles Cross-Origin Resource Sharing (CORS):

```python
from velithon.middleware import CORSMiddleware

app = Velithon(
    middleware=[
        CORSMiddleware(
            origins=["http://localhost:3000", "https://myapp.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
            max_age=3600
        )
    ]
)
```

**Configuration Options:**
- `origins`: List of allowed origins
- `allow_credentials`: Whether to allow credentials
- `allow_methods`: List of allowed HTTP methods
- `allow_headers`: List of allowed headers
- `expose_headers`: List of headers to expose
- `max_age`: Cache duration for preflight requests

### CompressionMiddleware

Compresses responses to reduce bandwidth:

```python
from velithon.middleware import CompressionMiddleware, CompressionLevel

app = Velithon(
    middleware=[
        CompressionMiddleware(
            compression_level=CompressionLevel.BALANCED,
            min_size=1024,
            content_types=["text/", "application/json", "application/xml"]
        )
    ]
)
```

**Configuration Options:**
- `compression_level`: Compression level (FAST, BALANCED, BEST)
- `min_size`: Minimum response size to compress (bytes)
- `content_types`: List of content types to compress
- `exclude_paths`: List of paths to exclude from compression

### SessionMiddleware

Manages user sessions with configurable backends:

```python
from velithon.middleware import SessionMiddleware, MemorySessionInterface

app = Velithon(
    middleware=[
        SessionMiddleware(
            secret_key="your-secret-key-here",
            session_interface=MemorySessionInterface(),
            max_age=3600,
            secure=False,
            http_only=True
        )
    ]
)
```

**Configuration Options:**
- `secret_key`: Secret key for session signing
- `session_interface`: Session storage backend
- `max_age`: Session lifetime in seconds
- `secure`: Whether to use secure cookies
- `http_only`: Whether to use HTTP-only cookies
- `same_site`: SameSite cookie policy

### AuthenticationMiddleware

Handles authentication and authorization:

```python
from velithon.middleware import AuthenticationMiddleware

app = Velithon(
    middleware=[
        AuthenticationMiddleware(
            exclude_paths=["/public", "/health"],
            on_auth_failure=lambda request: {"error": "Unauthorized"}
        )
    ]
)
```

**Configuration Options:**
- `exclude_paths`: List of paths to exclude from authentication
- `on_auth_failure`: Callback for authentication failures
- `auth_header`: Name of the authentication header

### PrometheusMiddleware

Collects metrics for monitoring and observability:

```python
from velithon.middleware import PrometheusMiddleware

app = Velithon(
    middleware=[
        PrometheusMiddleware(
            metrics_path="/metrics",
            include_http_requests_total=True,
            include_http_request_duration_seconds=True,
            include_http_request_size_bytes=True,
            include_http_response_size_bytes=True
        )
    ]
)
```

**Configuration Options:**
- `metrics_path`: Path to expose metrics
- `include_http_requests_total`: Whether to count total requests
- `include_http_request_duration_seconds`: Whether to measure request duration
- `include_http_request_size_bytes`: Whether to measure request size
- `include_http_response_size_bytes`: Whether to measure response size

### ProxyMiddleware

Acts as a reverse proxy with load balancing:

```python
from velithon.middleware import ProxyMiddleware

app = Velithon(
    middleware=[
        ProxyMiddleware(
            upstream_urls=["http://backend1:8000", "http://backend2:8000"],
            health_check_path="/health",
            circuit_breaker_threshold=5,
            timeout=30.0
        )
    ]
)
```

**Configuration Options:**
- `upstream_urls`: List of backend URLs
- `health_check_path`: Path for health checks
- `circuit_breaker_threshold`: Number of failures before circuit breaker opens
- `timeout`: Request timeout in seconds
- `load_balancing_strategy`: Strategy for load balancing

## Custom Middleware

### Basic Custom Middleware

Create custom middleware by extending `BaseHTTPMiddleware`:

```python
from velithon.middleware import BaseHTTPMiddleware
from velithon.requests import Request
from velithon.responses import Response
import time

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Add timing header
        duration = time.time() - start_time
        response.headers["X-Process-Time"] = f"{duration:.4f}s"
        
        return response

app = Velithon(middleware=[TimingMiddleware()])
```

### Conditional Middleware

Apply middleware conditionally:

```python
from velithon.middleware import ConditionalMiddleware

def is_api_request(request: Request) -> bool:
    return request.path.startswith("/api/")

app = Velithon(
    middleware=[
        ConditionalMiddleware(
            LoggingMiddleware(),
            condition=is_api_request
        )
    ]
)
```

### Middleware with State

Store and retrieve state in middleware:

```python
from velithon.middleware import BaseHTTPMiddleware
from velithon.requests import Request

class UserTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Add user tracking to request state
        request.state.user_id = self.extract_user_id(request)
        request.state.session_id = self.generate_session_id()
        
        response = await call_next(request)
        
        # Add tracking headers
        response.headers["X-User-ID"] = request.state.user_id
        response.headers["X-Session-ID"] = request.state.session_id
        
        return response
    
    def extract_user_id(self, request: Request) -> str:
        # Extract user ID from headers, cookies, etc.
        return request.headers.get("X-User-ID", "anonymous")
    
    def generate_session_id(self) -> str:
        import uuid
        return str(uuid.uuid4())
```

## Middleware Order

The order of middleware is important. Middleware is executed in the order it's added:

```python
app = Velithon(
    middleware=[
        # 1. Logging (first to capture everything)
        LoggingMiddleware(),
        
        # 2. CORS (early to handle preflight requests)
        CORSMiddleware(origins=["*"]),
        
        # 3. Authentication (before business logic)
        AuthenticationMiddleware(),
        
        # 4. Compression (after authentication, before response)
        CompressionMiddleware(),
        
        # 5. Custom middleware (last in chain)
        CustomMiddleware()
    ]
)
```

## Middleware Best Practices

### 1. Keep Middleware Lightweight

```python
# Good: Lightweight middleware
class SimpleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Custom"] = "value"
        return response

# Avoid: Heavy operations in middleware
class HeavyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Don't do heavy operations here
        await self.heavy_database_operation()  # ❌
        response = await call_next(request)
        return response
```

### 2. Use Conditional Middleware

```python
# Only apply middleware where needed
def is_admin_request(request: Request) -> bool:
    return request.path.startswith("/admin/")

app = Velithon(
    middleware=[
        ConditionalMiddleware(
            AdminAuthMiddleware(),
            condition=is_admin_request
        )
    ]
)
```

### 3. Handle Exceptions Gracefully

```python
class SafeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the error but don't break the request
            logger.error(f"Middleware error: {e}")
            # Return a fallback response or re-raise
            raise
```

### 4. Use Middleware for Cross-cutting Concerns

```python
# Good use cases for middleware:
# - Logging
# - Authentication
# - CORS
# - Compression
# - Rate limiting
# - Request/response transformation
# - Metrics collection

# Avoid using middleware for:
# - Business logic
# - Database operations
# - Complex calculations
```

## Advanced Middleware Patterns

### Middleware with Configuration

```python
from dataclasses import dataclass
from velithon.middleware import BaseHTTPMiddleware

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    burst_size: int = 10

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests.get(client_ip, [])
            if now - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.config.requests_per_minute:
            return JSONResponse(
                {"error": "Rate limit exceeded"},
                status_code=429
            )
        
        # Add current request
        self.requests[client_ip].append(now)
        
        return await call_next(request)
```

### Middleware with Dependency Injection

```python
from velithon.di import inject, Provide

class DatabaseMiddleware(BaseHTTPMiddleware):
    def __init__(self, database_service):
        self.database_service = database_service
    
    @inject
    async def dispatch(
        self, 
        request: Request, 
        call_next,
        db: DatabaseService = Provide[DatabaseService]
    ):
        # Use injected database service
        request.state.db = db
        return await call_next(request)
```

This covers the middleware system in Velithon. Middleware is a powerful tool for adding cross-cutting concerns to your application while keeping your route handlers clean and focused on business logic.
