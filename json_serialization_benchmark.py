#!/usr/bin/env python3
"""
A benchmark to compare different JSON serialization approaches.
"""
import time
import asyncio
import json
from velithon.responses import JSONResponse

# Try importing optimizations
try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

try:
    import ujson
    HAS_UJSON = True
except ImportError:
    HAS_UJSON = False

# Test parameters
iterations = 50000

async def benchmark_json_serializers():
    """Compare different JSON serialization approaches"""
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
    
    # Standard JSON
    std_json_times = []
    print("Testing standard json module...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            json_bytes = json.dumps(test_data, separators=(",", ":")).encode("utf-8")
        end = time.perf_counter()
        std_json_times.append(end - start)
    
    # orjson if available
    orjson_times = []
    if HAS_ORJSON:
        print("Testing orjson module...")
        for _ in range(5):
            start = time.perf_counter()
            for _ in range(iterations):
                json_bytes = orjson.dumps(test_data)
            end = time.perf_counter()
            orjson_times.append(end - start)
    
    # ujson if available
    ujson_times = []
    if HAS_UJSON:
        print("Testing ujson module...")
        for _ in range(5):
            start = time.perf_counter()
            for _ in range(iterations):
                json_bytes = ujson.dumps(test_data).encode("utf-8")
            end = time.perf_counter()
            ujson_times.append(end - start)
    
    # JSONResponse (which uses the optimized encoder)
    json_response_times = []
    print("Testing JSONResponse...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            response = JSONResponse(test_data)
            content = response.body  # Access body to trigger render
        end = time.perf_counter()
        json_response_times.append(end - start)
    
    # Calculate averages
    avg_std_json_time = sum(std_json_times) / len(std_json_times)
    avg_json_response_time = sum(json_response_times) / len(json_response_times)
    
    print(f"\nJSON Serialization Results ({iterations} iterations):")
    print(f"Standard json: {avg_std_json_time*1000:.2f}ms ({avg_std_json_time*1000000/iterations:.2f}μs per serialization)")
    
    if HAS_ORJSON:
        avg_orjson_time = sum(orjson_times) / len(orjson_times)
        print(f"orjson: {avg_orjson_time*1000:.2f}ms ({avg_orjson_time*1000000/iterations:.2f}μs per serialization)")
        print(f"orjson speedup vs std json: {avg_std_json_time/avg_orjson_time:.2f}x")
    
    if HAS_UJSON:
        avg_ujson_time = sum(ujson_times) / len(ujson_times)
        print(f"ujson: {avg_ujson_time*1000:.2f}ms ({avg_ujson_time*1000000/iterations:.2f}μs per serialization)")
        print(f"ujson speedup vs std json: {avg_std_json_time/avg_ujson_time:.2f}x")
    
    print(f"JSONResponse: {avg_json_response_time*1000:.2f}ms ({avg_json_response_time*1000000/iterations:.2f}μs per response)")
    print(f"JSONResponse overhead vs best serializer: {avg_json_response_time/(min([avg_std_json_time] + (orjson_times and [avg_orjson_time]) + (ujson_times and [avg_ujson_time]))):.2f}x")

async def main():
    print("🧪 JSON Serialization Benchmark")
    print("=" * 50)
    
    await benchmark_json_serializers()
    
    print("\n✅ Benchmark completed!")

if __name__ == "__main__":
    asyncio.run(main())
