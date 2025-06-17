# High-Performance JSON Serialization

Velithon includes a high-performance JSON serialization implementation built with Rust and Rayon for concurrent processing optimization. This provides significant performance improvements for large JSON responses.

## 🚀 Features

- **Parallel Processing**: Automatically detects when to use parallel serialization for large collections
- **Fast Path Optimization**: Special handling for simple objects (primitives, small collections)
- **Intelligent Caching**: Caches frequently serialized objects to avoid redundant work
- **Fallback Safety**: Graceful fallback to standard JSON for compatibility
- **Memory Efficient**: Uses Rust's zero-cost abstractions for minimal overhead
- **Batch Processing**: Optimized handling of multiple objects in a single response

## 📊 Performance Benefits

Based on benchmarks, the Rust-based JSON serializer provides:

| Data Type | Performance Improvement | Use Case |
|-----------|------------------------|----------|
| **Large Arrays** | 3-6x faster | API responses with many items |
| **Complex Objects** | 2-4x faster | Nested data structures |
| **Batch Processing** | 4-8x faster | Multiple objects in parallel |
| **Simple Objects** | 1.5-2x faster | Fast path optimization |

## 🛠️ Usage

### Basic Usage

```python
from velithon.json_responses import OptimizedJSONResponse

@app.get("/users")
async def get_users():
    users = await get_all_users()  # Large list of user objects
    
    # Automatically uses parallel processing for large datasets
    return OptimizedJSONResponse(users)
```

### Advanced Configuration

```python
from velithon.json_responses import OptimizedJSONResponse

@app.get("/data")
async def get_data():
    large_dataset = generate_large_dataset()
    
    return OptimizedJSONResponse(
        large_dataset,
        parallel_threshold=50,      # Use parallel processing for 50+ items
        enable_caching=True,        # Enable intelligent caching
        max_cache_size=1000        # Cache up to 1000 entries
    )
```

### Batch Processing

```python
from velithon.json_responses import BatchJSONResponse

@app.get("/batch-data")
async def get_batch_data():
    # Process multiple objects efficiently
    objects = [
        {"user_id": i, "data": generate_user_data(i)}
        for i in range(1000)
    ]
    
    return BatchJSONResponse(
        objects,
        parallel_threshold=50,
        combine_as_array=True      # Combine into single JSON array
    )
```

### Convenience Functions

```python
from velithon.json_responses import json_response, batch_json_response

@app.get("/simple")
async def simple_endpoint():
    data = {"message": "Hello", "items": [1, 2, 3]}
    return json_response(data, parallel_threshold=100)

@app.get("/multi")
async def multi_endpoint():
    objects = [{"id": i} for i in range(100)]
    return batch_json_response(objects)
```

## 🔧 Configuration Options

### OptimizedJSONResponse Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `parallel_threshold` | `int` | `100` | Minimum collection size for parallel processing |
| `use_parallel_auto` | `bool` | `True` | Auto-detect when to use parallel processing |
| `enable_caching` | `bool` | `True` | Enable intelligent response caching |
| `max_cache_size` | `int` | `1000` | Maximum number of cached entries |

### BatchJSONResponse Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `parallel_threshold` | `int` | `50` | Minimum object count for parallel processing |
| `combine_as_array` | `bool` | `True` | Combine objects into single JSON array |

## 📈 Performance Monitoring

Get detailed performance statistics:

```python
@app.get("/monitored")
async def monitored_endpoint():
    data = generate_large_data()
    response = OptimizedJSONResponse(data)
    
    # Get performance metrics
    stats = response.get_performance_stats()
    print(f"Render time: {stats['render_time_ms']:.3f}ms")
    print(f"Used parallel: {stats['used_parallel']}")
    print(f"Cache hit: {stats['cache_hit']}")
    
    return response
```

## 🧪 Benchmarking

Run the included benchmark to test performance on your system:

```bash
# Run comprehensive benchmarks
python benchmarks/json_serialization_benchmark.py

# Run optimization tests
python tests/test_json_optimization.py
```

## 🔄 Automatic Detection

The serializer automatically determines when to use parallel processing based on:

1. **Collection Size**: Arrays/objects larger than `parallel_threshold`
2. **Data Complexity**: Nested structures with multiple levels
3. **System Resources**: Available CPU cores and memory

## 💡 Best Practices

### When to Use Parallel Processing

✅ **Good candidates:**
- Large arrays (100+ items)
- Complex nested objects
- API responses with many records
- Batch processing scenarios

❌ **Not recommended:**
- Simple objects (primitives, small collections)
- Real-time responses where latency matters more than throughput
- Memory-constrained environments

### Optimization Tips

1. **Tune the Threshold**: Adjust `parallel_threshold` based on your data patterns
2. **Enable Caching**: Use caching for frequently requested data
3. **Monitor Performance**: Use performance stats to identify bottlenecks
4. **Batch When Possible**: Use `BatchJSONResponse` for multiple objects

## 🔧 Installation & Setup

### Prerequisites

1. **Rust Toolchain**: Install from [rustup.rs](https://rustup.rs/)
2. **Maturin**: Install with `pip install maturin`

### Building Extensions

```bash
# Development build
maturin develop

# Optimized release build
maturin develop --release

# For production
maturin build --release
```

### Verification

```python
# Test that extensions are available
try:
    from velithon._velithon import ParallelJSONSerializer
    print("✅ JSON optimization available")
except ImportError:
    print("❌ JSON optimization not available")
```

## 🐛 Troubleshooting

### Common Issues

**Import Error**: Extensions not compiled
```bash
maturin develop --release
```

**Performance Not Improved**: Check thresholds
```python
# Lower threshold for smaller datasets
OptimizedJSONResponse(data, parallel_threshold=10)
```

**Memory Usage**: Reduce cache size
```python
OptimizedJSONResponse(data, max_cache_size=100)
```

### Fallback Behavior

The implementation gracefully falls back to standard JSON when:
- Rust extensions are not available
- Serialization errors occur
- Memory constraints are encountered

## 📚 Technical Details

### Architecture

```
Python Layer (velithon/json_responses.py)
    ↓
Rust Layer (src/json_serializer.rs)
    ↓
Rayon Parallel Processing
    ↓
serde_json
```

### Thread Safety

- All serializers are thread-safe
- Concurrent access to cache is protected
- Parallel processing uses work-stealing queues

### Memory Management

- Zero-copy where possible
- Efficient memory allocation with jemalloc
- Automatic cleanup of resources

## 🎯 Migration Guide

### From Standard JSONResponse

**Before:**
```python
from velithon.responses import JSONResponse

return JSONResponse(large_data)
```

**After:**
```python
from velithon.json_responses import OptimizedJSONResponse

return OptimizedJSONResponse(large_data)
```

### Gradual Migration

1. **Start with large endpoints**: Migrate endpoints with large responses first
2. **Monitor performance**: Use performance stats to validate improvements
3. **Adjust thresholds**: Tune parameters based on your data patterns
4. **Expand usage**: Gradually apply to more endpoints

This optimization provides significant performance improvements for JSON-heavy applications while maintaining full compatibility with existing code.
