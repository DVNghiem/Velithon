# JSON Optimization

Velithon provides advanced JSON optimization features to maximize performance for API responses, including batch processing, streaming, and memory-efficient serialization.

## Overview

JSON optimization in Velithon includes:
- Optimized JSON serialization with custom encoders
- Batch JSON responses for multiple items
- Streaming JSON for large datasets
- Memory-efficient processing
- Custom serialization strategies

## Optimized JSON Responses

### Basic Optimized Responses

```python
from velithon import Velithon
from velithon.responses import OptimizedJSONResponse, json_response
from typing import List, Dict, Any
import datetime
import decimal

app = Velithon()

@app.get("/users")
async def get_users():
    users = [
        {"id": 1, "name": "John", "created_at": datetime.datetime.now()},
        {"id": 2, "name": "Jane", "created_at": datetime.datetime.now()}
    ]
    
    # Automatically handles datetime serialization
    return OptimizedJSONResponse(users)

@app.get("/financial-data")
async def get_financial_data():
    data = {
        "balance": decimal.Decimal("1234.56"),
        "transactions": [
            {"amount": decimal.Decimal("100.00"), "date": datetime.date.today()}
        ]
    }
    
    # Handles Decimal and date objects
    return OptimizedJSONResponse(data)
```

### Custom JSON Encoders

```python
from velithon.responses.json import JSONEncoder
import uuid
import enum

class Status(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, Status):
            return obj.value
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return super().default(obj)

# Configure app with custom encoder
app = Velithon()
app.json_encoder = CustomJSONEncoder

@app.get("/custom-data")
async def get_custom_data():
    data = {
        "id": uuid.uuid4(),
        "status": Status.ACTIVE,
        "tags": {"important", "featured"},  # set
        "metadata": CustomObject()  # object with to_dict method
    }
    
    return OptimizedJSONResponse(data)
```

## Batch JSON Responses

### Batch Processing

```python
from velithon.responses import BatchJSONResponse, batch_json_response
from typing import List, Generator

@app.get("/users/batch")
async def get_users_batch():
    """Return large number of users efficiently"""
    
    def get_users_generator() -> Generator[Dict, None, None]:
        # Process users in batches from database
        offset = 0
        batch_size = 1000
        
        while True:
            users = fetch_users_from_db(offset=offset, limit=batch_size)
            if not users:
                break
                
            for user in users:
                yield {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at
                }
            
            offset += batch_size
    
    return BatchJSONResponse(get_users_generator())

@app.get("/analytics/data")
async def get_analytics_data():
    """Batch process analytics data"""
    
    async def process_analytics():
        # Process data in chunks to avoid memory issues
        for chunk in get_analytics_chunks():
            processed_chunk = []
            for item in chunk:
                processed_item = {
                    "date": item.date,
                    "metrics": calculate_metrics(item),
                    "summary": generate_summary(item)
                }
                processed_chunk.append(processed_item)
            
            yield processed_chunk
    
    return batch_json_response(await process_analytics())
```

### Batch Configuration

```python
from velithon import Velithon
from velithon.middleware import Middleware
from velithon.middleware.json import JSONOptimizationMiddleware

app = Velithon(middleware=[
    Middleware(JSONOptimizationMiddleware,
               batch_size=1000,
               memory_limit=100*1024*1024,  # 100MB
               compression_enabled=True,
               streaming_threshold=10000)  # Items count
])

@app.get("/large-dataset")
async def get_large_dataset():
    """Automatically uses batch processing for large datasets"""
    data = fetch_large_dataset()  # Returns 50,000+ items
    
    # Automatically batched based on middleware configuration
    return OptimizedJSONResponse(data)
```

## Streaming JSON

### Server-Sent Events with JSON

```python
from velithon.responses import StreamingJSONResponse
import asyncio
import json

@app.get("/events/stream")
async def stream_events():
    """Stream JSON events in real-time"""
    
    async def event_generator():
        event_id = 0
        
        while True:
            # Simulate real-time data
            event_data = {
                "id": event_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "data": await fetch_real_time_data(),
                "type": "update"
            }
            
            yield event_data
            event_id += 1
            await asyncio.sleep(1)  # Wait 1 second between events
    
    return StreamingJSONResponse(event_generator())

@app.get("/logs/tail")
async def tail_logs():
    """Stream log entries as JSON"""
    
    async def log_generator():
        last_position = get_log_position()
        
        while True:
            new_logs = read_logs_since(last_position)
            
            for log_entry in new_logs:
                yield {
                    "timestamp": log_entry.timestamp,
                    "level": log_entry.level,
                    "message": log_entry.message,
                    "metadata": log_entry.metadata
                }
                last_position = log_entry.position
            
            await asyncio.sleep(0.5)  # Check for new logs every 500ms
    
    return StreamingJSONResponse(log_generator())
```

### Large File Processing

```python
@app.get("/data/export")
async def export_large_dataset():
    """Export large dataset as streaming JSON"""
    
    async def data_stream():
        # Start with opening array
        yield '{"data": ['
        
        first_item = True
        
        # Process data in chunks
        for chunk in get_data_chunks(chunk_size=5000):
            for item in chunk:
                if not first_item:
                    yield ','
                
                # Serialize each item individually
                yield json.dumps({
                    "id": item.id,
                    "processed_data": process_item(item),
                    "metadata": item.metadata
                })
                
                first_item = False
        
        # Close array and object
        yield ']}'
    
    headers = {
        "Content-Disposition": "attachment; filename=export.json",
        "Content-Type": "application/json"
    }
    
    return StreamingResponse(
        data_stream(),
        media_type="application/json",
        headers=headers
    )
```

## Memory Optimization

### Lazy Loading and Pagination

```python
from velithon.responses import LazyJSONResponse
from dataclasses import dataclass

@dataclass
class PaginatedResponse:
    items: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

@app.get("/products")
async def get_products(page: int = 1, per_page: int = 50):
    """Memory-efficient paginated response"""
    
    # Only fetch the current page
    offset = (page - 1) * per_page
    products = fetch_products(offset=offset, limit=per_page)
    total = count_products()
    
    response_data = PaginatedResponse(
        items=products,
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + per_page < total,
        has_prev=page > 1
    )
    
    return LazyJSONResponse(response_data)

@app.get("/users/{user_id}/posts")
async def get_user_posts(user_id: int, page: int = 1):
    """Lazy load user posts with related data"""
    
    def load_posts():
        # Only load when actually needed
        posts = fetch_user_posts(user_id, page=page)
        
        for post in posts:
            # Lazy load comments only when serializing
            post.comments = lambda: fetch_post_comments(post.id)
            post.tags = lambda: fetch_post_tags(post.id)
        
        return posts
    
    return LazyJSONResponse({"posts": load_posts})
```

### Memory Pool Management

```python
from velithon.optimization import MemoryPool, ObjectPool

class JSONResponsePool:
    def __init__(self):
        self.memory_pool = MemoryPool(max_size=50*1024*1024)  # 50MB
        self.object_pool = ObjectPool(max_objects=1000)
    
    def get_optimized_response(self, data):
        """Get memory-optimized JSON response"""
        
        # Use object pooling for response objects
        response_obj = self.object_pool.get_object()
        
        try:
            # Use memory pool for serialization
            with self.memory_pool.allocate() as memory_block:
                serialized = json.dumps(data, ensure_ascii=False)
                
                if len(serialized) > memory_block.size:
                    # Use streaming for large responses
                    return StreamingJSONResponse(data)
                else:
                    response_obj.content = serialized
                    return response_obj
                    
        finally:
            # Return object to pool
            self.object_pool.return_object(response_obj)

# Global pool instance
json_pool = JSONResponsePool()

@app.get("/memory-optimized")
async def memory_optimized_endpoint():
    large_data = generate_large_dataset()
    return json_pool.get_optimized_response(large_data)
```

## Performance Monitoring

### Response Time Tracking

```python
from velithon.middleware import Middleware
import time
import logging

class JSONPerformanceMiddleware:
    def __init__(self, app):
        self.app = app
        self.response_times = []
        self.serialization_times = []
    
    async def __call__(self, scope, protocol):
        if scope["type"] == "http":
            start_time = time.time()
            
            # Patch JSON serialization to track time
            original_dumps = json.dumps
            
            def timed_dumps(*args, **kwargs):
                serialize_start = time.time()
                result = original_dumps(*args, **kwargs)
                serialize_time = time.time() - serialize_start
                self.serialization_times.append(serialize_time)
                return result
            
            json.dumps = timed_dumps
            
            try:
                await self.app(scope, protocol)
            finally:
                total_time = time.time() - start_time
                self.response_times.append(total_time)
                json.dumps = original_dumps  # Restore original
                
                # Log performance metrics
                if len(self.response_times) % 100 == 0:
                    avg_response = sum(self.response_times[-100:]) / 100
                    avg_serialization = sum(self.serialization_times[-100:]) / 100
                    
                    logging.info(f"JSON Performance - "
                               f"Avg Response: {avg_response:.3f}s, "
                               f"Avg Serialization: {avg_serialization:.3f}s")
        else:
            await self.app(scope, protocol)

app = Velithon(middleware=[Middleware(JSONPerformanceMiddleware)])

@app.get("/performance-metrics")
async def get_performance_metrics():
    """Get JSON performance metrics"""
    middleware = app.middleware[0]  # Assuming first middleware
    
    if hasattr(middleware, 'response_times') and middleware.response_times:
        recent_times = middleware.response_times[-1000:]  # Last 1000 requests
        
        return OptimizedJSONResponse({
            "total_requests": len(middleware.response_times),
            "average_response_time": sum(recent_times) / len(recent_times),
            "min_response_time": min(recent_times),
            "max_response_time": max(recent_times),
            "p95_response_time": sorted(recent_times)[int(len(recent_times) * 0.95)],
            "average_serialization_time": sum(middleware.serialization_times[-1000:]) / len(middleware.serialization_times[-1000:])
        })
    
    return OptimizedJSONResponse({"message": "No metrics available yet"})
```

## Compression and Caching

### Response Compression

```python
from velithon.middleware.compression import JSONCompressionMiddleware

app = Velithon(middleware=[
    Middleware(JSONCompressionMiddleware,
               compression_level=6,
               minimum_size=1024,
               algorithms=['gzip', 'br', 'deflate'])
])

@app.get("/compressed-data")
async def get_compressed_data():
    """Large response that will be automatically compressed"""
    large_data = generate_large_json_data()
    
    # Response will be automatically compressed if larger than minimum_size
    return OptimizedJSONResponse(large_data)
```

### Response Caching

```python
from velithon.middleware.cache import JSONCacheMiddleware
import hashlib

class JSONCacheMiddleware:
    def __init__(self, app, cache_ttl=300):
        self.app = app
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    async def __call__(self, scope, protocol):
        if scope["type"] == "http" and scope["method"] == "GET":
            # Create cache key from path and query
            cache_key = hashlib.md5(
                f"{scope['path']}?{scope['query_string'].decode()}".encode()
            ).hexdigest()
            
            # Check cache
            if cache_key in self.cache:
                cached_response, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    # Return cached response
                    await send_cached_response(protocol, cached_response)
                    return
            
            # Capture response for caching
            response_data = await self.capture_response(scope, protocol)
            
            # Cache the response
            self.cache[cache_key] = (response_data, time.time())
        else:
            await self.app(scope, protocol)

app = Velithon(middleware=[
    Middleware(JSONCacheMiddleware, cache_ttl=600)  # 10 minutes
])
```

## Custom Serialization Strategies

### Field-Specific Serialization

```python
from velithon.serialization import FieldSerializer, SerializationStrategy

class UserSerializer(FieldSerializer):
    """Custom serializer for User objects"""
    
    def serialize_email(self, email: str, context: dict) -> str:
        # Mask email for non-admin users
        if not context.get('is_admin', False):
            return email[:3] + "***@" + email.split('@')[1]
        return email
    
    def serialize_password(self, password: str, context: dict) -> str:
        # Never serialize passwords
        return "[HIDDEN]"
    
    def serialize_created_at(self, date: datetime.datetime, context: dict) -> str:
        # Format dates consistently
        return date.isoformat()

# Register custom serializer
SerializationStrategy.register(User, UserSerializer())

@app.get("/users/{user_id}")
async def get_user(user_id: int, request: Request):
    user = get_user_by_id(user_id)
    is_admin = check_admin_permission(request)
    
    # Pass serialization context
    return OptimizedJSONResponse(
        user,
        serialization_context={"is_admin": is_admin}
    )
```

### Conditional Field Inclusion

```python
from velithon.serialization import ConditionalSerializer

class ProductSerializer(ConditionalSerializer):
    """Serialize products with conditional fields"""
    
    def get_fields(self, obj, context: dict) -> list:
        base_fields = ['id', 'name', 'price']
        
        # Include cost only for admin users
        if context.get('is_admin'):
            base_fields.append('cost')
        
        # Include inventory for inventory managers
        if context.get('can_view_inventory'):
            base_fields.extend(['stock_quantity', 'reorder_level'])
        
        # Include analytics for premium users
        if context.get('is_premium'):
            base_fields.extend(['view_count', 'conversion_rate'])
        
        return base_fields

@app.get("/products")
async def get_products(request: Request):
    products = fetch_all_products()
    user_permissions = get_user_permissions(request)
    
    return OptimizedJSONResponse(
        products,
        serialization_context=user_permissions
    )
```

## Best Practices

### 1. Choose the Right Response Type

```python
# Small, simple data - use OptimizedJSONResponse
@app.get("/user/profile")
async def get_profile():
    return OptimizedJSONResponse({"name": "John", "email": "john@example.com"})

# Large datasets - use BatchJSONResponse
@app.get("/users/all")
async def get_all_users():
    return BatchJSONResponse(get_users_generator())

# Real-time data - use StreamingJSONResponse
@app.get("/events")
async def stream_events():
    return StreamingJSONResponse(event_generator())

# Memory-constrained environments - use LazyJSONResponse
@app.get("/reports/large")
async def get_large_report():
    return LazyJSONResponse(lambda: generate_report())
```

### 2. Monitor Performance

```python
import psutil
import gc

@app.get("/health/json-performance")
async def json_performance_health():
    """Monitor JSON processing performance"""
    
    # Check memory usage
    memory_percent = psutil.virtual_memory().percent
    
    # Check garbage collection stats
    gc_stats = gc.get_stats()
    
    # Check response times
    avg_response_time = get_average_response_time()
    
    return OptimizedJSONResponse({
        "memory_usage_percent": memory_percent,
        "gc_collections": sum(stat['collections'] for stat in gc_stats),
        "average_response_time": avg_response_time,
        "status": "healthy" if memory_percent < 80 and avg_response_time < 0.1 else "warning"
    })
```

### 3. Error Handling for Large Responses

```python
from velithon.exceptions import JSONSerializationError

@app.get("/large-data-safe")
async def get_large_data_safely():
    """Safely handle large data serialization"""
    
    try:
        data = fetch_potentially_large_dataset()
        
        # Check data size before serialization
        estimated_size = estimate_json_size(data)
        
        if estimated_size > 100 * 1024 * 1024:  # 100MB
            # Use streaming for very large responses
            return StreamingJSONResponse(data_generator(data))
        elif estimated_size > 10 * 1024 * 1024:  # 10MB
            # Use batch processing for large responses
            return BatchJSONResponse(data)
        else:
            # Use optimized response for normal size
            return OptimizedJSONResponse(data)
            
    except MemoryError:
        return OptimizedJSONResponse(
            {"error": "Dataset too large", "suggestion": "Use pagination"},
            status_code=413
        )
    except JSONSerializationError as e:
        return OptimizedJSONResponse(
            {"error": "Serialization failed", "details": str(e)},
            status_code=500
        )
```

## Next Steps

- [Performance Optimization →](performance.md)
- [Response Types →](../user-guide/request-response.md)
- [Middleware →](../user-guide/middleware.md)
