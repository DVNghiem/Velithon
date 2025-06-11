#!/usr/bin/env python3
"""
Comprehensive performance benchmark suite for Velithon framework optimizations.
Measures the impact of various optimizations on key performance metrics.
"""

import asyncio
import gc
import json
import os
import statistics
import sys
import time
import traceback
import tracemalloc
from typing import Callable, Dict

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from velithon import Velithon
from velithon._utils import set_thread_pool
from velithon.params.dispatcher import _get_cached_signature
from velithon.responses import JSONResponse, PlainTextResponse


class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite."""
    
    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        self.results = {}
        
    def time_function(self, func: Callable, *args, **kwargs) -> Dict[str, float]:
        """Time a function execution and collect statistics."""
        times = []
        
        # Warm up
        for _ in range(10):
            func(*args, **kwargs)
        
        # Actual measurements
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'p95': sorted(times)[int(0.95 * len(times))],
            'p99': sorted(times)[int(0.99 * len(times))]
        }
    
    def benchmark_signature_resolution(self):
        """Benchmark function signature resolution performance."""
        print("🔍 Benchmarking signature resolution...")
        
        def sample_handler(user_id: int, name: str = "default", active: bool = True):
            return {"user_id": user_id, "name": name, "active": active}
        
        # Test signature caching
        result = self.time_function(_get_cached_signature, sample_handler)
        self.results['signature_resolution'] = result
        
        print(f"  Mean time: {result['mean']*1000:.3f}ms")
        print(f"  P95 time: {result['p95']*1000:.3f}ms")
    
    def benchmark_parameter_parsing(self):
        """Benchmark parameter parsing performance."""
        print("🔧 Benchmarking parameter parsing...")
        
        query_string = "user_id=123&name=john&active=true&score=95.5&tags=python,web,async"
        
        def simple_parse_query(query_str):
            """Simple query string parser for benchmarking."""
            if not query_str:
                return {}
            params = {}
            for pair in query_str.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    # Basic type conversion
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.replace('.', '').isdigit():
                        value = float(value) if '.' in value else int(value)
                    params[key] = value
            return params
        
        result = self.time_function(simple_parse_query, query_string)
        self.results['parameter_parsing'] = result
        
        print(f"  Mean time: {result['mean']*1000:.3f}ms")
        print(f"  P95 time: {result['p95']*1000:.3f}ms")
    
    def benchmark_dependency_injection(self):
        """Benchmark dependency injection performance."""
        print("💉 Benchmarking dependency injection...")
        
        app = Velithon()
        
        class UserService:
            def get_user(self, user_id: int):
                return {"id": user_id, "name": "Test User"}
        
        def get_user_service():
            return UserService()
        
        # Simple DI simulation with route using correct Velithon API
        async def get_user_handler(request):
            user_id = request.path_params.get("user_id", 1)
            service = get_user_service()
            return JSONResponse(service.get_user(int(user_id)))
        
        app.add_route("/users/{user_id}", get_user_handler, methods=["GET"])
        
        # Simulate DI resolution
        def simulate_di():
            service = get_user_service()
            return service.get_user(123)
        
        result = self.time_function(simulate_di)
        self.results['dependency_injection'] = result
        
        print(f"  Mean time: {result['mean']*1000:.3f}ms")
        print(f"  P95 time: {result['p95']*1000:.3f}ms")
    
    def benchmark_response_creation(self):
        """Benchmark response object creation."""
        print("📤 Benchmarking response creation...")
        
        test_data = {
            "users": [
                {"id": i, "name": f"User {i}", "active": True, "score": 95.5}
                for i in range(100)
            ],
            "total": 100,
            "page": 1
        }
        
        def create_json_response():
            return JSONResponse(test_data)
        
        def create_text_response():
            return PlainTextResponse("Hello, World!")
        
        json_result = self.time_function(create_json_response)
        text_result = self.time_function(create_text_response)
        
        self.results['json_response_creation'] = json_result
        self.results['text_response_creation'] = text_result
        
        print(f"  JSON Mean time: {json_result['mean']*1000:.3f}ms")
        print(f"  Text Mean time: {text_result['mean']*1000:.3f}ms")
    
    def benchmark_thread_pool_performance(self):
        """Benchmark thread pool operations."""
        print("🧵 Benchmarking thread pool performance...")
        
        def cpu_bound_task():
            return sum(i * i for i in range(1000))
        
        # Set up thread pool first
        set_thread_pool()
        
        def test_thread_pool():
            # Simple thread pool test
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as pool:
                future = pool.submit(cpu_bound_task)
                return future.result()
        
        result = self.time_function(test_thread_pool)
        self.results['thread_pool_execution'] = result
        
        print(f"  Mean time: {result['mean']*1000:.3f}ms")
        print(f"  P95 time: {result['p95']*1000:.3f}ms")
    
    def benchmark_memory_usage(self):
        """Benchmark memory usage patterns."""
        print("💾 Benchmarking memory usage...")
        
        tracemalloc.start()
        
        # Simulate typical request processing
        for _ in range(100):
            query_string = "user_id=123&name=john&active=true&score=95.5"
            # Simple query parsing for memory test
            params = {}
            for pair in query_string.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
            
            data = {"result": "success", "data": [1, 2, 3, 4, 5]}
            JSONResponse(data)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.results['memory_usage'] = {
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024
        }
        
        print(f"  Current memory: {current / 1024 / 1024:.2f} MB")
        print(f"  Peak memory: {peak / 1024 / 1024:.2f} MB")
    
    async def benchmark_concurrent_requests(self):
        """Benchmark concurrent request handling."""
        print("⚡ Benchmarking concurrent request handling...")
        
        app = Velithon()
        
        async def test_endpoint(request):
            # Simulate some processing
            await asyncio.sleep(0.001)
            return JSONResponse({"message": "Hello, World!", "timestamp": time.time()})
        
        app.add_route("/test", test_endpoint, methods=["GET"])
        
        async def simulate_request():
            # Simulate request processing without actual HTTP
            from velithon.requests import Request
            
            # Create mock scope and protocol for testing
            scope = type('MockScope', (), {
                'proto': 'http',
                'method': 'GET',
                'path': '/test',
                'headers': [],
                'query_string': b'',
                'path_params': {}
            })()
            
            protocol = type('MockProtocol', (), {})()
            request = Request(scope, protocol)
            
            return await test_endpoint(request)
        
        # Test concurrent execution
        start_time = time.perf_counter()
        
        tasks = [simulate_request() for _ in range(100)]
        await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        self.results['concurrent_requests'] = {
            'total_time': total_time,
            'requests_per_second': 100 / total_time,
            'avg_request_time': total_time / 100
        }
        
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Requests/sec: {100 / total_time:.0f}")
        print(f"  Avg request time: {(total_time / 100) * 1000:.3f}ms")
    
    def benchmark_cache_performance(self):
        """Benchmark caching mechanisms."""
        print("🗄️ Benchmarking cache performance...")
        
        from functools import lru_cache
        
        @lru_cache(maxsize=128)
        def cached_computation(n: int) -> int:
            return sum(i * i for i in range(n))
        
        def uncached_computation(n: int) -> int:
            return sum(i * i for i in range(n))
        
        # Test cached vs uncached
        cached_result = self.time_function(lambda: cached_computation(100))
        uncached_result = self.time_function(lambda: uncached_computation(100))
        
        self.results['cached_computation'] = cached_result
        self.results['uncached_computation'] = uncached_result
        
        speedup = uncached_result['mean'] / cached_result['mean']
        
        print(f"  Cached mean time: {cached_result['mean']*1000:.3f}ms")
        print(f"  Uncached mean time: {uncached_result['mean']*1000:.3f}ms")
        print(f"  Cache speedup: {speedup:.1f}x")
    
    async def run_all_benchmarks(self):
        """Run all benchmark tests."""
        print("🚀 Starting Velithon Performance Benchmark Suite")
        print("=" * 60)
        
        # Force garbage collection before starting
        gc.collect()
        
        start_time = time.time()
        
        try:
            self.benchmark_signature_resolution()
            print()
            
            self.benchmark_parameter_parsing()
            print()
            
            self.benchmark_dependency_injection()
            print()
            
            self.benchmark_response_creation()
            print()
            
            self.benchmark_thread_pool_performance()
            print()
            
            self.benchmark_memory_usage()
            print()
            
            await self.benchmark_concurrent_requests()
            print()
            
            self.benchmark_cache_performance()
            print()
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            traceback.print_exc()
            return
        
        total_time = time.time() - start_time
        
        print("=" * 60)
        print(f"✅ Benchmark suite completed in {total_time:.2f}s")
        
        # Save results
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save benchmark results to file."""
        results_file = "benchmark_results.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'iterations': self.iterations,
                'results': self.results
            }, f, indent=2)
        
        print(f"📊 Results saved to {results_file}")
    
    def print_summary(self):
        """Print a summary of benchmark results."""
        print("\n📈 Performance Summary:")
        print("-" * 40)
        
        for test_name, result in self.results.items():
            if isinstance(result, dict) and 'mean' in result:
                print(f"{test_name:.<30} {result['mean']*1000:>6.3f}ms")
            elif isinstance(result, dict) and 'requests_per_second' in result:
                print(f"{test_name:.<30} {result['requests_per_second']:>6.0f} req/s")
        
        print("-" * 40)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Velithon Performance Benchmark Suite")
    parser.add_argument('--iterations', type=int, default=1000, 
                       help='Number of iterations for each benchmark (default: 1000)')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(iterations=args.iterations)
    asyncio.run(benchmark.run_all_benchmarks())
