# JSON Responses

Velithon provides high-performance JSON serialization that automatically optimizes for the best performance based on your data.

## Overview

JSON handling in Velithon is now simplified:
- **JSONResponse**: Single, optimized JSON response class for all use cases
- **Automatic Optimization**: Built-in optimization that adapts to your data size and complexity
- **No Configuration Needed**: Works efficiently out of the box
- **Memory-Efficient Processing**: Optimized for both small and large datasets

## Unified JSON Responses

### All Data Sizes Handled Efficiently

```python
from velithon import Velithon
from velithon.responses import JSONResponse
import datetime
import decimal

app = Velithon()

@app.get("/users")
async def get_users():
    """Large dataset automatically optimized"""
    users = []
    for i in range(10000):  # Large dataset
        users.append({
            "id": i,
            "name": f"User {i}",
            "created_at": datetime.datetime.now(),
            "balance": decimal.Decimal("100.50")
        })
    
    # Automatically optimized for large datasets
    return JSONResponse(users)

@app.get("/small-data")
async def get_small_data():
    """Small dataset uses fast path"""
    data = {"message": "Hello", "count": 42}
    
    # Uses fast path for small objects
    return JSONResponse(data)

@app.get("/medium-data")
async def get_medium_data():
    """Medium dataset automatically handled"""
    data = {"message": "Hello", "count": 42}
    return JSONResponse(data)
```

### Configuration Options

```python
from velithon.responses import JSONResponse

@app.get("/configured-response")
async def get_configured_response():
    large_dataset = generate_large_data()
    
    return JSONResponse(
        large_dataset,
        parallel_threshold=5000,    # Use parallel processing for 5000+ items
        use_parallel_auto=True,     # Automatically decide when to use parallel
        enable_caching=True,        # Cache frequently serialized objects
        max_cache_size=500          # Maximum cached objects
    data = {"products": list(range(1000))}
    
    # All JSON responses are now automatically optimized
    return JSONResponse(data)
```

## Batch Processing Made Simple

### Efficient Collection Handling

```python
from velithon.responses import JSONResponse

@app.get("/users/batch")
async def get_users_batch():
    """Efficiently process and return large collections"""
    
    # Generate a large collection
    users = []
    for i in range(50000):
        users.append({
            "id": i,
            "name": f"User {i}",
            "email": f"user{i}@example.com",
            "created_at": datetime.datetime.now()
        })
    
    # JSONResponse automatically optimizes large collections
    return JSONResponse(users)

@app.get("/analytics/data")
async def get_analytics_data():
    """Process analytics data efficiently"""
    
    analytics_data = []
    for i in range(20000):
        analytics_data.append({
            "date": datetime.date.today(),
            "value": i * 1.5,
            "category": f"Category {i % 10}"
        })
    
    # No special configuration needed
    return JSONResponse(analytics_data)

@app.get("/products/export")
async def export_products():
    """Export large product catalog"""
    
    def generate_products():
        for i in range(100000):
            yield {
                "id": i,
                "name": f"Product {i}",
                "price": round(10.0 + (i * 0.01), 2),
                "in_stock": i % 3 != 0
            }
    
    # JSONResponse handles generators efficiently
    return JSONResponse(generate_products())
```

## Streaming JSON with StreamingResponse

### JSON Streaming for Large Datasets

```python
from velithon.responses import StreamingResponse
import json
import asyncio

@app.get("/events/stream")
async def stream_events():
    """Stream JSON events using StreamingResponse"""
    
    async def json_event_generator():
        event_id = 0
        
        # Start JSON array
        yield '{"events": ['
        
        first_event = True
        while event_id < 1000:  # Stream 1000 events
            if not first_event:
                yield ','
            
            event_data = {
                "id": event_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "type": "update",
                "data": f"Event data {event_id}"
            }
            
            yield json.dumps(event_data)
            first_event = False
            event_id += 1
            
            await asyncio.sleep(0.1)  # Small delay between events
        
        # Close JSON array and object
        yield ']}'
    
    return StreamingResponse(
        json_event_generator(),
        media_type="application/json"
    )

@app.get("/data/export")
async def export_large_dataset():
    """Export large dataset as streaming JSON"""
    
    async def data_stream():
        # Start with opening array
        yield '{"data": ['
        
        first_item = True
        
        # Simulate large dataset
        for i in range(50000):
            if not first_item:
                yield ','
            
            item_data = {
                "id": i,
                "value": i * 2.5,
                "description": f"Item {i}",
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            yield json.dumps(item_data)
            first_item = False
            
            # Yield control periodically
            if i % 1000 == 0:
                await asyncio.sleep(0)
        
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

## Performance Best Practices

### Choosing the Right Response Type

```python
from velithon.responses import JSONResponse, JSONResponse, JSONResponse, StreamingResponse

@app.get("/small-data")
async def get_small_data():
    """Use JSONResponse for small, simple data"""
    data = {"status": "ok", "count": 5}
    return JSONResponse(data)  # Fast for small objects

@app.get("/medium-data")
async def get_medium_data():
    """Use JSONResponse for medium to large data"""
    data = [{"id": i, "name": f"Item {i}"} for i in range(5000)]
    return JSONResponse(data)  # Parallel processing

@app.get("/large-collection")
async def get_large_collection():
    """Use JSONResponse for very large collections"""
    data = [{"id": i, "value": i * 2} for i in range(100000)]
    return JSONResponse(data)  # Optimized for large batches

@app.get("/huge-dataset")
async def get_huge_dataset():
    """Use StreamingResponse for extremely large datasets"""
    
    async def stream_data():
        yield '{"items": ['
        for i in range(1000000):  # 1 million items
            if i > 0:
                yield ','
            yield json.dumps({"id": i, "value": i})
            
            # Yield control every 1000 items
            if i % 1000 == 0:
                await asyncio.sleep(0)
        yield ']}'
    
    return StreamingResponse(stream_data(), media_type="application/json")
```

### Memory-Efficient Patterns

```python
@app.get("/efficient-pagination")
async def get_efficient_pagination(page: int = 1, size: int = 100):
    """Memory-efficient pagination"""
    
    # Don't load all data into memory
    offset = (page - 1) * size
    
    # Fetch only what's needed
    items = fetch_items_from_db(offset=offset, limit=size)
    total = count_items_in_db()
    
    response_data = {
        "items": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size
        }
    }
    
    return JSONResponse(response_data)

@app.get("/generator-based")
async def get_generator_based():
    """Use generators to avoid loading everything into memory"""
    
    def item_generator():
        # Fetch and yield items one by one
        for i in range(10000):
            # Simulate database fetch
            yield {"id": i, "data": f"Item {i}"}
    
    # JSONResponse handles generators efficiently
    return JSONResponse(item_generator())
```

## Middleware Integration

### Compression with JSON Responses

```python
from velithon.middleware import Middleware, CompressionMiddleware

# CompressionMiddleware works with all JSON response types
app = Velithon(middleware=[
    Middleware(CompressionMiddleware, 
               compression_level=6,
               minimum_size=1024)
])

@app.get("/compressed-json")
async def get_compressed_json():
    """Large JSON response that will be automatically compressed"""
    
    large_data = []
    for i in range(10000):
        large_data.append({
            "id": i,
            "description": f"This is item {i} with some description text",
            "metadata": {"category": f"Category {i % 10}", "priority": i % 5}
        })
    
    # Response will be automatically compressed if larger than minimum_size
    return JSONResponse(large_data)
```

### Custom Middleware for JSON Processing

```python
from velithon.middleware.base import BaseHTTPMiddleware
import time
import logging

class JSONPerformanceMiddleware(BaseHTTPMiddleware):
    """Monitor JSON response performance"""
    
    def __init__(self, app):
        super().__init__(app)
        self.response_times = []
    
    async def process_http_request(self, scope, protocol):
        start_time = time.time()
        
        await self.app(scope, protocol)
        
        # Log performance for JSON responses
        if scope.get("path", "").endswith(("/json", "/api")):
            duration = time.time() - start_time
            self.response_times.append(duration)
            
            if len(self.response_times) % 100 == 0:
                avg_time = sum(self.response_times[-100:]) / 100
                logging.info(f"JSON API avg response time: {avg_time:.3f}s")

app = Velithon(middleware=[Middleware(JSONPerformanceMiddleware)])
```

## Real-World Examples

### E-commerce Product Catalog

```python
@app.get("/products/catalog")
async def get_product_catalog(
    category: str = None,
    page: int = 1,
    size: int = 50,
    include_reviews: bool = False
):
    """Optimized product catalog endpoint"""
    
    # For small result sets, use standard response
    if size <= 50 and not include_reviews:
        products = fetch_products(category=category, page=page, size=size)
        return JSONResponse({
            "products": products,
            "page": page,
            "total": len(products)
        })
    
    # For larger result sets or with reviews, use optimized response
    elif size <= 1000:
        products = fetch_products_with_details(
            category=category, 
            page=page, 
            size=size,
            include_reviews=include_reviews
        )
        return JSONResponse({
            "products": products,
            "page": page,
            "size": size
        })
    
    # For very large exports, use batch response
    else:
        def product_generator():
            offset = 0
            batch_size = 1000
            
            while True:
                batch = fetch_products(
                    category=category,
                    offset=offset,
                    limit=batch_size
                )
                if not batch:
                    break
                    
                for product in batch:
                    yield product
                
                offset += batch_size
        
        return JSONResponse(product_generator())

@app.get("/analytics/dashboard")
async def get_analytics_dashboard():
    """Complex analytics dashboard with multiple data sources"""
    
    # Gather data from multiple sources
    sales_data = fetch_sales_metrics()
    user_data = fetch_user_metrics()
    performance_data = fetch_performance_metrics()
    
    dashboard_data = {
        "sales": sales_data,
        "users": user_data,
        "performance": performance_data,
        "generated_at": datetime.datetime.now().isoformat()
    }
    
    # Use optimized response for complex dashboard data
    return JSONResponse(dashboard_data)
```

## Performance Guidelines

### When to Use Each Response Type

1. **JSONResponse**: 
   - Small, simple objects (< 100 items)
   - Static or cached data
   - Simple key-value pairs

2. **JSONResponse**:
   - Medium to large datasets (100-10,000 items)
   - Complex nested objects
   - When you need automatic optimization

3. **JSONResponse**:
   - Very large collections (10,000+ items)
   - Generator-based data
   - Memory-constrained environments

4. **StreamingResponse**:
   - Extremely large datasets (100,000+ items)
   - Real-time data streams
   - When client needs to start processing before complete response

### Performance Tips

- Use generators to avoid loading large datasets into memory
- Configure appropriate `parallel_threshold` for your use case
- Enable compression for responses > 1KB
- Consider pagination for user-facing APIs
- Monitor response times and adjust strategies accordingly
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
    return JSONResponse(
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
    
    return JSONResponse(
        products,
        serialization_context=user_permissions
    )
```

## Best Practices

### 1. Choose the Right Response Type

```python
# Small, simple data - use JSONResponse
@app.get("/user/profile")
async def get_profile():
    return JSONResponse({"name": "John", "email": "john@example.com"})

# Large datasets - use JSONResponse
@app.get("/users/all")
async def get_all_users():
    return JSONResponse(get_users_generator())

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
    
    return JSONResponse({
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
            return JSONResponse(data)
        else:
            # Use optimized response for normal size
            return JSONResponse(data)
## Summary

Velithon's JSON optimization features provide significant performance improvements for API responses:

- **JSONResponse**: Rust-based parallel processing for large datasets with configurable thresholds
- **JSONResponse**: Efficient handling of very large collections and generators
- **StreamingResponse**: Memory-efficient streaming for extremely large datasets using standard streaming
- **Middleware Integration**: Works seamlessly with compression and other middleware

Choose the appropriate response type based on your data size and performance requirements:

- Small data (< 100 items): `JSONResponse`
- Medium data (100-10,000 items): `JSONResponse` 
- Large collections (10,000+ items): `JSONResponse`
- Huge datasets (100,000+ items): `StreamingResponse` with JSON

## Next Steps

- [Gateway & Proxy System →](gateway.md)
- [VSP Protocol →](vsp.md) 
- [Response Types →](../user-guide/request-response.md)
- [Middleware →](../user-guide/middleware.md)
