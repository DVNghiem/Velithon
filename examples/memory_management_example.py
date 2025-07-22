"""Velithon Memory Management Example.

This example demonstrates how to use Velithon's advanced memory management features
for maximum performance in production web applications.
"""

import asyncio
import logging

from velithon import (
    GCTuningMiddleware,
    JSONResponse,
    MemoryManagementMiddleware,
    MemoryMonitoringMiddleware,
    RequestMemoryContext,
    StreamingResponse,
    Velithon,
    enable_memory_optimizations,
    get_memory_stats,
    manual_memory_cleanup,
    with_memory_optimization,
)

# Configure logging to see memory optimization effects
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Velithon app with memory optimizations
app = Velithon()

# Enable global memory optimizations
enable_memory_optimizations()

# Add memory management middleware stack
# Order matters: GC tuning -> Memory management -> Memory monitoring
app.add_middleware(GCTuningMiddleware, disable_gc_during_request=True)
app.add_middleware(MemoryManagementMiddleware, cleanup_threshold=500)
app.add_middleware(MemoryMonitoringMiddleware, log_interval=1000)


@app.get('/')
async def root():
    """Demonstrate automatic memory management."""
    return JSONResponse({'message': 'Hello from memory-managed Velithon!'})


@app.get('/heavy-computation')
@with_memory_optimization  # Decorator for additional memory management
async def heavy_computation():
    """Endpoint that performs memory-intensive operations."""
    # Simulate heavy computation that creates many objects
    data = []
    for i in range(10000):
        data.append({'id': i, 'value': f'item_{i}', 'metadata': {'created': True}})

    # Process the data
    result = {
        'processed_items': len(data),
        'total_memory_usage': sum(len(str(item)) for item in data),
        'status': 'completed',
    }

    return JSONResponse(result)


@app.get('/memory-stats')
async def memory_stats_endpoint():
    """Endpoint to check current memory optimization statistics."""
    stats = get_memory_stats()
    return JSONResponse(stats)


@app.get('/manual-cleanup')
async def manual_cleanup_endpoint():
    """Endpoint to trigger manual memory cleanup."""
    cleanup_stats = manual_memory_cleanup()
    return JSONResponse({'message': 'Manual cleanup completed', 'stats': cleanup_stats})


@app.get('/streaming-data')
async def streaming_data():
    """Endpoint demonstrating memory-efficient streaming."""

    async def generate_data():
        # Use request memory context for optimal cleanup
        with RequestMemoryContext():
            for i in range(1000):
                yield f'data:{i}\\n'
                # Allow other coroutines to run
                if i % 100 == 0:
                    await asyncio.sleep(0)

    return StreamingResponse(generate_data(), media_type='text/plain')


@app.get('/cache-heavy')
async def cache_heavy_operation():
    """Endpoint that demonstrates efficient caching with memory management."""
    # This would typically use heavy caching - the memory optimizer
    # will automatically manage cache memory usage

    # Simulate cache-heavy operation
    cache_data = {}
    for i in range(5000):
        cache_data[f'key_{i}'] = {'data': f'cached_value_{i}', 'timestamp': i}

    return JSONResponse(
        {
            'cached_items': len(cache_data),
            'sample_key': 'key_100',
            'sample_value': cache_data.get('key_100', {}),
        }
    )


@app.on_startup
async def startup_event():
    """Startup event handler with memory optimization setup."""
    logger.info('Starting Velithon app with memory optimizations enabled')

    # Log initial memory stats
    initial_stats = get_memory_stats()
    logger.info(f'Initial memory stats: {initial_stats}')


@app.on_shutdown
async def shutdown_event():
    """Shutdown event handler with cleanup."""
    logger.info('Shutting down Velithon app')

    # Perform final cleanup
    cleanup_stats = manual_memory_cleanup()
    logger.info(f'Final cleanup stats: {cleanup_stats}')


# Example of using memory optimization in a custom function
@with_memory_optimization
async def process_large_dataset(data_size: int = 50000):
    """Process a large dataset with automatic memory optimization."""
    # Create large dataset
    dataset = [{'id': i, 'value': i * 2, 'processed': False} for i in range(data_size)]

    # Process dataset in chunks for better memory management
    chunk_size = 1000
    processed_count = 0

    for i in range(0, len(dataset), chunk_size):
        chunk = dataset[i : i + chunk_size]

        # Process chunk
        for item in chunk:
            item['processed'] = True
            item['result'] = item['value'] ** 2

        processed_count += len(chunk)

        # Allow garbage collection between chunks
        if processed_count % (chunk_size * 5) == 0:
            await asyncio.sleep(0)  # Yield control

    return {
        'total_processed': processed_count,
        'dataset_size': len(dataset),
        'memory_efficient': True,
    }


@app.get('/large-dataset/{size}')
async def process_dataset_endpoint(size: int):
    """Endpoint for processing large datasets with memory optimization."""
    if size > 100000:
        return JSONResponse(
            {'error': 'Dataset size too large, maximum is 100000'}, status_code=400
        )

    result = await process_large_dataset(size)
    return JSONResponse(result)


if __name__ == '__main__':
    # Example of running with memory optimizations
    print('Starting Velithon with memory optimizations...')
    print('Memory optimization features enabled:')
    print('- Garbage collection tuning')
    print('- Object pooling')
    print('- Weak reference caching')
    print('- Request-scoped memory contexts')
    print('- Automatic cleanup')
    print('\\nVisit these endpoints to see memory optimization in action:')
    print('- GET /: Basic optimized endpoint')
    print('- GET /heavy-computation: Memory-intensive operations')
    print('- GET /memory-stats: Current memory statistics')
    print('- GET /manual-cleanup: Trigger manual cleanup')
    print('- GET /streaming-data: Memory-efficient streaming')
    print('- GET /cache-heavy: Cache-heavy operations')
    print('- GET /large-dataset/{size}: Process large datasets')

    # In a real application, you would run this with velithon CLI using Granian RSGI:
    # velithon run --app memory_optimization_example:app --host 0.0.0.0 --port 8000
    # granian --interface rsgi memory_optimization_example:app
