#!/usr/bin/env python3
"""
A simplified benchmark focusing on the core performance bottlenecks.
"""
import time
import asyncio
from velithon import Velithon
from velithon.responses import JSONResponse, PlainTextResponse
from velithon.requests import Request
from velithon.optimizations import (
    get_json_encoder, 
    get_response_cache,
    get_dict_from_pool,
    return_dict_to_pool
)

# Test parameters
iterations = 50000

async def benchmark_json_vs_text():
    """Compare JSON response performance to text response"""
    test_data = {
        "message": "Hello World",
        "timestamp": time.time(),
        "data": list(range(20)),
        "nested": {
            "key1": "value1",
            "key2": [1, 2, 3, 4, 5],
            "key3": {"sub": "data"}
        }
    }
    
    # JSON response benchmark
    json_times = []
    print("Testing JSON response performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            response = JSONResponse(test_data)
            content = response.body  # Access body to trigger render
        end = time.perf_counter()
        json_times.append(end - start)
    
    # Text response benchmark
    text_times = []
    print("Testing PlainText response performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            response = PlainTextResponse("Hello World")
            content = response.body  # Access body to trigger render
        end = time.perf_counter()
        text_times.append(end - start)
    
    avg_json_time = sum(json_times) / len(json_times)
    avg_text_time = sum(text_times) / len(text_times)
    
    print(f"\nResponse Performance Results ({iterations} iterations):")
    print(f"JSON response time: {avg_json_time*1000:.2f}ms ({avg_json_time*1000000/iterations:.2f}μs per response)")
    print(f"Text response time: {avg_text_time*1000:.2f}ms ({avg_text_time*1000000/iterations:.2f}μs per response)")
    print(f"JSON/Text ratio: {avg_json_time/avg_text_time:.2f}x")

async def benchmark_object_pooling():
    """Benchmark object pooling performance"""
    pool_times = []
    print("\nTesting object pool performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            d = get_dict_from_pool()
            d['test'] = 1
            d['value'] = 2
            return_dict_to_pool(d)
        end = time.perf_counter()
        pool_times.append(end - start)
    
    direct_times = []
    print("Testing direct dict creation...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            d = {}
            d['test'] = 1
            d['value'] = 2
        end = time.perf_counter()
        direct_times.append(end - start)
    
    avg_pool_time = sum(pool_times) / len(pool_times)
    avg_direct_time = sum(direct_times) / len(direct_times)
    
    print(f"\nObject Pool Results ({iterations} iterations):")
    print(f"Object pool time: {avg_pool_time*1000:.2f}ms ({avg_pool_time*1000000/iterations:.2f}μs per operation)")
    print(f"Direct creation time: {avg_direct_time*1000:.2f}ms ({avg_direct_time*1000000/iterations:.2f}μs per operation)")
    print(f"Direct/Pool ratio: {avg_direct_time/avg_pool_time:.2f}x (>1 means pool is faster)")

async def main():
    print("🧪 Starting Velithon Bottleneck Analysis")
    print("=" * 50)
    
    await benchmark_json_vs_text()
    await benchmark_object_pooling()
    
    print("\n✅ Benchmark completed!")

if __name__ == "__main__":
    asyncio.run(main())
