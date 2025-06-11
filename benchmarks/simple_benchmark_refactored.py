#!/usr/bin/env python3
"""
Simple Performance Test to measure current optimization impact.
Refactored to use base benchmark classes.
"""

import asyncio
import time
from typing import Any, Dict

# Base benchmark imports
from base_benchmark import BaseBenchmark, ResponseBenchmarkMixin, TimingResult

# Velithon imports
from velithon.responses import JSONResponse


class SimpleBenchmark(BaseBenchmark, ResponseBenchmarkMixin):
    """Simple benchmark to test current performance using base classes."""
    
    def __init__(self, iterations: int = 5000):
        super().__init__(iterations)
    
    def benchmark_json_responses(self) -> TimingResult:
        """Benchmark JSON response creation and rendering using base timer."""
        print("🧪 Testing JSON response performance...")
        
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
        
        def create_and_render_response():
            response = JSONResponse(test_data)
            return response.render(test_data)
        
        result = self.timer.time_function(create_and_render_response)
        self.print_timing_results("JSON Response Performance", result)
        return result
    
    def benchmark_throughput(self) -> Dict[str, float]:
        """Benchmark simple throughput using base timer."""
        print("🚀 Testing throughput...")
        
        test_data_template = {
            "id": 1,
            "message": "test message",
            "data": [1, 2, 3, 4, 5]
        }
        
        def throughput_test():
            total_processed = 0
            start_time = time.perf_counter()
            
            for i in range(self.iterations):
                test_data = test_data_template.copy()
                test_data["id"] = i
                response = JSONResponse(test_data)
                response.render(test_data)
                total_processed += 1
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            throughput = total_processed / total_time
            
            return {
                'throughput': throughput,
                'total_time': total_time,
                'avg_time': total_time / total_processed
            }
        
        result = throughput_test()
        self.print_throughput_results("Throughput", result['throughput'])
        print(f"    Avg time: {result['avg_time']*1000:.3f}ms")
        
        return result
    
    async def benchmark_concurrent(self) -> Dict[str, float]:
        """Benchmark concurrent response creation using base timer."""
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
        
        start_time = time.perf_counter()
        tasks = [create_response(i) for i in range(num_concurrent)]
        await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        throughput = num_concurrent / total_time
        
        self.print_throughput_results("Concurrent Throughput", throughput)
        print(f"    Tasks: {num_concurrent}")
        
        return {
            'concurrent_throughput': throughput,
            'tasks': num_concurrent,
            'total_time': total_time
        }
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("🧪 Starting Simple Performance Benchmark")
        print("=" * 50)
        
        # Run all benchmarks
        json_result = self.benchmark_json_responses()
        throughput_result = self.benchmark_throughput()
        concurrent_result = await self.benchmark_concurrent()
        
        # Store results
        self.results.update({
            'json_performance': json_result,
            'throughput': throughput_result,
            'concurrent': concurrent_result
        })
        
        return {
            'timestamp': time.time(),
            'iterations': self.iterations,
            **self.results
        }


async def compare_with_baseline():
    """Compare current performance with known baseline."""
    print("\n📊 Performance Comparison")
    print("-" * 30)
    
    # Known baseline from original benchmark: 35,510 req/s, 71.4μs JSON time
    baseline_throughput = 35510
    baseline_json_time = 71.4  # μs
    
    # Run current benchmark
    benchmark = SimpleBenchmark(iterations=2000)
    current_results = await benchmark.run_benchmark()
    
    current_throughput = current_results['throughput']['throughput']
    current_json_time = current_results['json_performance'].stats['mean'] * 1000000  # Convert to μs
    
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
    
    # Save results using base class method
    benchmark.save_results('simple_benchmark_results.json')
    
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
    asyncio.run(main())
