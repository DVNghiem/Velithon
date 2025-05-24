# Middleware

## Built-in Middleware

### Logging Middleware

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

### CORS Middleware

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
                "application/javascript"
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
            secret_key="your-secret-key"  # Required for signed cookies
        )
    ]
)

# Cookie-based sessions (signed with HMAC)
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key="your-secret-key",
            session_interface="cookie",  # Use signed cookies
            max_age=3600,  # Session expires in 1 hour
            cookie_name="session",  # Custom cookie name
            cookie_path="/",  # Cookie path
            cookie_domain=None,  # Cookie domain
            cookie_secure=False,  # HTTPS only
            cookie_httponly=True,  # HTTP only (no JavaScript access)
            cookie_samesite="lax"  # SameSite policy
        )
    ]
)
```

**Using sessions in your endpoints:**

```python
@app.get("/login")
async def login(request: Request):
    # Access session through request.session
    session = request.session
    
    # Set session data
    session["user_id"] = 123
    session["username"] = "alice"
    
    return JSONResponse({"message": "Logged in"})

@app.get("/profile")
async def profile(request: Request):
    # Read session data
    user_id = request.session.get("user_id")
    
    if not user_id:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    
    return JSONResponse({
        "user_id": user_id,
        "username": request.session.get("username")
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
    
    async def load_session(self, session_id: str) -> Session:
        data = await self.redis.get(f"session:{session_id}")
        if data:
            import json
            return Session(json.loads(data), session_id=session_id)
        return Session(session_id=session_id)
    
    async def save_session(self, session: Session) -> None:
        if session.modified:
            import json
            await self.redis.setex(
                f"session:{session.session_id}",
                3600,  # 1 hour expiry
                json.dumps(dict(session))
            )

# Use custom interface
app = Velithon(
    middleware=[
        Middleware(
            SessionMiddleware,
            secret_key="your-secret-key",
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

## Custom Middleware

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

## Middleware Order

Middleware is executed in reverse order (last added is executed first):

```python
app = Velithon(
    middleware=[
        Middleware(LoggingMiddleware),    # Executed second
        Middleware(AuthMiddleware),      # Executed first
    ]
)
```
