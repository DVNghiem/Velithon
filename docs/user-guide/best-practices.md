# Best Practices for Velithon

This guide covers essential best practices for developing high-performance, secure, and maintainable Velithon applications.

## 🏗️ Application Architecture

### Project Structure

Organize your application for scalability and maintainability:

```
project/
├── main.py                    # Application entry point
├── config.py                  # Configuration management
├── containers.py              # Dependency injection containers
├── routes/
│   ├── __init__.py
│   ├── users.py              # User routes
│   ├── products.py           # Product routes
│   └── admin.py              # Admin routes
├── endpoints/
│   ├── __init__.py
│   ├── users.py              # User business logic
│   ├── products.py           # Product business logic
│   └── admin.py              # Admin business logic
├── services/
│   ├── __init__.py
│   ├── user_service.py       # Domain services
│   ├── email_service.py      # External services
│   └── database_service.py   # Data layer
├── models/
│   ├── __init__.py
│   ├── user.py               # Pydantic models
│   ├── product.py            # Request/Response models
│   └── schemas.py            # Database schemas
├── middleware/
│   ├── __init__.py
│   ├── auth.py               # Authentication middleware
│   ├── security.py           # Security headers
│   └── logging.py            # Request logging
├── templates/                 # Template files (if needed)
├── static/                    # Static assets
└── tests/
    ├── __init__.py
    ├── test_routes.py
    ├── test_services.py
    └── fixtures/
```

### Configuration Management

Use environment-based configuration with proper validation:

```python
from typing import List, Optional
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    # Application
    app_name: str = "Velithon Application"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 4
    log_level: str = "INFO"
    
    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Security
    secret_key: str
    jwt_secret: str = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE"]
    cors_headers: List[str] = ["*"]
    
    # File uploads
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_path: str = "./uploads"
    allowed_extensions: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".pdf"]
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(',')]
        return v
    
    @validator('debug', pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

## ⚡ Performance Best Practices

### 1. Use Optimized JSON Responses

For large datasets, use Velithon's optimized JSON serialization:

```python
from velithon.responses import JSONResponse

@app.get("/api/large-dataset")
async def get_large_dataset():
    data = generate_large_dataset()
    return JSONResponse(data)

@app.get("/api/batch-data")
async def get_batch_data():
    objects = [generate_object(i) for i in range(1000)]
    return JSONResponse(objects)

# Simple and optimized - no special configuration needed
@app.get("/api/simple-optimized")
async def get_simple_data():
    data = {"message": "Hello", "items": list(range(1000))}
    return JSONResponse(data)

@app.get("/api/batch-simple")
async def get_batch_simple():
    objects = [{"id": i, "value": f"item_{i}"} for i in range(500)]
    return JSONResponse(objects)
```

### 2. Connection Pooling

Always use connection pools for databases and external services:

```python
import asyncpg
import aioredis
from velithon import Velithon

app = Velithon()

@app.on_startup
async def setup_connections():
    # Database pool
    app.state.db_pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=10,
        max_size=50,
        command_timeout=60
    )
    
    # Redis pool
    app.state.redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )

@app.on_shutdown
async def cleanup_connections():
    await app.state.db_pool.close()
    await app.state.redis.close()
```

### 3. Efficient Async Operations

Always use async/await for I/O operations:

```python
# ✅ Good: Async database operations
class UserService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def get_user(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
    
    async def get_users_batch(self, user_ids: List[int]):
        async with self.db_pool.acquire() as conn:
            return await conn.fetch(
                "SELECT * FROM users WHERE id = ANY($1)", user_ids
            )

# ✅ Good: Concurrent operations
async def process_user_data(user_id: int):
    user_task = get_user(user_id)
    orders_task = get_user_orders(user_id)
    preferences_task = get_user_preferences(user_id)
    
    # Execute concurrently
    user, orders, preferences = await asyncio.gather(
        user_task, orders_task, preferences_task
    )
    
    return combine_user_data(user, orders, preferences)
```

### 4. Streaming for Large Responses

Use streaming for large datasets to reduce memory usage:

```python
@app.get("/export/users")
async def export_users():
    async def generate_csv():
        yield "id,name,email\n"
        async for user in stream_all_users():
            yield f"{user.id},{user.name},{user.email}\n"
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )
```

### 5. Caching Strategy

Implement intelligent caching for frequently accessed data:

```python
import redis.asyncio as redis
from functools import wraps

def cache_result(expire_seconds: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached = await app.state.redis.get(key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await app.state.redis.setex(
                key, expire_seconds, json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator

@cache_result(expire_seconds=600)
async def get_expensive_data(param: str):
    # Expensive operation here
    return await fetch_from_external_api(param)
```

## 🔒 Security Best Practices

### 1. Input Validation

Always validate and sanitize input data:

```python
from pydantic import BaseModel, validator, EmailStr
import re

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: Optional[int] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v) > 100:
            raise ValueError('Name too long')
        # Remove potential script tags
        v = re.sub(r'<[^>]*>', '', v)
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Invalid age')
        return v
```

### 2. Authentication & Authorization

Implement secure authentication with proper middleware:

```python
from velithon.middleware import Middleware
from velithon.middleware.auth import AuthenticationMiddleware, SecurityMiddleware
import jwt

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        
        # Skip auth for public endpoints
        if request.url.path in ['/health', '/docs', '/login']:
            return await self.app(scope, receive, send)
        
        # Extract token
        auth_header = request.headers.get('authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return await self.unauthorized_response(send)
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(
                token, 
                settings.jwt_secret, 
                algorithms=[settings.jwt_algorithm]
            )
            request.state.user_id = payload.get('user_id')
            request.state.user_role = payload.get('role', 'user')
        except jwt.InvalidTokenError:
            return await self.unauthorized_response(send)
        
        return await self.app(scope, receive, send)
    
    async def unauthorized_response(self, send):
        response = JSONResponse(
            {"error": "Unauthorized"}, 
            status_code=401
        )
        await response(None, None, send)

# Add middleware to application
app = Velithon(
    middleware=[
        Middleware(SecurityMiddleware),
        Middleware(AuthenticationMiddleware),
        Middleware(JWTAuthMiddleware)
    ]
)
```

### 3. HTTPS and Security Headers

Always use HTTPS in production and implement security headers:

```python
from velithon.middleware import Middleware
from velithon.middleware.auth import SecurityMiddleware

# Enable built-in security middleware
app = Velithon(
    middleware=[
        Middleware(SecurityMiddleware, add_security_headers=True)
    ]
)

# Or create custom security middleware
class CustomSecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.security_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'"
        }
    
    async def __call__(self, scope, receive, send):
        async def add_security_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                for name, value in self.security_headers.items():
                    headers[name.encode()] = value.encode()
                message["headers"] = list(headers.items())
            await send(message)
        
        await self.app(scope, receive, add_security_headers)

app = Velithon(
    middleware=[
        Middleware(CustomSecurityMiddleware)
    ]
)
```

### 4. Rate Limiting

Implement rate limiting to prevent abuse:

```python
import time
from collections import defaultdict
from velithon.middleware import Middleware

class RateLimitMiddleware:
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        client_ip = request.client.host
        
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] 
            if req_time > minute_ago
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            response = JSONResponse(
                {"error": "Rate limit exceeded"}, 
                status_code=429
            )
            await response(scope, receive, send)
            return
        
        # Record request
        self.requests[client_ip].append(now)
        
        await self.app(scope, receive, send)

app = Velithon(
    middleware=[
        Middleware(RateLimitMiddleware, requests_per_minute=100)
    ]
)
```

## 📁 File Upload Best Practices

### 1. Secure File Handling

Always validate and secure file uploads:

```python
import uuid
import aiofiles
from pathlib import Path

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def validate_and_save_file(file: UploadFile) -> str:
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed")
    
    # Validate file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # Generate secure filename
    secure_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = Path(settings.upload_path) / secure_filename
    
    # Create upload directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return str(file_path)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = await validate_and_save_file(file)
        return {"filename": file.filename, "path": file_path}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")
```

### 2. Content Validation

Validate file content, not just extensions:

```python
import magic

async def validate_file_content(file_path: Path, expected_types: List[str]):
    """Validate file content using magic numbers."""
    try:
        file_type = magic.from_file(str(file_path), mime=True)
        if file_type not in expected_types:
            raise ValueError(f"Invalid file type: {file_type}")
        return True
    except Exception:
        return False

# Usage
IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif']
if not await validate_file_content(file_path, IMAGE_TYPES):
    raise HTTPException(400, "Invalid image file")
```

## 🔄 Background Task Best Practices

### 1. Error Handling

Always implement proper error handling for background tasks:

```python
import logging
from velithon.background import BackgroundTasks

logger = logging.getLogger(__name__)

async def safe_background_task(task_func, *args, **kwargs):
    """Wrapper for safe background task execution."""
    try:
        await task_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Background task failed: {task_func.__name__}: {e}")
        # Optional: Send to error monitoring service
        # await send_error_to_monitoring(e, task_func.__name__)

@app.post("/orders")
async def create_order(order_data: dict):
    # Process order synchronously
    order = await process_order(order_data)
    
    # Create background tasks
    background_tasks = BackgroundTasks()
    
    # Add background tasks with error handling
    background_tasks.add_task(
        safe_background_task, 
        send_confirmation_email, 
        order_data["email"]
    )
    background_tasks.add_task(
        safe_background_task, 
        update_inventory, 
        order_data["items"]
    )
    
    # Execute background tasks
    await background_tasks()
    )
    background_tasks.add_task(
        safe_background_task, 
        log_order_analytics, 
        order
    )
    
    return {"message": "Order created", "order_id": order.id}
```

### 2. Task Prioritization

Implement task prioritization for better resource management:

```python
from enum import Enum

class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class PriorityBackgroundTasks:
    def __init__(self):
        self.tasks = {
            TaskPriority.HIGH: [],
            TaskPriority.MEDIUM: [],
            TaskPriority.LOW: []
        }
    
    def add_task(self, func, *args, priority=TaskPriority.MEDIUM, **kwargs):
        self.tasks[priority].append((func, args, kwargs))
    
    async def execute_all(self):
        # Execute high priority tasks first
        for priority in TaskPriority:
            for func, args, kwargs in self.tasks[priority]:
                await safe_background_task(func, *args, **kwargs)
```

## 🧪 Testing Best Practices

### 1. Test Structure

Organize your tests for maintainability:

```python
import pytest
import httpx

@pytest.fixture
async def client():
    # Note: Velithon doesn't have a built-in TestClient
    # Use httpx for testing HTTP endpoints
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def authenticated_client(client):
    # Create test user and authenticate
    token = await create_test_user_and_get_token()
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client

class TestUserEndpoints:
    async def test_create_user(self, client):
        user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecurePass123"
        }
        response = await client.post("/users", json=user_data)
        assert response.status_code == 201
        assert response.json()["email"] == user_data["email"]
    
    async def test_get_user_unauthorized(self, client):
        response = await client.get("/users/1")
        assert response.status_code == 401
    
    async def test_get_user_authorized(self, authenticated_client):
        response = await authenticated_client.get("/users/1")
        assert response.status_code == 200
```

### 2. Mocking External Services

Mock external dependencies for reliable tests:

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_email_service():
    with patch('services.email_service.send_email') as mock:
        mock.return_value = AsyncMock()
        yield mock

class TestOrderProcessing:
    async def test_order_creation_sends_email(self, client, mock_email_service):
        order_data = {"items": [{"id": 1, "quantity": 2}]}
        
        response = await client.post("/orders", json=order_data)
        
        assert response.status_code == 201
        mock_email_service.assert_called_once()
```

## 🚀 Production Deployment

### 1. Environment Configuration

Use proper environment separation:

```bash
# .env.production
ENV=production
DEBUG=false
LOG_LEVEL=INFO
WORKERS=8
HOST=0.0.0.0
PORT=8000

# Database with connection pooling
DATABASE_URL=postgresql://user:pass@db:5432/prod_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis for caching and sessions
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-very-secure-secret-key
JWT_SECRET=your-jwt-secret-key
```

### 2. Health Checks

Implement comprehensive health checks:

```python
@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version
    }
    
    # Check database
    try:
        async with app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
        checks["status"] = "unhealthy"
    
    # Check Redis
    try:
        await app.state.redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"
        checks["status"] = "unhealthy"
    
    status_code = 200 if checks["status"] == "healthy" else 503
    return JSONResponse(checks, status_code=status_code)
```

### 3. Monitoring and Logging

Implement proper logging and monitoring:

```python
import structlog
from prometheus_client import Counter, Histogram, generate_latest

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 
    'HTTP request duration'
)

class MonitoringMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        start_time = time.time()
        
        async def record_metrics(message):
            if message["type"] == "http.response.start":
                # Record metrics
                REQUEST_COUNT.labels(
                    method=scope.method,
                    endpoint=scope.path,
                    status=message.get("status", 200)
                ).inc()
                
                REQUEST_DURATION.observe(time.time() - start_time)
                
                # Structured logging
                logger = structlog.get_logger()
                logger.info(
                    "HTTP request",
                    method=scope.method,
                    path=scope.path,
                    status_code=message.get("status", 200),
                    duration=time.time() - start_time,
                    client_ip=scope.client
                )
            
            await send(message)
        
        await self.app(scope, receive, record_metrics)

app = Velithon(
    middleware=[
        Middleware(MonitoringMiddleware)
    ]
)

# Metrics endpoint defined in the Velithon application
app.router.add_route("/metrics", 
    lambda request: PlainTextResponse(generate_latest()),
    methods=["GET"])
```

## 📊 Monitoring and Observability

### 1. Application Metrics

Track key application metrics:

```python
from velithon.middleware import Middleware
import time

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
    
    async def __call__(self, scope, receive, send):
        start_time = time.time()
        self.request_count += 1
        
        async def track_response(message):
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                if status_code >= 400:
                    self.error_count += 1
                
                duration = time.time() - start_time
                self.response_times.append(duration)
                
                # Keep only last 1000 response times
                if len(self.response_times) > 1000:
                    self.response_times = self.response_times[-1000:]
            
            await send(message)
        
        await self.app(scope, receive, track_response)

app = Velithon(
    middleware=[
        Middleware(MetricsMiddleware)
    ]
)
```

### 2. Error Tracking

Implement comprehensive error tracking:

```python
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Configure Sentry
sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.ERROR
)

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[sentry_logging],
    traces_sample_rate=0.1,  # Adjust based on traffic
    release=settings.app_version,
    environment=settings.environment
)

# Error handling should be done within endpoints
@app.get("/api/example")
async def example_endpoint(request: Request):
    try:
        # Your business logic here
        result = some_business_logic()
        return {"result": result}
    except Exception as exc:
        # Log error with context
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            request_path=request.url.path,
            request_method=request.method,
            user_id=getattr(request.state, 'user_id', None)
        )
        
        # Return appropriate error response
        if settings.debug:
            return JSONResponse(
                {"error": str(exc), "type": type(exc).__name__},
                status_code=500
        )
    else:
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500
        )
```

Following these best practices will help you build robust, secure, and high-performance Velithon applications that are easy to maintain and scale.
