import asyncio
import json
import time
import tracemalloc
from unittest.mock import MagicMock

# Velithon imports
from velithon.application import Velithon
from velithon.datastructures import Protocol, Scope
from velithon.requests import Request
from velithon.responses import JSONResponse, PlainTextResponse

# Try importing optimizations
try:
    from velithon.performance import get_json_encoder, get_response_cache
    HAS_OPTIMIZATIONS = True
    print("✅ Advanced optimizations available")
except ImportError:
    HAS_OPTIMIZATIONS = False
    print("❌ Advanced optimizations not available")

class AdvancedBenchmarkSuite:
    """Advanced benchmark suite for testing optimization improvements."""
    
    def __init__(self, iterations: int = 10000):
        self.iterations = iterations
        self.results = {}
        self.setup_test_app()
    
    def setup_test_app(self):
        """Set up test Velithon application."""
        self.app = Velithon()
        
        # Add test routes
        async def json_endpoint(request: Request) -> JSONResponse:
            data = {
                "message": "Hello World",
                "timestamp": time.time(),
                "request_id": getattr(request.scope, '_request_id', 'test'),
                "data": list(range(10))  # Some array data
            }
            return JSONResponse(data)
        
        async def simple_json_endpoint(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})
        
        async def text_endpoint(request: Request) -> PlainTextResponse:
            return PlainTextResponse("Hello World")
        
        self.app.add_route("/json", json_endpoint)
        self.app.add_route("/simple", simple_json_endpoint)
        self.app.add_route("/text", text_endpoint)
    
    def time_execution(self, func, *args, **kwargs):
        """Time function execution with high precision."""
        times = []
        for _ in range(min(1000, self.iterations)):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            'result': result,
            'times': times,
            'mean': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'median': sorted(times)[len(times) // 2],
            'p95': sorted(times)[int(len(times) * 0.95)],
            'p99': sorted(times)[int(len(times) * 0.99)],
            'std_dev': (sum([(t - sum(times) / len(times))**2 for t in times]) / len(times)) ** 0.5
        }
    
    async def async_time_execution(self, coro_func, *args, **kwargs):
        """Time async function execution."""
        times = []
        for _ in range(min(1000, self.iterations)):
            start = time.perf_counter()
            result = await coro_func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            'result': result,
            'times': times,
            'mean': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'median': sorted(times)[len(times) // 2],
            'p95': sorted(times)[int(len(times) * 0.95)],
            'p99': sorted(times)[int(len(times) * 0.99)],
            'std_dev': (sum([(t - sum(times) / len(times))**2 for t in times]) / len(times)) ** 0.5
        }
    
    def benchmark_optimized_json_response(self):
        """Benchmark optimized JSON response creation."""
        print("🧪 Testing optimized JSON response creation...")
        
        test_data = {
            "message": "Hello World",
            "timestamp": time.time(),
            "numbers": list(range(50)),
            "nested": {
                "data": {"key": "value", "count": 42},
                "array": [1, 2, 3, 4, 5]
            }
        }
        
        # Test original orjson response
        def create_orjson_response():
            import orjson
            return orjson.dumps(test_data, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY)
        
        orjson_results = self.time_execution(create_orjson_response)
        self.results['orjson_response'] = {k: v for k, v in orjson_results.items() if k != 'result'}
        
        # Test optimized response if available
        if HAS_OPTIMIZATIONS:
            json_encoder = get_json_encoder()
            
            def create_optimized_response():
                return json_encoder.encode(test_data)
            
            optimized_results = self.time_execution(create_optimized_response)
            self.results['optimized_json_response'] = {k: v for k, v in optimized_results.items() if k != 'result'}
            
            # Calculate speedup
            speedup = orjson_results['mean'] / optimized_results['mean']
            self.results['json_speedup'] = speedup
            print(f"   📈 JSON encoding speedup: {speedup:.2f}x")
        else:
            print("   ⚠️ Optimized JSON encoder not available")
    
    def benchmark_response_caching(self):
        """Benchmark response caching effectiveness."""
        print("🗄️ Testing response caching...")
        
        if not HAS_OPTIMIZATIONS:
            print("   ⚠️ Response caching not available")
            return
        
        response_cache = get_response_cache()
        test_data = {"message": "cached response", "id": 123}
        
        # First access (cache miss)
        def cache_miss():
            cache_key = "test_response_123"
            cached = response_cache.get(cache_key)
            if cached is None:
                # Simulate response creation
                result = json.dumps(test_data).encode()
                response_cache.put(cache_key, result)
                return result
            return cached
        
        miss_results = self.time_execution(cache_miss)
        
        # Second access (cache hit)
        def cache_hit():
            cache_key = "test_response_123"
            return response_cache.get(cache_key)
        
        hit_results = self.time_execution(cache_hit)
        
        self.results['cache_miss'] = {k: v for k, v in miss_results.items() if k != 'result'}
        self.results['cache_hit'] = {k: v for k, v in hit_results.items() if k != 'result'}
        
        # Calculate cache effectiveness
        cache_speedup = miss_results['mean'] / hit_results['mean']
        self.results['cache_speedup'] = cache_speedup
        print(f"   📈 Cache speedup: {cache_speedup:.2f}x")
    
    async def benchmark_concurrent_json_responses(self):
        """Benchmark concurrent JSON response handling."""
        print("⚡ Testing concurrent JSON response handling...")
        
        async def create_json_response():
            response = JSONResponse({
                "id": 123,
                "message": "test response",
                "data": list(range(10))
            })
            return response.body
        
        # Test sequential responses
        start_time = time.perf_counter()
        for _ in range(100):
            await create_json_response()
        sequential_time = time.perf_counter() - start_time
        
        # Test concurrent responses
        start_time = time.perf_counter()
        tasks = [create_json_response() for _ in range(100)]
        await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start_time
        
        self.results['sequential_json_time'] = sequential_time
        self.results['concurrent_json_time'] = concurrent_time
        self.results['concurrency_speedup'] = sequential_time / concurrent_time
        
        print(f"   📈 Concurrency speedup: {sequential_time / concurrent_time:.2f}x")
    
    def benchmark_memory_efficiency(self):
        """Benchmark memory usage patterns."""
        print("💾 Testing memory efficiency...")
        
        tracemalloc.start()
        
        # Create many responses to test memory patterns
        responses = []
        for i in range(1000):
            data = {
                "id": i,
                "message": f"Response {i}",
                "data": list(range(i % 20))
            }
            response = JSONResponse(data)
            responses.append(response.body)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.results['memory_current_mb'] = current / 1024 / 1024
        self.results['memory_peak_mb'] = peak / 1024 / 1024
        
        print(f"   📊 Memory usage - Current: {current / 1024 / 1024:.3f} MB, Peak: {peak / 1024 / 1024:.3f} MB")
    
    async def benchmark_application_throughput(self):
        """Benchmark complete application throughput."""
        print("🚀 Testing application throughput...")
        
        # Create mock scope and protocol
        def create_mock_request():
            scope = MagicMock()
            scope.proto = "http"
            scope.method = "GET"
            scope.path = "/json"
            scope.query_string = b""
            scope.headers = {}
            scope._request_id = "test"
            scope.client = "127.0.0.1"
            scope.server = "localhost:8000"
            scope.scheme = "http"
            
            protocol = MagicMock()
            protocol.return_value = b'{"test": "data"}'
            
            return Request(Scope(scope=scope), Protocol(protocol=protocol))
        
        # Test throughput
        num_requests = 1000
        start_time = time.perf_counter()
        
        for _ in range(num_requests):
            request = create_mock_request()
            # Simulate JSON response creation
            response = JSONResponse({
                "message": "Hello World",
                "timestamp": time.time()
            })
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        requests_per_second = num_requests / total_time
        
        self.results['app_throughput_rps'] = requests_per_second
        self.results['app_avg_response_time'] = total_time / num_requests
        
        print(f"   📊 Application throughput: {requests_per_second:,.0f} req/s")
        print(f"   ⏱️ Average response time: {(total_time / num_requests) * 1000:.3f} ms")
    
    async def run_all_benchmarks(self):
        """Run all benchmark tests."""
        print("🧪 Starting Advanced Performance Benchmark Suite")
        print("=" * 60)
        
        # Basic optimizations
        self.benchmark_optimized_json_response()
        self.benchmark_response_caching()
        self.benchmark_memory_efficiency()
        
        # Advanced async tests
        await self.benchmark_concurrent_json_responses()
        await self.benchmark_application_throughput()
        
        print("\n📊 Benchmark Results Summary:")
        print("=" * 60)
        
        if HAS_OPTIMIZATIONS:
            if 'json_speedup' in self.results:
                print(f"🚀 JSON Encoding Speedup: {self.results['json_speedup']:.2f}x")
            if 'cache_speedup' in self.results:
                print(f"🗄️ Response Cache Speedup: {self.results['cache_speedup']:.2f}x")
            if 'pool_speedup' in self.results:
                print(f"♻️ Object Pool Speedup: {self.results['pool_speedup']:.2f}x")
        
        if 'concurrency_speedup' in self.results:
            print(f"⚡ Concurrency Speedup: {self.results['concurrency_speedup']:.2f}x")
        
        if 'app_throughput_rps' in self.results:
            print(f"🎯 Application Throughput: {self.results['app_throughput_rps']:,.0f} req/s")
        
        if 'memory_peak_mb' in self.results:
            print(f"💾 Peak Memory Usage: {self.results['memory_peak_mb']:.3f} MB")
        
        # Save detailed results
        timestamp = time.time()
        results_data = {
            'timestamp': timestamp,
            'iterations': self.iterations,
            'has_optimizations': HAS_OPTIMIZATIONS,
            'results': self.results
        }
        
        with open('advanced_benchmark_results.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print("\n📄 Detailed results saved to: advanced_benchmark_results.json")
        
        return results_data


async def main():
    """Run the advanced benchmark suite."""
    suite = AdvancedBenchmarkSuite(iterations=1000)
    results = await suite.run_all_benchmarks()
    
    print("\n✅ Advanced benchmark suite completed!")
    
    # Compare with previous results if available
    try:
        with open('benchmark_results.json', 'r') as f:
            previous_results = json.load(f)
        
        print("\n📈 Performance Comparison:")
        print("=" * 60)
        
        if 'results' in previous_results and 'concurrent_requests' in previous_results['results']:
            old_rps = previous_results['results']['concurrent_requests']['requests_per_second']
            if 'app_throughput_rps' in results['results']:
                new_rps = results['results']['app_throughput_rps']
                improvement = (new_rps / old_rps - 1) * 100
                print(f"🎯 Throughput improvement: {improvement:+.1f}% ({old_rps:,.0f} → {new_rps:,.0f} req/s)")
        
        if 'results' in previous_results and 'json_response_creation' in previous_results['results']:
            old_json_time = previous_results['results']['json_response_creation']['mean']
            if 'optimized_json_response' in results['results']:
                new_json_time = results['results']['optimized_json_response']['mean']
                improvement = (1 - new_json_time / old_json_time) * 100
                print(f"🚀 JSON response improvement: {improvement:+.1f}% ({old_json_time*1e6:.1f}μs → {new_json_time*1e6:.1f}μs)")
    
    except FileNotFoundError:
        print("📝 No previous benchmark results found for comparison")


if __name__ == "__main__":
    asyncio.run(main())
