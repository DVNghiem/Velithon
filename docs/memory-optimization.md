# Velithon Memory Optimization Guide

This guide explains how to use Velithon's advanced memory optimization features to achieve maximum performance in production web applications.

## Overview

Velithon provides comprehensive memory optimization features that include:

- **Garbage Collection Tuning**: Intelligent GC scheduling optimized for web workloads
- **Object Pooling**: Reuse of frequently allocated objects to reduce GC pressure
- **Weak Reference Caching**: Memory-safe caching that prevents memory leaks
- **Request-Scoped Memory Management**: Automatic cleanup after each request
- **Memory Monitoring**: Real-time tracking of memory usage and statistics
- **Automatic Cleanup**: Intelligent cleanup based on memory thresholds

## Quick Start

### Basic Setup

```python
from velithon import Velithon, enable_memory_optimizations

# Create your app
app = Velithon()

# Enable global memory optimizations
enable_memory_optimizations()

@app.get("/")
async def root():
    return {"message": "Memory optimized Velithon app!"}
```

### Using Middleware

```python
from velithon import (
    Velithon, 
    MemoryOptimizationMiddleware,
    MemoryMonitoringMiddleware,
    GCTuningMiddleware
)

app = Velithon()

# Add memory optimization middleware (order matters)
app.add_middleware(GCTuningMiddleware, disable_gc_during_request=True)
app.add_middleware(MemoryOptimizationMiddleware, cleanup_threshold=1000)
app.add_middleware(MemoryMonitoringMiddleware, log_interval=5000)
```

## Core Components

### 1. Garbage Collection Optimizer

The `GarbageCollectionOptimizer` provides intelligent garbage collection management:

```python
from velithon.memory_optimization import get_memory_optimizer

optimizer = get_memory_optimizer()

# Enable optimizations
optimizer.enable()

# Manual garbage collection with statistics
stats = optimizer.gc_optimizer.manual_collection(generation=2)
print(f"Collected {stats['collected_objects']} objects in {stats['collection_time_ms']:.2f}ms")

# Get comprehensive statistics
memory_stats = optimizer.get_comprehensive_stats()
```

#### GC Tuning Parameters

- **Generation 0 Threshold**: 2000 (default: 700) - Reduces frequent collections of short-lived objects
- **Generation 1 Threshold**: 15 (default: 10) - Handles middleware objects efficiently  
- **Generation 2 Threshold**: 5 (default: 10) - Better long-term memory management

### 2. Object Pools

Object pools reduce allocation overhead by reusing frequently created objects:

```python
from velithon.memory_optimization import get_memory_optimizer

optimizer = get_memory_optimizer()

# Create a pool for request processing objects
request_pool = optimizer.create_object_pool(
    name="request_objects",
    factory=lambda: {"headers": {}, "data": None},
    reset_func=lambda obj: obj.clear(),
    max_size=100
)

# Use the pool
obj = request_pool.acquire()
# ... use the object ...
request_pool.release(obj)

# Get pool statistics
stats = request_pool.get_stats()
print(f"Pool reuse ratio: {stats['reuse_ratio']:.2%}")
```

### 3. Weak Reference Caching

Prevents memory leaks by using weak references for cached objects:

```python
from velithon.memory_optimization import get_memory_optimizer

optimizer = get_memory_optimizer()

# Create a weak reference cache
cache = optimizer.create_weak_cache(
    name="user_sessions",
    max_size=1000
)

# Use the cache
cache.put("session_123", session_object)
session = cache.get("session_123")  # Returns object or None if GC'd

# Get cache statistics
stats = cache.get_stats()
print(f"Cache hit ratio: {stats['hit_ratio']:.2%}")
```

### 4. Request Memory Context

Automatic memory management for individual requests:

```python
from velithon.memory_optimization import RequestMemoryContext

# Manual usage
with RequestMemoryContext(enable_monitoring=True):
    # Request processing code here
    # Automatic cleanup happens when context exits
    pass

# As a decorator
from velithon.memory_optimization import with_memory_optimization

@with_memory_optimization
async def heavy_processing():
    # This function will have automatic memory optimization
    large_data = process_large_dataset()
    return large_data
```

## Middleware Options

### MemoryOptimizationMiddleware

Provides comprehensive memory optimization for each request:

```python
app.add_middleware(
    MemoryOptimizationMiddleware,
    enable_monitoring=True,         # Monitor memory usage
    cleanup_threshold=1000,         # Trigger cleanup every N requests
    cleanup_interval=300.0          # Periodic cleanup interval (seconds)
)
```

### MemoryMonitoringMiddleware

Logs memory statistics and monitors usage:

```python
app.add_middleware(
    MemoryMonitoringMiddleware,
    log_interval=1000              # Log stats every N requests
)
```

### GCTuningMiddleware

Fine-tunes garbage collection during request processing:

```python
app.add_middleware(
    GCTuningMiddleware,
    disable_gc_during_request=True,    # Disable GC during request processing
    generation_0_interval=100,         # Gen 0 cleanup every N requests
    generation_2_interval=1000         # Gen 2 cleanup every N requests
)
```

## Monitoring and Statistics

### Memory Statistics

Get comprehensive memory usage information:

```python
from velithon import get_memory_stats

stats = get_memory_stats()

# Example output:
{
    'gc_stats': {
        'gc_enabled': False,
        'gc_thresholds': (2000, 15, 5),
        'gc_counts': (245, 12, 1),
        'total_objects': 15420
    },
    'system_memory': {
        'rss_mb': 45.2,
        'vms_mb': 123.4
    },
    'object_pools': {
        'request_objects': {
            'pool_size': 15,
            'reuse_ratio': 0.85
        }
    },
    'weak_caches': {
        'user_sessions': {
            'size': 234,
            'hit_ratio': 0.92
        }
    }
}
```

### Manual Cleanup

Trigger manual memory cleanup when needed:

```python
from velithon import manual_memory_cleanup

cleanup_stats = manual_memory_cleanup()

# Example output:
{
    'cleanup_time_ms': 12.5,
    'gc_stats': {
        'collected_objects': 1250,
        'collection_time_ms': 8.3,
        'generation': 2
    }
}
```

## Performance Tuning Tips

### 1. Middleware Order

The order of memory optimization middleware matters for optimal performance:

```python
# Optimal order:
app.add_middleware(GCTuningMiddleware)          # First - controls GC timing
app.add_middleware(MemoryOptimizationMiddleware) # Second - manages memory
app.add_middleware(MemoryMonitoringMiddleware)   # Last - monitors/logs
```

### 2. Cleanup Thresholds

Adjust cleanup thresholds based on your application's characteristics:

```python
# High-traffic applications
app.add_middleware(MemoryOptimizationMiddleware, cleanup_threshold=500)

# Memory-intensive applications  
app.add_middleware(MemoryOptimizationMiddleware, cleanup_threshold=100)

# Low-traffic applications
app.add_middleware(MemoryOptimizationMiddleware, cleanup_threshold=2000)
```

### 3. Object Pool Sizing

Size object pools based on your concurrent request load:

```python
# High concurrency
optimizer.create_object_pool("requests", factory, max_size=200)

# Medium concurrency
optimizer.create_object_pool("requests", factory, max_size=100)

# Low concurrency
optimizer.create_object_pool("requests", factory, max_size=50)
```

### 4. Cache Sizing

Size weak reference caches based on your data characteristics:

```python
# Large datasets, frequent access
optimizer.create_weak_cache("data", max_size=5000)

# Small datasets, infrequent access
optimizer.create_weak_cache("data", max_size=500)
```

## Best Practices

### 1. Enable Early

Enable memory optimizations as early as possible in your application:

```python
from velithon import enable_memory_optimizations

# Enable before creating the app
enable_memory_optimizations()

app = Velithon()
```

### 2. Monitor Memory Usage

Regularly monitor memory statistics in production:

```python
import logging
from velithon import get_memory_stats

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_memory_stats(request, call_next):
    response = await call_next(request)
    
    # Log memory stats periodically
    if request.state.request_count % 10000 == 0:
        stats = get_memory_stats()
        logger.info(f"Memory stats: {stats}")
    
    return response
```

### 3. Use Context Managers

Use request memory contexts for memory-intensive operations:

```python
@app.post("/process-data")
async def process_large_data(data: LargeDataModel):
    with RequestMemoryContext():
        # Process large data with automatic cleanup
        result = await process_data_intensive_operation(data)
        return result
```

### 4. Handle Cleanup Gracefully

Implement graceful cleanup in shutdown handlers:

```python
@app.on_shutdown
async def cleanup():
    from velithon import manual_memory_cleanup
    
    # Perform final cleanup
    cleanup_stats = manual_memory_cleanup()
    logger.info(f"Shutdown cleanup: {cleanup_stats}")
```

## Production Deployment

### Environment Variables

Control memory optimization behavior via environment variables:

```bash
# Enable/disable memory optimizations
VELITHON_MEMORY_OPTIMIZATION=true

# Memory threshold for cleanup (MB)
VELITHON_MEMORY_THRESHOLD=100

# GC cleanup intervals
VELITHON_GC_GEN0_INTERVAL=100
VELITHON_GC_GEN2_INTERVAL=1000

# Object pool sizes
VELITHON_POOL_MAX_SIZE=100

# Cache sizes
VELITHON_CACHE_MAX_SIZE=1000
```

### Monitoring Integration

Integrate with monitoring systems:

```python
# Prometheus metrics example
from prometheus_client import Gauge, Counter

memory_usage_gauge = Gauge('velithon_memory_usage_mb', 'Memory usage in MB')
gc_collections_counter = Counter('velithon_gc_collections_total', 'Total GC collections')

@app.middleware("http")
async def update_metrics(request, call_next):
    response = await call_next(request)
    
    # Update metrics
    stats = get_memory_stats()
    if 'system_memory' in stats:
        memory_usage_gauge.set(stats['system_memory']['rss_mb'])
    
    return response
```

### Health Checks

Include memory statistics in health checks:

```python
@app.get("/health")
async def health_check():
    stats = get_memory_stats()
    
    # Check if memory usage is healthy
    memory_mb = stats.get('system_memory', {}).get('rss_mb', 0)
    is_healthy = memory_mb < 500  # Example threshold
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "memory_mb": memory_mb,
        "gc_enabled": stats.get('gc_stats', {}).get('gc_enabled', False)
    }
```

## Troubleshooting

### High Memory Usage

If you notice high memory usage:

1. Check object pool statistics for low reuse ratios
2. Monitor cache hit ratios - low ratios indicate inefficient caching
3. Reduce cleanup thresholds for more frequent cleanup
4. Enable more aggressive GC tuning

### Performance Issues

If memory optimization causes performance issues:

1. Increase cleanup thresholds to reduce cleanup frequency
2. Disable GC during request processing only for CPU-intensive endpoints
3. Use larger object pools to reduce allocation overhead
4. Monitor GC collection times and adjust thresholds accordingly

### Memory Leaks

If you suspect memory leaks:

1. Use weak reference caches instead of regular caches
2. Ensure object pools have proper reset functions
3. Monitor object counts over time
4. Use manual cleanup more frequently

## Advanced Features

### Custom Object Factories

Create custom object factories for specialized use cases:

```python
class RequestBufferFactory:
    def __init__(self, initial_size=1024):
        self.initial_size = initial_size
    
    def __call__(self):
        return bytearray(self.initial_size)
    
    def reset(self, buffer):
        buffer.clear()
        # Resize if too large
        if len(buffer) > self.initial_size * 4:
            buffer = bytearray(self.initial_size)

factory = RequestBufferFactory(2048)
pool = optimizer.create_object_pool("buffers", factory, factory.reset)
```

### Custom Memory Monitoring

Implement custom memory monitoring for specific use cases:

```python
class CustomMemoryMonitor:
    def __init__(self):
        self.peak_memory = 0
        self.request_count = 0
    
    def check_memory(self):
        stats = get_memory_stats()
        current_memory = stats.get('system_memory', {}).get('rss_mb', 0)
        
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
            
        self.request_count += 1
        
        # Custom cleanup logic
        if self.request_count % 1000 == 0:
            if current_memory > self.peak_memory * 0.8:
                manual_memory_cleanup()

monitor = CustomMemoryMonitor()

@app.middleware("http")
async def custom_monitoring(request, call_next):
    response = await call_next(request)
    monitor.check_memory()
    return response
```

This comprehensive memory optimization system ensures that your Velithon applications run efficiently in production environments with minimal memory overhead and optimal garbage collection behavior.
