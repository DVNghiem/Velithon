#!/usr/bin/env python3
"""
Advanced benchmark suite for testing optimization improvements.
Refactored to use base benchmark classes and eliminate duplication.
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Velithon imports
from velithon.application import Velithon
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

# Base benchmark imports
from base_benchmark import (
    BaseBenchmark,
    CacheBenchmarkMixin,
    ResponseBenchmarkMixin,
    TimingResult,
    generate_test_api_response,
    generate_test_user_data,
)


class AdvancedBenchmarkSuite(BaseBenchmark, ResponseBenchmarkMixin, CacheBenchmarkMixin):
    """Advanced benchmark suite using base classes for testing optimization improvements."""
    
    def __init__(self, iterations: int = 10000):
        super().__init__(iterations)
        self.setup_test_app()
    
    def setup_test_app(self):
        """Set up test Velithon application."""
        self.app = Velithon()
        
        # Add test routes using cleaner syntax
        @self.app.get("/json")
        async def json_endpoint(request: Request) -> JSONResponse:
            data = {
                "message": "Hello World",
                "timestamp": time.time(),
                "request_id": getattr(request.scope, '_request_id', 'test'),
                "data": list(range(10))
            }
            return JSONResponse(data)
        
        @self.app.get("/simple")
        async def simple_json_endpoint(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})
        
        @self.app.get("/text")
        async def text_endpoint(request: Request) -> PlainTextResponse:
            return PlainTextResponse("Hello World")
    
    def benchmark_optimized_json_response(self) -> Dict[str, TimingResult]:
        """Benchmark optimized JSON response creation."""
        print("🧪 Testing optimized JSON response creation...")
        
        test_data = generate_test_api_response("medium")
        
        if HAS_OPTIMIZATIONS:
            # Test with optimizations
            def optimized_json_creation():
                encoder = get_json_encoder()
                return encoder.encode(test_data)
            
            optimized_result = self.timer.time_function(optimized_json_creation)
            self.print_timing_results("Optimized JSON Creation", optimized_result)
        else:
            optimized_result = None
        
        # Test standard JSON creation for comparison
        standard_result = self.benchmark_json_response_creation(test_data)
        self.print_timing_results("Standard JSON Creation", standard_result)
        
        results = {"standard": standard_result}
        if optimized_result:
            results["optimized"] = optimized_result
            speedup = self.calculate_speedup(
                standard_result.stats['mean'], 
                optimized_result.stats['mean']
            )
            results["speedup"] = speedup
            print(f"  Optimization speedup: {speedup:.2f}x")
        
        return results
    
    def benchmark_response_caching(self) -> Dict[str, Any]:
        """Benchmark response caching performance."""
        print("🗄️ Testing response caching...")
        
        if not HAS_OPTIMIZATIONS:
            print("  Skipping - optimizations not available")
            return {"status": "skipped"}
        
        test_data = generate_test_user_data(50)
        response_cache = get_response_cache()
        
        # Cache miss (first access)
        def cache_miss():
            cache_key = "test_response_123"
            cached = response_cache.get(cache_key)
            if cached is None:
                # Simulate response creation
                import json
                result = json.dumps(test_data).encode()
                response_cache.put(cache_key, result)
                return result
            return cached
        
        miss_result = self.timer.time_function(cache_miss)
        
        # Cache hit (second access)
        def cache_hit():
            cache_key = "test_response_123"
            return response_cache.get(cache_key)
        
        hit_result = self.timer.time_function(cache_hit)
        
        # Calculate cache effectiveness
        cache_speedup = miss_result.stats['mean'] / hit_result.stats['mean']
        
        self.print_timing_results("Cache Miss", miss_result)
        self.print_timing_results("Cache Hit", hit_result)
        print(f"  Cache speedup: {cache_speedup:.2f}x")
        
        return {
            'cache_miss': miss_result,
            'cache_hit': hit_result,
            'speedup': cache_speedup
        }
    
    async def benchmark_concurrent_json_responses(self) -> Dict[str, Any]:
        """Benchmark concurrent JSON response handling using base timer."""
        print("⚡ Testing concurrent JSON response handling...")
        
        test_data = {"id": 123, "message": "test response", "data": list(range(10))}
        
        async def create_json_response():
            response = JSONResponse(test_data)
            return response.body
        
        # Test sequential responses
        sequential_times = []
        for _ in range(100):
            start = time.perf_counter()
            await create_json_response()
            sequential_times.append(time.perf_counter() - start)
        
        # Test concurrent responses
        start_time = time.perf_counter()
        tasks = [create_json_response() for _ in range(100)]
        await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start_time
        
        sequential_total = sum(sequential_times)
        concurrency_speedup = sequential_total / concurrent_time
        
        print(f"  Sequential time: {sequential_total*1000:.3f}ms")
        print(f"  Concurrent time: {concurrent_time*1000:.3f}ms")
        print(f"  Concurrency speedup: {concurrency_speedup:.2f}x")
        
        return {
            'sequential_time': sequential_total,
            'concurrent_time': concurrent_time,
            'speedup': concurrency_speedup,
            'operations': 100
        }
    
    def benchmark_optimized_encoder_performance(self) -> Dict[str, Any]:
        """Benchmark JSON encoder performance improvements."""
        print("🔄 Testing JSON encoder optimizations...")
        
        if not HAS_OPTIMIZATIONS:
            print("  Skipping - optimizations not available")
            return {"status": "skipped"}
        
        # Test different data sizes
        results = {}
        for size in ["small", "medium", "large"]:
            test_data = generate_test_api_response(size)
            
            # Standard encoder
            def standard_encode():
                import json
                return json.dumps(test_data)
            
            # Optimized encoder
            def optimized_encode():
                encoder = get_json_encoder()
                return encoder.encode(test_data)
            
            standard_result = self.timer.time_function(standard_encode)
            optimized_result = self.timer.time_function(optimized_encode)
            
            speedup = self.calculate_speedup(
                standard_result.stats['mean'],
                optimized_result.stats['mean']
            )
            
            self.print_timing_results(f"Standard Encoding ({size})", standard_result)
            self.print_timing_results(f"Optimized Encoding ({size})", optimized_result)
            print(f"  {size} data speedup: {speedup:.2f}x")
            
            results[size] = {
                'standard': standard_result,
                'optimized': optimized_result,
                'speedup': speedup
            }
        
        return results
    
    async def benchmark_memory_efficiency(self) -> Dict[str, Any]:
        """Benchmark memory efficiency of optimizations."""
        print("💾 Testing memory efficiency...")
        
        test_data = generate_test_api_response("large")
        
        # Memory profile standard operations
        def standard_operations():
            responses = []
            for i in range(100):
                data = test_data.copy()
                data['id'] = i
                response = JSONResponse(data)
                responses.append(response.body)
            return len(responses)
        
        memory_result = self.memory_profiler.profile_function(standard_operations)
        
        self.print_memory_results("Standard Operations", memory_result['memory'])
        
        # Test optimized operations if available
        if HAS_OPTIMIZATIONS:
            def optimized_operations():
                encoder = get_json_encoder()
                responses = []
                for i in range(100):
                    data = test_data.copy()
                    data['id'] = i
                    encoded = encoder.encode(data)
                    responses.append(encoded)
                return len(responses)
            
            opt_memory_result = self.memory_profiler.profile_function(optimized_operations)
            self.print_memory_results("Optimized Operations", opt_memory_result['memory'])
            
            memory_improvement = (
                memory_result['memory']['peak_mb'] / 
                opt_memory_result['memory']['peak_mb']
            )
            print(f"  Memory efficiency: {memory_improvement:.2f}x")
            
            return {
                'standard_memory': memory_result['memory'],
                'optimized_memory': opt_memory_result['memory'],
                'improvement': memory_improvement
            }
        
        return {'standard_memory': memory_result['memory']}
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run the complete advanced benchmark suite."""
        print("🚀 Starting Advanced Performance Benchmark Suite")
        print("=" * 60)
        
        # Run all benchmarks
        json_results = self.benchmark_optimized_json_response()
        cache_results = self.benchmark_response_caching()
        concurrent_results = await self.benchmark_concurrent_json_responses()
        encoder_results = self.benchmark_optimized_encoder_performance()
        memory_results = await self.benchmark_memory_efficiency()
        
        # Store results
        self.results.update({
            'optimized_json': json_results,
            'response_caching': cache_results,
            'concurrent_responses': concurrent_results,
            'encoder_optimizations': encoder_results,
            'memory_efficiency': memory_results
        })
        
        # Calculate overall optimization impact
        optimization_impact = self._calculate_optimization_impact()
        
        print("\n🎯 OPTIMIZATION IMPACT SUMMARY")
        print("=" * 50)
        print(f"Overall performance improvement: {optimization_impact:.2f}x")
        
        return {
            'timestamp': time.time(),
            'iterations': self.iterations,
            'has_optimizations': HAS_OPTIMIZATIONS,
            'optimization_impact': optimization_impact,
            'detailed_results': self.results
        }
    
    def _calculate_optimization_impact(self) -> float:
        """Calculate overall optimization impact."""
        speedups = []
        
        # Collect speedup metrics from various benchmarks
        if 'optimized_json' in self.results and 'speedup' in self.results['optimized_json']:
            speedups.append(self.results['optimized_json']['speedup'])
        
        if 'response_caching' in self.results and 'speedup' in self.results['response_caching']:
            speedups.append(self.results['response_caching']['speedup'])
        
        if 'concurrent_responses' in self.results and 'speedup' in self.results['concurrent_responses']:
            speedups.append(self.results['concurrent_responses']['speedup'])
        
        # Calculate geometric mean of speedups for overall impact
        if speedups:
            import math
            geometric_mean = math.exp(sum(math.log(s) for s in speedups) / len(speedups))
            return geometric_mean
        
        return 1.0  # No improvement if no optimizations available


async def main():
    """Main function to run advanced performance benchmarks."""
    try:
        # Create benchmark suite
        suite = AdvancedBenchmarkSuite(iterations=5000)
        
        # Run comprehensive benchmarks
        results = await suite.run_benchmark()
        
        # Save results
        suite.save_results('advanced_benchmark_results.json')
        print("\n📄 Detailed results saved to: advanced_benchmark_results.json")
        
        # Performance assessment
        optimization_impact = results.get('optimization_impact', 1.0)
        
        print("\n🏆 FINAL ASSESSMENT")
        print("=" * 40)
        
        if optimization_impact >= 2.0:
            print("🌟 EXCELLENT optimization impact (2x+ improvement)")
        elif optimization_impact >= 1.5:
            print("✅ GOOD optimization impact (1.5x+ improvement)")
        elif optimization_impact >= 1.2:
            print("⚠️ MODERATE optimization impact (1.2x+ improvement)")
        elif optimization_impact >= 1.0:
            print("❌ MINIMAL optimization impact")
        else:
            print("💥 PERFORMANCE REGRESSION detected!")
        
        if not results.get('has_optimizations', False):
            print("⚠️ Note: Advanced optimizations not available for testing")
        
        return optimization_impact >= 1.0
    
    except Exception as e:
        print(f"❌ Advanced benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
