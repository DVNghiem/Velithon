# Memory Optimization Guide

Velithon includes comprehensive memory optimization features designed to minimize memory usage, reduce allocations, and improve overall performance. This guide covers all the memory optimization components and how to use them effectively.

## Overview

The memory optimization system consists of several key components:

1. **Memory Pool**: Efficient allocation and reuse of memory chunks
2. **String Interner**: Reduces memory usage by reusing identical strings
3. **Memory-Aware LRU Cache**: Intelligent caching with memory limits
4. **Optimized JSON Responses**: Memory-efficient JSON serialization with caching
5. **Background Task Memory Management**: Bounded queues and memory pressure handling

## Core Components

### Memory Pool

The `MemoryPool` provides efficient allocation and reuse of memory chunks to reduce allocation overhead.

```python
from velithon._velithon import MemoryPool

# Create a memory pool
pool = MemoryPool(max_size_per_pool=1024)

# Allocate memory
ptr = pool.allocate(256)  # Allocate 256 bytes

# Deallocate when done
pool.deallocate(ptr, 256)

# Get statistics
stats = pool.get_stats()
print(f"Cache hit rate: {stats['cache_hit_rate_percent']}%")
print(f"Peak memory: {stats['peak_allocated_bytes']} bytes")
```

### String Interner

The `StringInterner` reduces memory usage by ensuring that identical strings share the same memory location.

```python
from velithon._velithon import StringInterner

interner = StringInterner()

# Intern strings (identical strings will share memory)
email1 = interner.intern("user@example.com")
email2 = interner.intern("user@example.com")  # Same memory as email1

# Get statistics
stats = interner.get_stats()
print(f"Intern hit rate: {stats['hit_rate_percent']}%")

# Cleanup dead references
cleaned = interner.cleanup()
print(f"Cleaned up {cleaned} dead references")
```

### Memory-Aware LRU Cache

The `MemoryAwareLRUCache` provides intelligent caching with both entry count and memory size limits.

```python
from velithon._velithon import MemoryAwareLRUCache

# Create cache with limits
cache = MemoryAwareLRUCache(
    max_entries=1000,      # Maximum number of entries
    max_memory_mb=100      # Maximum memory usage in MB
)

# Store and retrieve values
cache.put("key1", {"data": "value"})
value = cache.get("key1")

# Get comprehensive statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
print(f"Memory usage: {stats['memory_mb']} MB")
print(f"Entries: {stats['entries']}")
```

## High-Level Memory Management

### Global Memory Handler

Velithon provides a global memory handler that coordinates all memory optimization components:

```python
from velithon.memory import (
    get_global_memory_handler,
    configure_global_memory_handler,
    get_memory_stats,
    cleanup_memory
)

# Configure the global handler
configure_global_memory_handler(
    memory_pool_size=2048,
    enable_response_caching=True,
    cache_max_entries=1000,
    cache_max_memory_mb=100
)

# Get the handler
handler = get_global_memory_handler()

# Cache a response
handler.cache_response("cache_key", response_data)

# Retrieve cached response
cached = handler.get_cached_response("cache_key")

# Get comprehensive memory statistics
stats = get_memory_stats()
print(f"Pool cache hit rate: {stats['pool_cache_hit_rate_percent']}%")
print(f"Total memory usage: {stats['cache_memory_mb']} MB")

# Perform cleanup
cleanup_stats = cleanup_memory()
print(f"Collected {cleanup_stats['gc_objects_collected']} objects")
```

### Memory-Optimized Response Cache

For response-specific caching with string interning:

```python
from velithon.memory import MemoryOptimizedResponseCache

cache = MemoryOptimizedResponseCache(
    max_entries=500,
    max_memory_mb=50,
    enable_string_interning=True,
    gc_threshold=100  # Force GC every 100 requests
)

# Cache responses
success = cache.put("response_key", response_data)

# Retrieve responses
response = cache.get("response_key")

# Get detailed statistics
stats = cache.get_stats()
print(f"Cache hit rate: {stats['cache_hit_rate_percent']}%")
print(f"String interner hit rate: {stats['interner_hit_rate_percent']}%")
```

## Optimized JSON Responses

### Basic Usage

```python
from velithon.responses.json_optimized import OptimizedJSONResponse

# Create optimized JSON response
response = OptimizedJSONResponse(
    content={"users": users_data, "metadata": metadata},
    parallel_threshold=5000,    # Use parallel processing for large objects
    enable_caching=True,        # Enable response caching
    max_cache_size=1000        # Cache up to 1000 responses
)

# Get performance statistics
stats = response.get_performance_stats()
print(f"Render time: {stats['render_time_ms']:.2f}ms")
print(f"Used parallel processing: {stats['used_parallel']}")
print(f"Cache hit: {stats['cache_hit']}")
```

### Advanced Configuration

```python
from velithon.responses.json_optimized import (
    OptimizedJSONResponse,
    json_response,
    batch_json_response
)

# Convenience function
response = json_response(
    content=data,
    status_code=200,
    parallel_threshold=1000,
    enable_compression=True
)

# Batch processing for multiple objects
batch_response = batch_json_response(
    objects=[obj1, obj2, obj3],
    parallel_threshold=50,
    chunk_size=10
)
```

## Background Task Memory Management

### Memory-Bounded Task Queues

```python
from velithon.background import BackgroundTasks

# Create background tasks with memory limits
tasks = BackgroundTasks(
    max_concurrent=10,
    max_queue_size=1000,           # Maximum queued tasks
    memory_pressure_threshold=500   # Start GC when queue > 500
)

# Add tasks (will fail if queue is full)
try:
    tasks.add_task(my_function, args=(arg1, arg2))
except MemoryError as e:
    print(f"Queue full: {e}")

# Get queue statistics
stats = tasks.get_queue_stats()
print(f"Queue utilization: {stats['utilization_percent']}%")
print(f"Memory pressure: {bool(stats['memory_pressure'])}")

# Clear tasks if needed
cleared_count = tasks.clear_tasks()
print(f"Cleared {cleared_count} pending tasks")
```

## Performance Best Practices

### 1. Configure Memory Limits Appropriately

```python
# For high-traffic applications
configure_global_memory_handler(
    memory_pool_size=4096,       # Larger pool for more allocations
    cache_max_entries=2000,      # More cache entries
    cache_max_memory_mb=200      # Higher memory limit
)

# For memory-constrained environments
configure_global_memory_handler(
    memory_pool_size=512,        # Smaller pool
    cache_max_entries=500,       # Fewer cache entries
    cache_max_memory_mb=50       # Lower memory limit
)
```

### 2. Use String Interning for Repeated Strings

```python
# Good: Use string interning for frequently repeated strings
interner = StringInterner()
user_emails = [interner.intern(email) for email in email_list]

# Bad: Don't intern unique strings
# Don't intern things like UUIDs or unique identifiers
```

### 3. Monitor Memory Usage

```python
import asyncio
from velithon.memory import get_memory_stats, cleanup_memory

async def memory_monitoring_task():
    """Periodic memory monitoring and cleanup."""
    while True:
        stats = get_memory_stats()
        
        # Check memory pressure
        if stats.get('cache_memory_mb', 0) > 150:  # 150 MB threshold
            print("Memory pressure detected, performing cleanup...")
            cleanup_stats = cleanup_memory()
            print(f"Freed {cleanup_stats['gc_objects_collected']} objects")
        
        await asyncio.sleep(60)  # Check every minute

# Start monitoring
asyncio.create_task(memory_monitoring_task())
```

### 4. Optimize JSON Response Caching

```python
from velithon.responses.json_optimized import OptimizedJSONResponse

@app.get("/users")
async def get_users():
    # Enable caching for frequently requested data
    return OptimizedJSONResponse(
        content=users_data,
        enable_caching=True,
        parallel_threshold=1000,  # Adjust based on typical data size
    )

@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    # Use cache key based on report parameters
    cache_key = f"report_{report_id}"
    
    # Try cache first
    handler = get_global_memory_handler()
    cached = handler.get_cached_response(cache_key)
    if cached:
        return Response(content=cached, media_type="application/json")
    
    # Generate report
    report_data = generate_report(report_id)
    response = OptimizedJSONResponse(report_data)
    
    # Cache for future requests
    handler.cache_response(cache_key, response.body)
    
    return response
```

### 5. Handle Memory Pressure Gracefully

```python
from velithon.memory import get_memory_stats, cleanup_memory

@app.middleware("http")
async def memory_pressure_middleware(request: Request, call_next):
    """Middleware to handle memory pressure."""
    
    # Check memory before processing request
    stats = get_memory_stats()
    memory_usage_mb = stats.get('cache_memory_mb', 0)
    
    if memory_usage_mb > 100:  # Threshold
        # Perform cleanup before processing
        cleanup_memory()
    
    response = await call_next(request)
    
    # Add memory usage headers for monitoring
    response.headers["X-Memory-Usage-MB"] = str(memory_usage_mb)
    
    return response
```

## Debugging and Monitoring

### Memory Statistics

```python
from velithon.memory import get_memory_stats

def print_memory_report():
    """Print comprehensive memory usage report."""
    stats = get_memory_stats()
    
    print("Memory Usage Report")
    print("=" * 50)
    
    # Memory pool stats
    print(f"Memory Pool Cache Hit Rate: {stats.get('pool_cache_hit_rate_percent', 0)}%")
    print(f"Memory Pool Peak Usage: {stats.get('pool_peak_allocated_bytes', 0)} bytes")
    
    # Cache stats
    print(f"Response Cache Hit Rate: {stats.get('cache_hit_rate_percent', 0)}%")
    print(f"Response Cache Memory: {stats.get('cache_memory_mb', 0):.2f} MB")
    print(f"Response Cache Entries: {stats.get('cache_entries', 0)}")
    
    # String interner stats
    if 'interner_hit_rate_percent' in stats:
        print(f"String Interner Hit Rate: {stats['interner_hit_rate_percent']}%")
        print(f"Interned Strings: {stats.get('interner_current_strings', 0)}")
    
    print("=" * 50)

# Call periodically or in health checks
print_memory_report()
```

### Health Check Endpoint

```python
@app.get("/health/memory")
async def memory_health():
    """Memory health check endpoint."""
    stats = get_memory_stats()
    
    # Calculate health metrics
    memory_usage_mb = stats.get('cache_memory_mb', 0)
    cache_hit_rate = stats.get('cache_hit_rate_percent', 0)
    
    status = "healthy"
    if memory_usage_mb > 150:  # Warning threshold
        status = "warning"
    if memory_usage_mb > 200:  # Critical threshold
        status = "critical"
    
    return {
        "status": status,
        "memory_usage_mb": memory_usage_mb,
        "cache_hit_rate_percent": cache_hit_rate,
        "recommendations": [
            "Consider increasing cache size" if cache_hit_rate < 80 else None,
            "Memory usage high, consider cleanup" if memory_usage_mb > 150 else None,
        ]
    }
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check cache size limits
   - Verify cleanup is running
   - Monitor for memory leaks

2. **Low Cache Hit Rates**
   - Increase cache size
   - Check cache key strategy
   - Verify TTL settings

3. **Performance Degradation**
   - Monitor GC frequency
   - Check memory pool efficiency
   - Verify parallel processing thresholds

### Performance Tuning

```python
# Profile memory usage
from velithon.benchmarks.memory_optimization_benchmark import MemoryBenchmark

benchmark = MemoryBenchmark(iterations=1000)
results = await benchmark.run_comprehensive_benchmark()

# Analyze results and adjust settings
if results['lru_cache']['cache_stats']['hit_rate_percent'] < 80:
    # Increase cache size
    configure_global_memory_handler(cache_max_entries=2000)

if results['memory_pool']['pool_stats']['cache_hit_rate_percent'] < 70:
    # Increase pool size
    configure_global_memory_handler(memory_pool_size=2048)
```

## Migration Guide

### From Standard Responses

```python
# Before: Standard JSON response
from velithon.responses import JSONResponse

@app.get("/data")
async def get_data():
    return JSONResponse({"data": expensive_data})

# After: Optimized JSON response
from velithon.responses.json_optimized import OptimizedJSONResponse

@app.get("/data")
async def get_data():
    return OptimizedJSONResponse(
        {"data": expensive_data},
        enable_caching=True,
        parallel_threshold=1000
    )
```

### Gradual Migration

1. **Start with monitoring**: Add memory statistics endpoints
2. **Enable global handler**: Configure basic memory management
3. **Migrate high-traffic endpoints**: Convert to optimized responses
4. **Add background task limits**: Implement bounded queues
5. **Full optimization**: Enable all memory features

This comprehensive memory optimization system provides significant performance improvements while maintaining compatibility with existing code.
