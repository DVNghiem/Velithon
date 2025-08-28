# Advanced Features

Velithon provides several advanced features for building sophisticated, high-performance applications. This section covers the most powerful capabilities for expert users.

## 🌐 Gateway & Proxy System

Velithon includes a high-performance gateway system built in Rust for maximum efficiency. The gateway provides load balancing, circuit breakers, health checking, and intelligent request routing.

### Key Features
- **High Performance**: Rust-based implementation using hyper
- **Load Balancing**: Multiple strategies (round-robin, random, weighted)
- **Circuit Breaker**: Prevents cascading failures
- **Health Checking**: Automatic monitoring of upstream services
- **Connection Pooling**: Efficient connection reuse
- **Request Transformation**: Header and path manipulation

### Quick Example

```python
from velithon import Velithon
from velithon.gateway import Gateway, forward_to

app = Velithon()
gateway = Gateway()

@app.get("/api/{path:path}")
async def api_proxy(request: Request):
    return await forward_to("http://api-service:8080", request)
```

**Learn More**: [Gateway & Proxy Guide](../advanced/gateway.md)

## ⚡ High-Performance JSON Serialization

Velithon includes a Rust-based JSON serialization system that provides significant performance improvements for large JSON responses through parallel processing and intelligent caching.

### Performance Benefits

| Data Type | Performance Improvement | Use Case |
|-----------|------------------------|----------|
| **Large Arrays** | 3-6x faster | API responses with many items |
| **Complex Objects** | 2-4x faster | Nested data structures |
| **Batch Processing** | 4-8x faster | Multiple objects in parallel |
| **Simple Objects** | 1.5-2x faster | Fast path optimization |

### Quick Example

```python
from velithon.responses import JSONResponse

@app.get("/large-dataset")
async def get_large_dataset():
    data = generate_large_dataset()
    return JSONResponse(data)

@app.get("/batch-data")
async def get_batch_data():
    objects = [generate_object(i) for i in range(1000)]
    return JSONResponse(objects)
```

**Learn More**: [JSON Optimization Guide](json-optimization.md)

## 🧩 Advanced Dependency Injection

Velithon's dependency injection system supports complex scenarios including scoped dependencies, conditional injection, and lifecycle management.

### Advanced Patterns

#### Scoped Dependencies
```python
from velithon.di import ServiceContainer, Provide, SingletonProvider, FactoryProvider, Scope

class DatabaseSession:
    def __init__(self):
        self.connection = create_connection()
    
    def __del__(self):
        self.connection.close()

class Container(ServiceContainer):
    database_session = FactoryProvider(DatabaseSession, scope=Scope.REQUEST)

container = Container()

@app.get("/users")
async def get_users(db: DatabaseSession = Provide[container.database_session]):
    return await db.fetch_users()
```

#### Conditional Injection
```python
class ConditionalContainer(ServiceContainer):
    @property
    def cache_service(self):
        if settings.use_redis_cache:
            return RedisCache()
        else:
            return MemoryCache()

class RedisCache:
    pass

class MemoryCache:
    pass
```

**Learn More**: [Dependency Injection Guide](../user-guide/dependency-injection.md)

## 🔌 Advanced Middleware

### Middleware Optimization

Velithon automatically optimizes middleware stacks for better performance:

```python
from velithon.middleware import Middleware
from velithon.middleware.compression import CompressionMiddleware
from velithon.middleware.auth import AuthenticationMiddleware, SecurityMiddleware
from velithon.middleware.logging import LoggingMiddleware

# Middleware are automatically reordered for optimal performance
app = Velithon(
    middleware=[
        Middleware(CompressionMiddleware),  # Low priority
        Middleware(AuthenticationMiddleware),         # High priority  
        Middleware(LoggingMiddleware),      # Low priority
        Middleware(SecurityMiddleware),     # High priority
    ]
)

# Result: SecurityMiddleware -> AuthenticationMiddleware -> CompressionMiddleware -> LoggingMiddleware
```

### Custom High-Performance Middleware

```python
class FastCacheMiddleware:
    def __init__(self, app, cache_ttl: int = 300):
        self.app = app
        self.cache_ttl = cache_ttl
        self.cache = {}
    
    async def __call__(self, scope, receive, send):
        if scope["method"] != "GET":
            return await self.app(scope, receive, send)
        
        cache_key = f"{scope['path']}?{scope.get('query_string', b'').decode()}"
        
        # Check cache
        if cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return await cached_response(scope, receive, send)
        
        # Capture response for caching
        response_data = []
        
        async def capture_send(message):
            response_data.append(message)
            await send(message)
        
        await self.app(scope, receive, capture_send)
        
        # Cache successful responses
        if response_data and response_data[0].get("status", 500) < 400:
            self.cache[cache_key] = (
                create_response_from_data(response_data),
                time.time()
            )
```

## 🔄 Advanced Background Tasks

### Task Queues with Priorities

```python
from velithon.background import BackgroundTaskQueue, TaskPriority
import asyncio

class AdvancedBackgroundTasks:
    def __init__(self):
        self.queue = BackgroundTaskQueue()
    
    def add_high_priority_task(self, func, *args, **kwargs):
        self.queue.put_nowait((TaskPriority.HIGH, func, args, kwargs))
    
    def add_low_priority_task(self, func, *args, **kwargs):
        self.queue.put_nowait((TaskPriority.LOW, func, args, kwargs))
    
    async def worker(self):
        while True:
            try:
                priority, func, args, kwargs = await self.queue.get()
                await func(*args, **kwargs)
                self.queue.task_done()
            except Exception as e:
                logger.error(f"Background task failed: {e}")

# Start background workers
background_tasks = AdvancedBackgroundTasks()
asyncio.create_task(background_tasks.worker())
```

### Distributed Task Processing

```python
from celery import Celery

# Configure Celery for distributed tasks
celery_app = Celery(
    'velithon_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@celery_app.task
def process_heavy_computation(data):
    # CPU-intensive task
    return complex_calculation(data)

@app.post("/compute")
async def submit_computation(data: dict):
    # Submit to distributed queue
    task = process_heavy_computation.delay(data)
    
    # Create background task for storing task ID
    background_tasks = BackgroundTasks()
    background_tasks.add_task(store_task_id, task.id, user_id)
    
    # Execute background tasks
    await background_tasks()
    
    return {"task_id": task.id, "status": "submitted"}
```

## 🌊 Advanced WebSocket Features

### WebSocket with Authentication

```python
from velithon.websockets import WebSocketManager
import jwt

class AuthenticatedWebSocketManager(WebSocketManager):
    async def authenticate_connection(self, websocket, token: str):
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            return payload.get("user_id")
        except jwt.InvalidTokenError:
            await websocket.close(code=4001, reason="Invalid token")
            return None

manager = AuthenticatedWebSocketManager()

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user_id = await manager.authenticate_connection(websocket, token)
    if user_id:
        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                await manager.broadcast_to_user(user_id, data)
        except WebSocketDisconnect:
            manager.disconnect(websocket)
```

### WebSocket Connection Pooling

```python
class PooledWebSocketManager:
    def __init__(self, max_connections_per_user: int = 10):
        self.max_connections = max_connections_per_user
        self.user_connections = defaultdict(list)
    
    async def connect(self, websocket: WebSocket, user_id: str):
        connections = self.user_connections[user_id]
        
        # Enforce connection limit
        if len(connections) >= self.max_connections:
            oldest_connection = connections.pop(0)
            await oldest_connection.close(code=4002, reason="Connection limit exceeded")
        
        await websocket.accept()
        connections.append(websocket)
    
    async def broadcast_to_user(self, user_id: str, message: str):
        connections = self.user_connections[user_id]
        disconnected = []
        
        for connection in connections:
            try:
                await connection.send_text(message)
            except ConnectionClosed:
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            connections.remove(conn)
```

## 🎯 Advanced Routing

### Dynamic Route Generation

```python
from velithon.routing import RouteGenerator

class APIRouteGenerator:
    def __init__(self, app: Velithon):
        self.app = app
    
    def generate_crud_routes(self, model_class, prefix: str):
        """Generate CRUD routes for a model."""
        
        @self.app.get(f"/{prefix}")
        async def list_items(skip: int = 0, limit: int = 100):
            return await model_class.list(skip=skip, limit=limit)
        
        @self.app.post(f"/{prefix}")
        async def create_item(item: model_class.create_schema):
            return await model_class.create(item)
        
        @self.app.get(f"/{prefix}/{{item_id}}")
        async def get_item(item_id: int):
            return await model_class.get_by_id(item_id)
        
        @self.app.put(f"/{prefix}/{{item_id}}")
        async def update_item(item_id: int, item: model_class.update_schema):
            return await model_class.update(item_id, item)
        
        @self.app.delete(f"/{prefix}/{{item_id}}")
        async def delete_item(item_id: int):
            await model_class.delete(item_id)
            return {"status": "deleted"}

# Usage
route_generator = APIRouteGenerator(app)
route_generator.generate_crud_routes(User, "users")
route_generator.generate_crud_routes(Product, "products")
```

### Conditional Routing

```python
@app.route("/api/v1/users", methods=["GET"], condition=lambda: settings.api_v1_enabled)
async def get_users_v1():
    return await get_users_legacy()

@app.route("/api/v2/users", methods=["GET"], condition=lambda: settings.api_v2_enabled)
async def get_users_v2():
    return await get_users_modern()
```

## 📊 Advanced Monitoring

### Custom Metrics Collection

```python
from velithon.monitoring import MetricsCollector
import time

class BusinessMetricsCollector:
    def __init__(self):
        self.metrics = MetricsCollector()
    
    async def track_user_action(self, action: str, user_id: str, duration: float):
        self.metrics.increment(f"user_action.{action}")
        self.metrics.histogram(f"user_action.{action}.duration", duration)
        self.metrics.gauge(f"active_users", self.get_active_user_count())
    
    async def track_business_event(self, event: str, value: float):
        self.metrics.increment(f"business.{event}")
        self.metrics.gauge(f"business.{event}.value", value)

# Usage in endpoints
metrics = BusinessMetricsCollector()

@app.post("/purchase")
async def make_purchase(purchase_data: dict):
    start_time = time.time()
    
    result = await process_purchase(purchase_data)
    
    await metrics.track_user_action(
        "purchase", 
        purchase_data["user_id"], 
        time.time() - start_time
    )
    await metrics.track_business_event("revenue", purchase_data["amount"])
    
    return result
```

## 🔧 Performance Tuning

### Connection Pool Optimization

```python
import asyncio
from velithon.db import OptimizedConnectionPool

class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def initialize_pool(self):
        self.pool = await OptimizedConnectionPool.create(
            dsn=settings.database_url,
            min_size=20,
            max_size=100,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            setup=self.setup_connection
        )
    
    async def setup_connection(self, connection):
        # Optimize connection settings
        await connection.execute("SET work_mem = '256MB'")
        await connection.execute("SET effective_cache_size = '4GB'")
        await connection.execute("SET max_parallel_workers_per_gather = 4")
```

These advanced features enable you to build sophisticated, high-performance applications with Velithon. Each feature is designed to work seamlessly with the others, allowing you to create powerful, scalable systems.
