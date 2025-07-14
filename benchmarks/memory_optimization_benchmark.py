#!/usr/bin/env python3
"""Comprehensive memory optimization benchmark for Velithon."""

from __future__ import annotations

import asyncio
import gc
import time
import tracemalloc
from typing import Any

import pytest

# Test the memory optimization components
try:
    from velithon._velithon import (
        StringInterner,
        MemoryAwareLRUCache,
        MemoryStats
    )
    from velithon.memory import (
        MemoryOptimizedResponseCache,
        MemoryAwareRequestHandler,
        get_global_memory_handler,
        cleanup_memory,
        get_memory_stats
    )
    HAS_OPTIMIZATIONS = True
except ImportError as e:
    print(f"⚠️  Memory optimizations not available: {e}")
    HAS_OPTIMIZATIONS = False

# Simple JSON response for testing
import json

class JSONResponse:
    def __init__(self, data):
        self.data = data
        self.body = json.dumps(data).encode()
        self.headers = {"Content-Type": "application/json"}
    
    def __len__(self):
        return len(self.body)

class OptimizedJSONResponse:
    def __init__(self, data):
        self.data = data
        self.body = json.dumps(data).encode()
        self.headers = {"Content-Type": "application/json"}
    
    def __len__(self):
        return len(self.body)
except ImportError as e:
    print(f"⚠️  Memory optimizations not available: {e}")
    HAS_OPTIMIZATIONS = False


def generate_test_data(size: str = 'medium') -> dict[str, Any]:
    """Generate test data of various sizes."""
    sizes = {
        'small': 100,
        'medium': 1000,
        'large': 10000,
        'xlarge': 50000,
    }
    
    count = sizes.get(size, 1000)
    
    return {
        'users': [
            {
                'id': i,
                'name': f'User {i}',
                'email': f'user{i}@example.com',
                'metadata': {
                    'created_at': f'2023-01-{(i % 30) + 1:02d}',
                    'scores': [j * 2 for j in range(min(20, i % 50))],
                    'active': i % 3 == 0,
                }
            }
            for i in range(count)
        ],
        'pagination': {
            'total': count,
            'pages': (count // 50) + 1,
            'current_page': 1,
        },
        'metadata': {
            'generated_at': time.time(),
            'size': size,
        }
    }


class MemoryBenchmark:
    """Memory optimization benchmarking suite."""
    
    def __init__(self, iterations: int = 100):
        self.iterations = iterations
        self.results = {}
    
    def run_memory_pool_benchmark(self) -> dict[str, Any]:
        """Benchmark memory pool performance."""
        print("🔧 Testing Memory Pool Performance...")
        
        if not HAS_OPTIMIZATIONS:
            return {"error": "Memory optimizations not available"}
        
        pool = MemoryPool(max_size_per_pool=100)
        
        # Test allocation/deallocation patterns
        tracemalloc.start()
        start_time = time.perf_counter()
        
        allocated_ptrs = []
        sizes = [64, 128, 256, 512, 1024, 2048]
        
        # Allocation phase
        for i in range(self.iterations):
            size = sizes[i % len(sizes)]
            try:
                ptr = pool.allocate(size)
                allocated_ptrs.append((ptr, size))
            except Exception as e:
                print(f"Allocation failed: {e}")
        
        allocation_time = time.perf_counter() - start_time
        
        # Deallocation phase
        dealloc_start = time.perf_counter()
        for ptr, size in allocated_ptrs:
            try:
                pool.deallocate(ptr, size)
            except Exception as e:
                print(f"Deallocation failed: {e}")
        
        deallocation_time = time.perf_counter() - dealloc_start
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        pool_stats = pool.get_stats()
        
        return {
            'allocation_time_ms': allocation_time * 1000,
            'deallocation_time_ms': deallocation_time * 1000,
            'total_time_ms': (allocation_time + deallocation_time) * 1000,
            'memory_current_mb': current / 1024 / 1024,
            'memory_peak_mb': peak / 1024 / 1024,
            'pool_stats': pool_stats,
        }
    
    def run_string_interner_benchmark(self) -> dict[str, Any]:
        """Benchmark string interning performance."""
        print("📝 Testing String Interner Performance...")
        
        if not HAS_OPTIMIZATIONS:
            return {"error": "Memory optimizations not available"}
        
        interner = StringInterner()
        
        # Generate test strings
        test_strings = [
            f"user_{i}@example.com" for i in range(1000)
        ] * 10  # Repeat for interning benefits
        
        tracemalloc.start()
        start_time = time.perf_counter()
        
        interned_strings = []
        for s in test_strings:
            interned = interner.intern(s)
            interned_strings.append(interned)
        
        intern_time = time.perf_counter() - start_time
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        interner_stats = interner.get_stats()
        
        return {
            'intern_time_ms': intern_time * 1000,
            'strings_processed': len(test_strings),
            'unique_strings': len(set(test_strings)),
            'memory_current_mb': current / 1024 / 1024,
            'memory_peak_mb': peak / 1024 / 1024,
            'interner_stats': interner_stats,
        }
    
    def run_lru_cache_benchmark(self) -> dict[str, Any]:
        """Benchmark memory-aware LRU cache."""
        print("💾 Testing Memory-Aware LRU Cache...")
        
        if not HAS_OPTIMIZATIONS:
            return {"error": "Memory optimizations not available"}
        
        cache = MemoryAwareLRUCache(max_entries=500, max_memory_mb=10)
        
        # Generate test data
        test_objects = []
        for i in range(1000):
            obj = {
                'id': i,
                'data': [j for j in range(i % 100)],
                'metadata': f'object_{i}' * 10,
            }
            test_objects.append((f'key_{i}', obj))
        
        tracemalloc.start()
        start_time = time.perf_counter()
        
        # Fill cache
        for key, obj in test_objects:
            try:
                cache.put(key, obj)
            except Exception as e:
                print(f"Cache put failed for {key}: {e}")
        
        put_time = time.perf_counter() - start_time
        
        # Test retrieval
        get_start = time.perf_counter()
        hits = 0
        misses = 0
        
        for key, _ in test_objects[:200]:  # Test subset
            result = cache.get(key)
            if result is not None:
                hits += 1
            else:
                misses += 1
        
        get_time = time.perf_counter() - get_start
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        cache_stats = cache.get_stats()
        
        return {
            'put_time_ms': put_time * 1000,
            'get_time_ms': get_time * 1000,
            'hit_ratio': hits / (hits + misses) if (hits + misses) > 0 else 0,
            'memory_current_mb': current / 1024 / 1024,
            'memory_peak_mb': peak / 1024 / 1024,
            'cache_stats': cache_stats,
        }
    
    def run_response_cache_benchmark(self) -> dict[str, Any]:
        """Benchmark optimized response caching."""
        print("📊 Testing Response Cache Performance...")
        
        if not HAS_OPTIMIZATIONS:
            return {"error": "Memory optimizations not available"}
        
        response_cache = MemoryOptimizedResponseCache(
            max_entries=200,
            max_memory_mb=20,
        )
        
        # Generate test responses
        test_data = generate_test_data('medium')
        
        tracemalloc.start()
        start_time = time.perf_counter()
        
        # Cache responses
        for i in range(self.iterations):
            cache_key = f"response_{i % 50}"  # Some overlap for cache hits
            data = test_data.copy()
            data['request_id'] = i
            
            # Try to get from cache first
            cached = response_cache.get(cache_key)
            if cached is None:
                # Simulate response creation and caching
                response_cache.put(cache_key, data)
        
        cache_time = time.perf_counter() - start_time
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        cache_stats = response_cache.get_stats()
        
        return {
            'cache_time_ms': cache_time * 1000,
            'requests_processed': self.iterations,
            'memory_current_mb': current / 1024 / 1024,
            'memory_peak_mb': peak / 1024 / 1024,
            'cache_stats': cache_stats,
        }
    
    def run_json_response_comparison(self) -> dict[str, Any]:
        """Compare standard vs optimized JSON responses."""
        print("🚀 Comparing JSON Response Performance...")
        
        test_data = generate_test_data('large')
        
        # Standard JSON Response
        tracemalloc.start()
        standard_start = time.perf_counter()
        
        standard_responses = []
        for i in range(50):  # Reduced iterations for large data
            data = test_data.copy()
            data['request_id'] = i
            response = JSONResponse(data)
            standard_responses.append(response.body)
        
        standard_time = time.perf_counter() - standard_start
        standard_current, standard_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Clear memory between tests
        gc.collect()
        
        # Optimized JSON Response
        optimized_results = {"error": "Optimized responses not available"}
        if HAS_OPTIMIZATIONS:
            tracemalloc.start()
            optimized_start = time.perf_counter()
            
            optimized_responses = []
            for i in range(50):
                data = test_data.copy()
                data['request_id'] = i
                response = OptimizedJSONResponse(data)
                optimized_responses.append(response.body)
            
            optimized_time = time.perf_counter() - optimized_start
            optimized_current, optimized_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            optimized_results = {
                'time_ms': optimized_time * 1000,
                'memory_current_mb': optimized_current / 1024 / 1024,
                'memory_peak_mb': optimized_peak / 1024 / 1024,
                'responses_generated': len(optimized_responses),
            }
        
        return {
            'standard': {
                'time_ms': standard_time * 1000,
                'memory_current_mb': standard_current / 1024 / 1024,
                'memory_peak_mb': standard_peak / 1024 / 1024,
                'responses_generated': len(standard_responses),
            },
            'optimized': optimized_results,
        }
    
    async def run_comprehensive_benchmark(self) -> dict[str, Any]:
        """Run all memory benchmarks."""
        print("🏁 Starting Comprehensive Memory Benchmark Suite")
        print("=" * 60)
        
        # Individual component benchmarks
        memory_pool_results = self.run_memory_pool_benchmark()
        string_interner_results = self.run_string_interner_benchmark()
        lru_cache_results = self.run_lru_cache_benchmark()
        response_cache_results = self.run_response_cache_benchmark()
        json_comparison_results = self.run_json_response_comparison()
        
        # Global memory stats
        global_stats = {}
        if HAS_OPTIMIZATIONS:
            global_stats = get_memory_stats()
        
        # Cleanup and final stats
        cleanup_stats = {}
        if HAS_OPTIMIZATIONS:
            cleanup_stats = cleanup_memory()
        
        results = {
            'memory_pool': memory_pool_results,
            'string_interner': string_interner_results,
            'lru_cache': lru_cache_results,
            'response_cache': response_cache_results,
            'json_comparison': json_comparison_results,
            'global_stats': global_stats,
            'cleanup_stats': cleanup_stats,
            'benchmark_config': {
                'iterations': self.iterations,
                'has_optimizations': HAS_OPTIMIZATIONS,
            }
        }
        
        self.print_summary(results)
        return results
    
    def print_summary(self, results: dict[str, Any]) -> None:
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("📈 MEMORY BENCHMARK SUMMARY")
        print("=" * 60)
        
        if not HAS_OPTIMIZATIONS:
            print("⚠️  Memory optimizations not available - compile Rust extensions first")
            return
        
        # Memory Pool
        if 'memory_pool' in results and 'pool_stats' in results['memory_pool']:
            pool_stats = results['memory_pool']['pool_stats']
            print(f"🔧 Memory Pool:")
            print(f"   Cache Hit Rate: {pool_stats.get('cache_hit_rate_percent', 0)}%")
            print(f"   Peak Memory: {results['memory_pool']['memory_peak_mb']:.2f} MB")
        
        # String Interner
        if 'string_interner' in results and 'interner_stats' in results['string_interner']:
            interner_stats = results['string_interner']['interner_stats']
            print(f"📝 String Interner:")
            print(f"   Hit Rate: {interner_stats.get('hit_rate_percent', 0)}%")
            print(f"   Memory Savings: {results['string_interner']['memory_peak_mb']:.2f} MB")
        
        # LRU Cache
        if 'lru_cache' in results and 'cache_stats' in results['lru_cache']:
            cache_stats = results['lru_cache']['cache_stats']
            print(f"💾 LRU Cache:")
            print(f"   Hit Rate: {cache_stats.get('hit_rate_percent', 0)}%")
            print(f"   Memory Usage: {cache_stats.get('memory_mb', 0)} MB")
        
        # JSON Comparison
        if 'json_comparison' in results:
            comparison = results['json_comparison']
            if 'optimized' in comparison and 'error' not in comparison['optimized']:
                standard = comparison['standard']
                optimized = comparison['optimized']
                
                time_improvement = standard['time_ms'] / optimized['time_ms']
                memory_improvement = standard['memory_peak_mb'] / optimized['memory_peak_mb']
                
                print(f"🚀 JSON Response Optimization:")
                print(f"   Speed Improvement: {time_improvement:.2f}x")
                print(f"   Memory Improvement: {memory_improvement:.2f}x")
        
        print("=" * 60)


async def main():
    """Run the memory benchmark suite."""
    benchmark = MemoryBenchmark(iterations=100)
    results = await benchmark.run_comprehensive_benchmark()
    
    # Save results to file
    import json
    with open('memory_benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\n📁 Results saved to memory_benchmark_results.json")


if __name__ == "__main__":
    asyncio.run(main())
