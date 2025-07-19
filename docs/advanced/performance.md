# Performance Optimization

Velithon provides various performance optimization techniques and best practices for high-performance applications.

## Overview

This guide covers performance optimization strategies, profiling techniques, and configuration options to maximize your Velithon application's performance.

## Application Configuration

```python
from velithon import Velithon

# Optimized application configuration
app = Velithon(
    debug=False,  # Disable debug mode in production
)

# Note: Compression should be handled at the server level (Granian/nginx)
# or through middleware, not application configuration
```

## Async Best Practices

```python
import asyncio
from velithon import Velithon

app = Velithon()

# Use async/await properly
@app.get("/fast-endpoint")
async def fast_endpoint():
    # Avoid blocking operations
    await asyncio.sleep(0.1)  # Non-blocking
    return {"status": "fast"}

# Batch operations when possible
@app.get("/batch-operations")
async def batch_operations():
    tasks = [
        process_item(i) for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    return {"results": results}

async def process_item(item_id):
    # Simulate async processing
    await asyncio.sleep(0.01)
    return f"processed_{item_id}"
```

## Database Optimization

```python
from velithon.di import ServiceContainer

class OptimizedDatabaseService:
    def __init__(self):
        self.connection_pool = self._create_pool()
    
    def _create_pool(self):
        # Configure connection pooling
        return {
            "min_size": 10,
            "max_size": 20,
            "max_queries": 50000,
            "max_inactive_connection_lifetime": 300
        }
    
    async def get_users_batch(self, user_ids):
        # Use batch queries instead of individual queries
        query = "SELECT * FROM users WHERE id = ANY($1)"
        return await self.execute(query, user_ids)
    
    async def get_with_cache(self, key, query_func):
        # Implement caching layer
        cached = await self.get_from_cache(key)
        if cached:
            return cached
        
        result = await query_func()
        await self.set_cache(key, result, ttl=300)
        return result

class DatabaseContainer(ServiceContainer):
    database_service = OptimizedDatabaseService()

# Use with dependency injection
from velithon.di import inject, Provide

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db_service: OptimizedDatabaseService = Provide[DatabaseContainer.database_service]
):
    return await db_service.get_user(user_id)
```

## JSON Optimization

```python
from velithon.response import JSONResponse
import orjson

# Use optimized JSON serialization
@app.get("/json-data")
async def json_data():
    large_data = {"items": [{"id": i, "name": f"item_{i}"} for i in range(1000)]}
    
    # Velithon automatically uses optimized JSON serialization
    return JSONResponse(large_data)

# Custom JSON encoder for specific needs
class CustomJSONResponse(JSONResponse):
    def render(self, content):
        return orjson.dumps(
            content,
            option=orjson.OPT_FAST_MODE | orjson.OPT_SERIALIZE_NUMPY
        )
```

## Caching Strategies

```python
from functools import lru_cache
import asyncio

# In-memory caching
@lru_cache(maxsize=1000)
def expensive_computation(input_data):
    # CPU-intensive operation
    return sum(range(input_data))

# Async caching with TTL
class AsyncCache:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    async def get(self, key, ttl=300):
        if key in self._cache:
            if asyncio.get_event_loop().time() - self._timestamps[key] < ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None
    
    async def set(self, key, value):
        self._cache[key] = value
        self._timestamps[key] = asyncio.get_event_loop().time()

cache = AsyncCache()

@app.get("/cached-data/{item_id}")
async def cached_data(item_id: int):
    cached_result = await cache.get(f"item_{item_id}")
    if cached_result:
        return cached_result
    
    # Simulate expensive operation
    result = {"id": item_id, "data": f"expensive_computation_{item_id}"}
    await cache.set(f"item_{item_id}", result)
    return result
```

## Request/Response Optimization

```python
from velithon import Request, Response

@app.middleware("http")
async def compression_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # Note: Actual compression should be handled at the server level
    # This is just for demonstration of header manipulation
    if "gzip" in request.headers.get("accept-encoding", ""):
        response.headers["content-encoding"] = "gzip"
    
    return response

# Streaming responses for large data
@app.get("/large-data")
async def large_data():
    async def generate_data():
        for i in range(10000):
            yield f"data_chunk_{i}\n"
    
    return Response(
        generate_data(),
        media_type="text/plain",
        headers={"content-disposition": "attachment; filename=data.txt"}
    )
```

## Profiling and Monitoring

```python
import time
from functools import wraps

def profile_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            print(f"Endpoint {func.__name__} took {duration:.4f} seconds")
    return wrapper

@app.get("/profiled-endpoint")
@profile_endpoint
async def profiled_endpoint():
    await asyncio.sleep(0.1)
    return {"message": "profiled"}

# Memory profiling
import tracemalloc

@app.middleware("http")
async def memory_profiling_middleware(request: Request, call_next):
    tracemalloc.start()
    response = await call_next(request)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    response.headers["X-Memory-Current"] = str(current)
    response.headers["X-Memory-Peak"] = str(peak)
    
    return response
```

## Production Optimizations

```python
# Use Granian RSGI server for production via CLI
# velithon run --app main:app --workers 4 --runtime-mode mt --loop auto --http auto --log-level INFO

# For advanced configuration, create a production script
def configure_production():
    from velithon import Velithon
    
    app = Velithon(
        debug=False,  # Disable debug in production
    )
    
    # Your app configuration here...
    
    return app

# Run with CLI:
# velithon run --app production:app --host 0.0.0.0 --port 8000 --workers 4 --runtime-mode mt --loop auto --http auto --log-level INFO
```
```

## Performance Tips

1. **Use async/await consistently**
2. **Implement connection pooling**
3. **Enable compression at server level (Granian/nginx)**
4. **Use caching strategies**
5. **Optimize database queries**
6. **Profile your application regularly**
7. **Monitor memory usage**
8. **Use Granian RSGI server for production**
9. **Configure proper worker counts**
10. **Minimize middleware overhead**
