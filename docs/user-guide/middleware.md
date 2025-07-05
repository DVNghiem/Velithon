# Middleware

Middleware in Velithon allows you to process requests and responses before they reach your application endpoints. Velithon provides a comprehensive set of built-in middleware and supports custom middleware creation.

## Adding Middleware

Middleware is added to your application during initialization:

```python
from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.cors import CORSMiddleware
from velithon.middleware.compression import CompressionMiddleware

app = Velithon(
    middleware=[
        Middleware(CORSMiddleware, allow_origins=["*"]),
        Middleware(CompressionMiddleware, minimum_size=500),
    ]
)
```

## Built-in Middleware

### CORS Middleware

Handle Cross-Origin Resource Sharing (CORS) for browser requests:

```python
from velithon.middleware.cors import CORSMiddleware

app = Velithon(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["https://frontend.example.com", "https://app.example.com"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            max_age=600  # Preflight cache duration in seconds
        )
    ]
)

# Allow all origins (development only)
app = Velithon(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],  # Allows all HTTP methods
            allow_headers=["*"],
            allow_credentials=False  # Cannot use credentials with wildcard origins
        )
    ]
)
```

**CORS Middleware features:**
- Automatic preflight request handling
- Origin validation
- Method and header validation
- Credential support
- Configurable preflight cache duration
- Secure defaults

### Compression Middleware

Automatically compress HTTP responses using gzip compression:

```python
from velithon.middleware.compression import CompressionMiddleware, CompressionLevel

app = Velithon(
    middleware=[
        Middleware(
            CompressionMiddleware,
            minimum_size=500,  # Only compress responses >= 500 bytes
            compression_level=CompressionLevel.BALANCED,  # Compression level
            compressible_types={  # Custom content types to compress
                "application/json",
                "text/html", 
                "text/css",
                "application/javascript",
                "text/plain",
                "text/xml",
                "application/xml"
            }
        )
    ]
)
```

The compression middleware will:
- Only compress responses for clients that accept gzip encoding
- Only compress responses above the minimum size threshold (default: 500 bytes)
- Only compress responses with compressible content types
- Add appropriate `Content-Encoding` and `Vary` headers
- Automatically update the `Content-Length` header

**Compression levels:**
- `CompressionLevel.FASTEST` (1): Fastest compression, larger file size
- `CompressionLevel.BALANCED` (6): Balanced speed and compression ratio (default)
- `CompressionLevel.BEST` (9): Best compression, slower speed

### Session Middleware

Provides session support with multiple backend options for storing session data:

```python
from velithon.middleware.session import SessionMiddleware

# Memory-based sessions (default)
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key="your-secret-key-here"  # Required for signed cookies
        )
    ]
)

# Cookie-based sessions (signed with HMAC)
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key="your-secret-key-here",
            cookie_name="velithon_session",  # Custom cookie name
            max_age=3600,  # Session expires in 1 hour
            cookie_params={
                "path": "/",
                "domain": None,
                "secure": False,  # Set to True for HTTPS
                "httponly": True,  # Prevent JavaScript access
                "samesite": "lax"  # CSRF protection
            }
        )
    ]
)
```

**Using sessions in your endpoints:**

```python
from velithon.requests import Request
from velithon.responses import JSONResponse

@app.get("/login")
async def login(request: Request):
    # Access session through request.session
    session = request.session
    
    # Set session data
    session["user_id"] = 123
    session["username"] = "alice"
    session["is_admin"] = False
    
    return JSONResponse({"message": "Logged in"})

@app.get("/profile")
async def profile(request: Request):
    # Read session data
    user_id = request.session.get("user_id")
    
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    
    return JSONResponse({
        "user_id": user_id,
        "username": request.session.get("username"),
        "is_admin": request.session.get("is_admin", False)
    })

@app.post("/logout")
async def logout(request: Request):
    # Clear session data
    request.session.clear()
    return JSONResponse({"message": "Logged out"})
```

**Session backends:**

- **Memory**: Fast in-memory storage (default). Data is lost when the server restarts.
- **Signed Cookie**: Stores session data in browser cookies, signed with HMAC for security. Limited by browser cookie size (~4KB).

**Custom session interface:**

```python
from velithon.middleware.session import SessionInterface, Session

class RedisSessionInterface(SessionInterface):
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def load_session(self, session_id: str) -> dict:
        data = await self.redis.get(f"session:{session_id}")
        if data:
            import json
            return json.loads(data)
        return {}
    
    async def save_session(self, session_id: str, session_data: dict) -> None:
        import json
        await self.redis.setex(
            f"session:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(session_data)
        )

    async def delete_session(self, session_id: str) -> None:
        await self.redis.delete(f"session:{session_id}")

    def generate_session_id(self) -> str:
        import os
        return os.urandom(32).hex()

# Use custom interface
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            session_interface=RedisSessionInterface(redis_client)
        )
    ]
)
```

**Session features:**
- Automatic session creation and management
- Secure HMAC signing for cookie-based sessions
- Configurable cookie settings (secure, httponly, samesite)
- Session expiration support
- Modification tracking (only saves when data changes)
- Thread-safe memory storage
- Easy access via `request.session`

### Security Middleware

Adds security headers and handles global security policies:

```python
from velithon.middleware.auth import SecurityMiddleware

app = Velithon(
    middleware=[
        Middleware(
            SecurityMiddleware,
            add_security_headers=True,  # Add standard security headers
            cors_enabled=False  # Enable if using CORS
        )
    ]
)
```

The security middleware automatically adds these headers:
- `X-Content-Type-Options: nosniff` - Prevent MIME type sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - Enable XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Control referrer information

### Authentication Middleware

Handles authentication errors gracefully:

```python
from velithon.middleware.auth import AuthenticationMiddleware

app = Velithon(
    middleware=[
        Middleware(AuthenticationMiddleware)
    ]
)
```

This middleware catches `AuthenticationError` and `AuthorizationError` exceptions and returns appropriate HTTP error responses.

### Logging Middleware

Automatically logs requests and responses:

```python
from velithon.middleware.logging import LoggingMiddleware

app = Velithon(
    middleware=[
        Middleware(
            LoggingMiddleware,
            logger_name="velithon.requests",  # Custom logger name
            level="INFO"  # Log level
        )
    ]
)
```

### Proxy Middleware

Provides advanced proxy capabilities for microservices:

```python
from velithon.middleware.proxy import ProxyMiddleware

app = Velithon(
    middleware=[
        Middleware(
            ProxyMiddleware,
            target_url="http://backend-service:8080",
            strip_path="/api",  # Strip this prefix before forwarding
            add_headers={"X-Forwarded-By": "Velithon"},
            timeout_ms=5000,
            max_retries=3
        )
    ]
)
```

## Custom Middleware

### Creating Custom HTTP Middleware

```python
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.datastructures import Scope, Protocol
from velithon.requests import Request
from velithon.responses import JSONResponse
import time

class TimingMiddleware(BaseHTTPMiddleware):
    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        start_time = time.time()
        
        # Add timing info to scope
        scope.state = getattr(scope, 'state', {})
        scope.state['start_time'] = start_time
        
        # Process the request
        await self.app(scope, protocol)
        
        # Calculate duration
        duration = time.time() - start_time
        print(f"Request took {duration:.3f} seconds")

# Add to your app
app = Velithon(
    middleware=[
        Middleware(TimingMiddleware)
    ]
)
```

### Protocol Wrapper Middleware

For middleware that needs to modify responses:

```python
from velithon.middleware.base import ProtocolWrapperMiddleware
from velithon.datastructures import Protocol

class CustomHeaderProtocol:
    def __init__(self, protocol: Protocol, custom_header: str):
        self.protocol = protocol
        self.custom_header = custom_header
    
    def __getattr__(self, name):
        return getattr(self.protocol, name)
    
    def response_bytes(self, status: int, headers: list, body: bytes):
        # Add custom header
        headers.append(('X-Custom', self.custom_header))
        return self.protocol.response_bytes(status, headers, body)

class CustomHeaderMiddleware(ProtocolWrapperMiddleware):
    def __init__(self, app, custom_header: str = "Velithon"):
        super().__init__(app)
        self.custom_header = custom_header
    
    def create_wrapped_protocol(self, scope: Scope, protocol: Protocol) -> Protocol:
        return CustomHeaderProtocol(protocol, self.custom_header)

# Usage
app = Velithon(
    middleware=[
        Middleware(CustomHeaderMiddleware, custom_header="MyApp/1.0")
    ]
)
```

### Conditional Middleware

For middleware that should only run under certain conditions:

```python
from velithon.middleware.base import ConditionalMiddleware
from velithon.datastructures import Scope, Protocol

class APIKeyMiddleware(ConditionalMiddleware):
    def __init__(self, app, required_paths: list[str], api_key: str):
        super().__init__(app)
        self.required_paths = required_paths
        self.api_key = api_key
    
    async def should_process_request(self, scope: Scope, protocol: Protocol) -> bool:
        # Only process requests to protected paths
        if not any(scope.path.startswith(path) for path in self.required_paths):
            return True  # Continue processing
        
        # Check API key
        api_key = scope.headers.get('x-api-key')
        if api_key != self.api_key:
            from velithon.responses import JSONResponse
            response = JSONResponse(
                {"error": "Invalid API key"}, 
                status_code=401
            )
            await response(scope, protocol)
            return False  # Stop processing
        
        return True  # Continue processing

# Usage
app = Velithon(
    middleware=[
        Middleware(
            APIKeyMiddleware,
            required_paths=["/api/admin", "/api/internal"],
            api_key="secret-key"
        )
    ]
)
```

## Middleware Order

Middleware order matters! Middleware is executed in the order it's defined:

```python
app = Velithon(
    middleware=[
        # 1. CORS (should be first for preflight requests)
        Middleware(CORSMiddleware, allow_origins=["*"]),
        
        # 2. Security headers
        Middleware(SecurityMiddleware),
        
        # 3. Authentication
        Middleware(AuthenticationMiddleware),
        
        # 4. Sessions (after auth)
        Middleware(SessionMiddleware, secret_key="secret"),
        
        # 5. Compression (should be last)
        Middleware(CompressionMiddleware),
    ]
)
```

## Middleware Best Practices

### Performance Considerations

```python
# Use caching for expensive operations
class CachingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.cache = {}
    
    async def process_http_request(self, scope: Scope, protocol: Protocol):
        # Check cache before processing
        cache_key = f"{scope.method}:{scope.path}"
        
        if cache_key in self.cache:
            # Return cached response
            cached_response = self.cache[cache_key]
            await cached_response(scope, protocol)
            return
        
        # Process normally and cache result
        await self.app(scope, protocol)
```

### Error Handling

```python
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def process_http_request(self, scope: Scope, protocol: Protocol):
        try:
            await self.app(scope, protocol)
        except Exception as e:
            # Log the error
            import logging
            logging.exception(f"Unhandled error: {e}")
            
            # Return error response
            from velithon.responses import JSONResponse
            response = JSONResponse(
                {"error": "Internal server error"},
                status_code=500
            )
            await response(scope, protocol)
```

### Request Modification

```python
class RequestModifierMiddleware(BaseHTTPMiddleware):
    async def process_http_request(self, scope: Scope, protocol: Protocol):
        # Add custom data to scope
        scope.custom_data = {"processed_by": "middleware"}
        
        # Modify headers
        headers = dict(scope.headers)
        headers['x-processed'] = 'true'
        scope.headers = headers
        
        await self.app(scope, protocol)
```

This middleware system provides powerful capabilities for cross-cutting concerns like authentication, logging, compression, and security while maintaining high performance through Velithon's optimized RSGI architecture.
