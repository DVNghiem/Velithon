# JSON Responses

Velithon provides high-performance JSON serialization using orjson with minimal, intelligent caching.

## Overview

JSON handling in Velithon is streamlined and fast:
- **orjson-only**: Uses orjson exclusively for maximum performance
- **Smart Caching**: Caches only small strings (≤50 chars) to avoid overhead
- **No Configuration Needed**: Works efficiently out of the box with sensible defaults
- **Memory-Efficient**: Minimal memory footprint with cache size limits

## Simple, Fast JSON Responses

### All Data Handled with orjson

```python
from velithon import Velithon
from velithon.responses import JSONResponse
import datetime
import decimal

app = Velithon()

@app.get("/users")
async def get_users():
    """Large dataset processed with orjson"""
    users = []
    for i in range(10000):  # Large dataset
        users.append({
            "id": i,
            "name": f"User {i}",
            "created_at": datetime.datetime.now(),
            "balance": decimal.Decimal("100.50")
        })
    
    # orjson handles large datasets efficiently
    return JSONResponse(users)

@app.get("/small-data")
async def get_small_data():
    """Small strings may be cached automatically"""
    data = {"message": "Hello", "count": 42}
    
    # Small responses benefit from intelligent caching
    return JSONResponse(data)

@app.get("/complex-data")
async def get_complex_data():
    """Complex objects processed directly with orjson"""
    """Complex objects processed directly with orjson"""
    data = {
        "users": list(range(1000)),
        "metadata": {"processed_at": datetime.datetime.now()},
        "settings": {"cache_enabled": True}
    }
    
    # orjson handles all JSON serialization efficiently
    return JSONResponse(data)
```

## Simple Architecture

### How It Works

```python
from velithon._utils import FastJSONEncoder

# The FastJSONEncoder is minimal and focused
encoder = FastJSONEncoder()

# Only small strings are cached to avoid overhead
small_response = '{"status": "ok"}'  # This might be cached
large_response = {"data": list(range(1000))}  # Direct orjson encoding

# orjson backend is used exclusively
print(encoder._backend)  # 'orjson'
```

## Efficient Collection Handling

### Direct orjson Processing

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
    
    # orjson processes large collections efficiently
    return JSONResponse(users)

async def get_analytics_data():
    """Stream large analytics datasets efficiently"""
    analytics = {
        "metrics": list(range(25000)),
        "timestamps": [datetime.datetime.now() for _ in range(25000)],
        "metadata": {"generated_at": datetime.datetime.now()}
    }
    
    # orjson handles large analytical data efficiently
    return JSONResponse(analytics)
```

## Performance Characteristics

### orjson Benefits

- **Speed**: Up to 5.4M simple operations per second
- **Memory Efficiency**: Low memory overhead compared to standard library
- **Type Support**: Native support for datetime, decimal, numpy arrays
- **Unicode**: Proper UTF-8 handling for international content

### Intelligent Caching

```python
# Only small strings (≤50 chars) are cached
short_message = "ok"                    # Cached
medium_message = "x" * 60              # Not cached (too long)
complex_object = {"data": [1, 2, 3]}   # Not cached (not a string)

# Cache is limited to 50 entries and 100 bytes per entry
# This prevents memory bloat while providing benefits for common small responses
```

## Best Practices

### Optimal Usage

```python
@app.get("/status")
async def get_status():
    """Short responses benefit from caching"""
    return JSONResponse({"status": "healthy"})

@app.get("/data")
async def get_data():
    """Large data uses orjson's full power"""
    return JSONResponse({
        "items": large_dataset,
        "count": len(large_dataset),
        "processed_at": datetime.datetime.now()
    })
```

### What Changed from Complex Versions

**Removed Features** (for better performance):
- Multiple JSON backend fallbacks (ujson, stdlib json)
- Complex parallel processing configuration
- Advanced caching for complex objects
- Cache hit/miss statistics tracking
- Automatic optimization thresholds

**Why Simplified?**
- orjson is consistently fastest for all use cases
- Complex caching often added overhead without benefit
- Statistics tracking consumed CPU cycles
- Simpler code is more maintainable and predictable

## Migration from Complex Versions

### Before (Complex)
```python
# Old complex configuration
return JSONResponse(
    data,
    parallel_threshold=5000,
    use_parallel_auto=True,
    enable_caching=True,
    max_cache_size=500
)
```

### After (Simplified)
```python
# New simplified approach
return JSONResponse(data)  # That's it! orjson handles everything efficiently
```

## Summary

Velithon's simplified JSON handling provides excellent performance with minimal complexity:

- **orjson-only**: Consistent, fast JSON encoding for all use cases
- **Smart Caching**: Only small strings are cached to avoid overhead  
- **Zero Configuration**: Works efficiently out of the box
- **Memory Efficient**: Minimal cache footprint with size limits

### Performance Characteristics
- Up to **5.4M operations/second** for simple JSON encoding
- **Low memory overhead** compared to complex caching systems
- **Predictable performance** without adaptive algorithms
- **Native support** for datetime, decimal, and numpy types

### Simple API
```python
from velithon.responses import JSONResponse

# That's it - orjson handles everything efficiently
return JSONResponse(your_data)
```

## Next Steps

- [Memory Optimization →](memory-optimization.md)
- [Gateway & Proxy System →](gateway.md)
- [Response Types →](../user-guide/request-response.md)
- [Middleware →](../user-guide/middleware.md)
