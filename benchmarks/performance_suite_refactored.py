#!/usr/bin/env python3
"""
Comprehensive performance benchmark suite for Velithon framework optimizations.
Refactored to use base benchmark classes and eliminate duplication.
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Base benchmark imports
from base_benchmark import (
    BaseBenchmark,
    CacheBenchmarkMixin,
    ResponseBenchmarkMixin,
    TimingResult,
    generate_test_api_response,
    generate_test_user_data,
)

from velithon import Velithon
from velithon.params.dispatcher import _get_cached_signature
from velithon.responses import JSONResponse


class PerformanceBenchmark(BaseBenchmark, ResponseBenchmarkMixin, CacheBenchmarkMixin):
    """Comprehensive performance benchmarking suite using base classes."""
    
    def __init__(self, iterations: int = 1000):
        super().__init__(iterations)
        self.setup_test_app()
        
    def setup_test_app(self):
        """Set up test Velithon application."""
        self.app = Velithon()
        
        async def sample_handler(request):
            return JSONResponse({"message": "test"})
        
        self.app.add_route("/test", sample_handler, methods=["GET"])
    
    def benchmark_signature_resolution(self) -> TimingResult:
        """Benchmark function signature resolution performance."""
        print("🔍 Benchmarking signature resolution...")
        
        def sample_handler(user_id: int, name: str = "default", active: bool = True):
            return {"user_id": user_id, "name": name, "active": active}
        
        def test_signature_resolution():
            return _get_cached_signature(sample_handler)
        
        result = self.timer.time_function(test_signature_resolution)
        self.print_timing_results("Signature Resolution", result)
        return result
    
    def benchmark_parameter_parsing(self) -> TimingResult:
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
        
        def test_parsing():
            return simple_parse_query(query_string)
        
        result = self.timer.time_function(test_parsing)
        self.print_timing_results("Parameter Parsing", result)
        return result
    
    def benchmark_dependency_injection(self) -> TimingResult:
        """Benchmark dependency injection performance."""
        print("💉 Benchmarking dependency injection...")
        
        class UserService:
            def get_user(self, user_id: int):
                return {"id": user_id, "name": "Test User"}
        
        def get_user_service():
            return UserService()
        
        def simulate_di():
            service = get_user_service()
            return service.get_user(123)
        
        result = self.timer.time_function(simulate_di)
        self.print_timing_results("Dependency Injection", result)
        return result
    
    def benchmark_response_creation(self) -> Dict[str, TimingResult]:
        """Benchmark response object creation."""
        print("📤 Benchmarking response creation...")
        
        test_data = generate_test_user_data(100)
        
        # Use mixin methods for consistent benchmarking
        json_result = self.benchmark_json_response_creation(test_data)
        text_result = self.benchmark_text_response_creation("Hello, World!")
        
        self.print_timing_results("JSON Response Creation", json_result)
        self.print_timing_results("Text Response Creation", text_result)
        
        return {
            'json': json_result,
            'text': text_result
        }
    
    def benchmark_json_serialization(self) -> Dict[str, TimingResult]:
        """Benchmark JSON serialization with different data sizes."""
        print("🔄 Benchmarking JSON serialization...")
        
        results = {}
        for size in ["small", "medium", "large"]:
            test_data = generate_test_api_response(size)
            
            def serialize_json():
                response = JSONResponse(test_data)
                return response.render(test_data)
            
            result = self.timer.time_function(serialize_json)
            self.print_timing_results(f"JSON Serialization ({size})", result)
            results[size] = result
        
        return results
    
    def benchmark_middleware_performance(self) -> TimingResult:
        """Benchmark middleware execution overhead."""
        print("🔀 Benchmarking middleware performance...")
        
        app = Velithon()
        
        # Simple middleware that adds a header
        class TestMiddleware:
            async def __call__(self, scope, receive, send):
                # Simple passthrough with header modification
                scope['test_header'] = 'benchmark'
                # In real middleware, this would call the next app
                return {"processed": True}
        
        middleware = TestMiddleware()
        
        def test_middleware():
            scope = {'type': 'http', 'method': 'GET'}
            return asyncio.run(middleware(scope, None, None))
        
        result = self.timer.time_function(test_middleware)
        self.print_timing_results("Middleware Overhead", result)
        return result
    
    def benchmark_caching_performance(self) -> Dict[str, Any]:
        """Benchmark various caching scenarios."""
        print("🗄️ Benchmarking caching performance...")
        
        # Use cache benchmark mixin
        cache_results = self.benchmark_lru_cache_performance(128)
        
        print(f"  Cache speedup: {cache_results['speedup']:.2f}x")
        self.print_timing_results("Cached Operations", cache_results['cached'])
        self.print_timing_results("Uncached Operations", cache_results['uncached'])
        
        return cache_results
    
    async def benchmark_async_performance(self) -> TimingResult:
        """Benchmark async operation performance."""
        print("⚡ Benchmarking async performance...")
        
        async def async_operation():
            # Simulate async work
            await asyncio.sleep(0.001)  # 1ms delay
            return {"result": "async_complete"}
        
        result = await self.timer.time_async_function(async_operation)
        self.print_timing_results("Async Operations", result)
        return result
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run the complete benchmark suite."""
        print("🚀 Starting Comprehensive Performance Benchmark")
        print("=" * 60)
        
        # Run all benchmarks
        signature_result = self.benchmark_signature_resolution()
        parsing_result = self.benchmark_parameter_parsing()
        di_result = self.benchmark_dependency_injection()
        response_results = self.benchmark_response_creation()
        json_results = self.benchmark_json_serialization()
        middleware_result = self.benchmark_middleware_performance()
        cache_results = self.benchmark_caching_performance()
        async_result = await self.benchmark_async_performance()
        
        # Store all results
        self.results.update({
            'signature_resolution': signature_result,
            'parameter_parsing': parsing_result,
            'dependency_injection': di_result,
            'response_creation': response_results,
            'json_serialization': json_results,
            'middleware_performance': middleware_result,
            'caching_performance': cache_results,
            'async_performance': async_result
        })
        
        # Print summary
        print("\n📊 BENCHMARK SUMMARY")
        print("=" * 40)
        
        # Calculate overall performance metrics
        avg_times = []
        for key, result in self.results.items():
            if isinstance(result, TimingResult):
                avg_times.append(result.stats['mean'])
                print(f"{key}: {result.stats['mean']*1000:.3f}ms avg")
        
        if avg_times:
            overall_avg = sum(avg_times) / len(avg_times)
            print(f"\nOverall average operation time: {overall_avg*1000:.3f}ms")
        
        return {
            'timestamp': time.time(),
            'iterations': self.iterations,
            'overall_avg_ms': overall_avg * 1000 if avg_times else 0,
            'detailed_results': self.results
        }


async def run_performance_comparison():
    """Run performance benchmarks and compare with baseline."""
    print("🔬 Starting Performance Analysis")
    
    # Create benchmark with reasonable iterations for comprehensive testing
    benchmark = PerformanceBenchmark(iterations=2000)
    
    # Run benchmarks with memory profiling
    benchmark.memory_profiler.start_profiling()
    results = await benchmark.run_benchmark()
    memory_stats = benchmark.memory_profiler.stop_profiling()
    
    # Print memory usage
    print("\n💾 MEMORY USAGE")
    print("=" * 30)
    benchmark.print_memory_results("Benchmark Memory Usage", memory_stats)
    
    # Save results
    benchmark.save_results('performance_benchmark_results.json')
    print("\n📄 Detailed results saved to: performance_benchmark_results.json")
    
    return results


async def main():
    """Main function to run comprehensive performance benchmarks."""
    try:
        results = await run_performance_comparison()
        
        # Performance assessment
        overall_avg = results.get('overall_avg_ms', 0)
        
        print("\n🎯 PERFORMANCE ASSESSMENT")
        print("=" * 40)
        print(f"Overall average operation time: {overall_avg:.3f}ms")
        
        if overall_avg < 1.0:
            print("✅ EXCELLENT performance (sub-millisecond)")
        elif overall_avg < 10.0:
            print("✅ GOOD performance")
        elif overall_avg < 50.0:
            print("⚠️ ACCEPTABLE performance")
        else:
            print("❌ POOR performance - optimization needed")
        
        return True
    
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
