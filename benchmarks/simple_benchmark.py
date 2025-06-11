#!/usr/bin/env python3
"""
Simple Performance Test to measure current optimization impact.
"""

import asyncio
import time
from typing import Any, Dict

# Base benchmark imports
from base_benchmark import BaseBenchmark, ResponseBenchmarkMixin

# Velithon imports
from velithon.responses import JSONResponse


class SimpleBenchmark(BaseBenchmark, ResponseBenchmarkMixin):
    """Simple benchmark to test current performance."""
    
    def __init__(self, iterations: int = 5000):
        self.iterations = iterations
    
    def benchmark_json_responses(self) -> Dict[str, float]:
        """Benchmark JSON response creation and rendering."""
        print("🧪 Testing JSON response performance...")
        
        times = []
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
        
        # Warmup
        for _ in range(100):
            response = JSONResponse(test_data)
            response.render(test_data)
        
        # Actual benchmark
        for i in range(self.iterations):
            start = time.perf_counter()
            
            response = JSONResponse(test_data)
            content = response.render(test_data)
            
            end = time.perf_counter()
            times.append(end - start)
        
        times.sort()
        mean_time = sum(times) / len(times)
        p95_time = times[int(len(times) * 0.95)]
        p99_time = times[int(len(times) * 0.99)]
        
        print(f"   📈 Mean: {mean_time*1000:.3f}ms")
        print(f"   📈 P95:  {p95_time*1000:.3f}ms") 
        print(f"   📈 P99:  {p99_time*1000:.3f}ms")
        
        return {
            'mean': mean_time,
            'p95': p95_time,
            'p99': p99_time,
            'times': times
        }
    
    def benchmark_throughput(self) -> Dict[str, float]:
        """Benchmark simple throughput."""
        print("🚀 Testing throughput...")
        
        test_data = {
            "id": 1,
            "message": "test message",
            "data": [1, 2, 3, 4, 5]
        }
        
        # Warmup
        for _ in range(100):
            response = JSONResponse(test_data)
            response.render(test_data)
        
        start_time = time.perf_counter()
        
        for i in range(self.iterations):
            test_data["id"] = i
            response = JSONResponse(test_data)
            content = response.render(test_data)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        throughput = self.iterations / total_time
        
        print(f"   📊 Throughput: {throughput:,.0f} responses/sec")
        print(f"   ⏱️ Avg time: {total_time/self.iterations*1000:.3f}ms")
        
        return {
            'throughput': throughput,
            'avg_time': total_time / self.iterations,
            'total_time': total_time
        }
    
    async def benchmark_concurrent(self) -> Dict[str, float]:
        """Benchmark concurrent response creation."""
        print("⚡ Testing concurrent performance...")
        
        async def create_response(i: int):
            data = {
                "id": i,
                "message": f"Message {i}",
                "data": list(range(i % 10))
            }
            response = JSONResponse(data)
            return response.render(data)
        
        num_concurrent = min(100, self.iterations // 10)
        tasks = [create_response(i) for i in range(num_concurrent)]
        
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        throughput = len(tasks) / total_time
        
        print(f"   📈 Concurrent throughput: {throughput:,.0f} responses/sec")
        print(f"   📈 Tasks: {len(tasks)}")
        
        return {
            'concurrent_throughput': throughput,
            'tasks': len(tasks),
            'total_time': total_time
        }
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("🧪 Starting Simple Performance Benchmark")
        print("=" * 50)
        
        results = {
            'timestamp': time.time(),
            'iterations': self.iterations,
            'json_performance': self.benchmark_json_responses(),
            'throughput': self.benchmark_throughput(),
            'concurrent': await self.benchmark_concurrent()
        }
        
        return results


async def compare_with_baseline():
    """Compare current performance with known baseline."""
    print("\n📊 Performance Comparison")
    print("-" * 30)
    
    # Known baseline from original benchmark: 35,510 req/s, 71.4μs JSON time
    baseline_throughput = 35510
    baseline_json_time = 71.4  # μs
    
    # Run current benchmark
    benchmark = SimpleBenchmark(iterations=2000)
    current_results = await benchmark.run_full_benchmark()
    
    current_throughput = current_results['throughput']['throughput']
    current_json_time = current_results['json_performance']['mean'] * 1000000  # Convert to μs
    
    # Calculate improvements
    throughput_ratio = current_throughput / baseline_throughput
    json_improvement = baseline_json_time / current_json_time
    
    print(f"\nBaseline Performance:    {baseline_throughput:,.0f} req/s, {baseline_json_time:.1f}μs JSON")
    print(f"Current Performance:     {current_throughput:,.0f} req/s, {current_json_time:.1f}μs JSON")
    print(f"Throughput Change:       {throughput_ratio:.2f}x")
    print(f"JSON Improvement:        {json_improvement:.2f}x")
    
    if throughput_ratio > 1.0:
        print("✅ Overall performance IMPROVED")
    else:
        print("❌ Overall performance DECREASED")
    
    if json_improvement > 1.0:
        print("✅ JSON performance IMPROVED")
    else:
        print("❌ JSON performance DECREASED")
    
    # Save results
    comparison = {
        'baseline': {
            'throughput': baseline_throughput,
            'json_time_us': baseline_json_time
        },
        'current': current_results,
        'improvements': {
            'throughput_ratio': throughput_ratio,
            'json_improvement': json_improvement
        }
    }
    
    with open('simple_benchmark_results.json', 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    
    print("\n📄 Results saved to: simple_benchmark_results.json")
    
    return comparison


async def main():
    """Main function."""
    comparison = await compare_with_baseline()
    
    # Summary
    throughput_ratio = comparison['improvements']['throughput_ratio']
    json_improvement = comparison['improvements']['json_improvement']
    
    print("\n🎯 FINAL SUMMARY:")
    print(f"Throughput: {throughput_ratio:.2f}x baseline")
    print(f"JSON Speed: {json_improvement:.2f}x baseline")
    
    if throughput_ratio > 0.9 and json_improvement > 1.0:
        print("✅ Optimizations provide NET BENEFIT")
        return True
    else:
        print("❌ Optimizations need further work")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())