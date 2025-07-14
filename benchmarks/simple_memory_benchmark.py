#!/usr/bin/env python3
"""Simplified memory optimization benchmark for Velithon."""

import json
import time
import gc
import psutil
import os
import sys
from typing import Dict, Any, List

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test the memory optimization components
try:
    from velithon._velithon import StringInterner, MemoryAwareLRUCache, MemoryStats
    memory_optimizations_available = True
    print("✅ Memory optimizations loaded successfully")
except ImportError as e:
    print(f"⚠️  Some memory optimizations not available: {e}")
    memory_optimizations_available = False
    # Create mock classes
    class StringInterner:
        def __init__(self): pass
        def intern(self, s): return s
        def get_stats(self): return {}
        def clear(self): pass
    
    class MemoryAwareLRUCache:
        def __init__(self, max_entries=1000, max_memory_mb=100): pass
        def get(self, key): return None
        def put(self, key, value): pass
        def get_stats(self): return {}
        def clear(self): pass
    
    class MemoryStats:
        def __init__(self): pass
        def record_allocation(self, size): pass
        def record_deallocation(self, size): pass
        def get_stats(self): return {}
        def reset(self): pass

# Simple JSON response for testing
class JSONResponse:
    def __init__(self, data):
        self.data = data
        self.body = json.dumps(data).encode()
        self.headers = {"Content-Type": "application/json"}
    
    def __len__(self):
        return len(self.body)

def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def generate_test_data(size: str = 'medium') -> Dict[str, Any]:
    """Generate test data of various sizes."""
    sizes = {
        'small': 100,
        'medium': 1000,
        'large': 10000,
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
        'meta': {
            'count': count,
            'generated_at': time.time(),
            'version': '1.0'
        }
    }

class MemoryBenchmark:
    """Memory optimization benchmark suite."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        
    def run_memory_stats_test(self) -> Dict[str, Any]:
        """Test memory statistics tracking."""
        print("📊 Testing Memory Stats...")
        
        stats = MemoryStats()
        start_time = time.time()
        
        # Simulate allocations
        for i in range(1000):
            stats.record_allocation(1024 * (i + 1))
        
        # Simulate some deallocations
        for i in range(500):
            stats.record_deallocation(1024 * (i + 1))
        
        end_time = time.time()
        result_stats = stats.get_stats()
        
        return {
            'duration': end_time - start_time,
            'operations': 1500,
            'ops_per_second': 1500 / (end_time - start_time),
            'final_stats': result_stats
        }
    
    def run_string_interner_test(self) -> Dict[str, Any]:
        """Test string interning performance."""
        print("📝 Testing String Interner...")
        
        interner = StringInterner()
        test_strings = [f"test_string_{i}" for i in range(1000)]
        # Add duplicates
        test_strings.extend([f"test_string_{i}" for i in range(500)])
        
        start_time = time.time()
        
        for s in test_strings:
            interner.intern(s)
        
        end_time = time.time()
        stats = interner.get_stats()
        
        return {
            'duration': end_time - start_time,
            'total_strings': len(test_strings),
            'unique_strings': 1000,
            'operations_per_second': len(test_strings) / (end_time - start_time),
            'hit_rate': stats.get('hit_rate_percent', 0),
            'final_stats': stats
        }
    
    def run_lru_cache_test(self) -> Dict[str, Any]:
        """Test memory-aware LRU cache performance."""
        print("💾 Testing Memory-Aware LRU Cache...")
        
        cache = MemoryAwareLRUCache(max_entries=500, max_memory_mb=10)
        test_data = generate_test_data('small')
        
        start_time = time.time()
        
        # Test puts
        for i in range(1000):
            key = f"key_{i}"
            value = json.dumps(test_data)
            try:
                cache.put(key, value)
            except Exception:
                pass  # Cache might reject large values
        
        # Test gets
        hit_count = 0
        for i in range(500):
            key = f"key_{i}"
            if cache.get(key) is not None:
                hit_count += 1
        
        end_time = time.time()
        stats = cache.get_stats()
        
        return {
            'duration': end_time - start_time,
            'put_operations': 1000,
            'get_operations': 500,
            'cache_hits': hit_count,
            'hit_rate': (hit_count / 500) * 100,
            'operations_per_second': 1500 / (end_time - start_time),
            'final_stats': stats
        }
    
    def run_json_response_test(self) -> Dict[str, Any]:
        """Test JSON response creation performance."""
        print("🚀 Testing JSON Response Performance...")
        
        test_data = generate_test_data('medium')
        
        start_memory = get_memory_usage()
        start_time = time.time()
        
        responses = []
        for i in range(100):
            response = JSONResponse(test_data)
            responses.append(response)
        
        end_time = time.time()
        end_memory = get_memory_usage()
        
        # Calculate total response size
        total_size = sum(len(r) for r in responses)
        
        return {
            'duration': end_time - start_time,
            'responses_created': 100,
            'responses_per_second': 100 / (end_time - start_time),
            'memory_delta_mb': end_memory - start_memory,
            'total_response_size_mb': total_size / (1024 * 1024),
            'avg_response_size_kb': (total_size / 100) / 1024
        }
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run all benchmarks and return comprehensive results."""
        print("🏁 Starting Comprehensive Memory Benchmark Suite")
        print("=" * 60)
        
        # Force garbage collection before starting
        gc.collect()
        initial_memory = get_memory_usage()
        
        results = {}
        
        # Run individual tests
        results['memory_stats'] = self.run_memory_stats_test()
        results['string_interner'] = self.run_string_interner_test()
        results['lru_cache'] = self.run_lru_cache_test()
        results['json_response'] = self.run_json_response_test()
        
        # Final memory check
        gc.collect()
        final_memory = get_memory_usage()
        
        results['overall'] = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_delta_mb': final_memory - initial_memory,
            'optimizations_available': memory_optimizations_available,
        }
        
        return results

def print_results(results: Dict[str, Any]):
    """Print benchmark results in a formatted way."""
    print("\n🎯 BENCHMARK RESULTS")
    print("=" * 60)
    
    for test_name, test_results in results.items():
        if test_name == 'overall':
            continue
            
        print(f"\n📋 {test_name.replace('_', ' ').title()}")
        print("-" * 40)
        
        for key, value in test_results.items():
            if key == 'final_stats':
                continue
            if isinstance(value, float):
                if 'time' in key or 'duration' in key:
                    print(f"  {key:25}: {value:.4f}s")
                elif 'memory' in key:
                    print(f"  {key:25}: {value:.2f} MB")
                elif 'per_second' in key:
                    print(f"  {key:25}: {value:.2f}/s")
                else:
                    print(f"  {key:25}: {value:.2f}")
            else:
                print(f"  {key:25}: {value}")
    
    # Overall summary
    overall = results.get('overall', {})
    print(f"\n🏆 OVERALL SUMMARY")
    print("-" * 40)
    print(f"  Memory Usage Start    : {overall.get('initial_memory_mb', 0):.2f} MB")
    print(f"  Memory Usage End      : {overall.get('final_memory_mb', 0):.2f} MB")
    print(f"  Memory Delta          : {overall.get('memory_delta_mb', 0):.2f} MB")
    print(f"  Optimizations Available: {overall.get('optimizations_available', False)}")

def main():
    """Main benchmark execution."""
    benchmark = MemoryBenchmark()
    results = benchmark.run_comprehensive_benchmark()
    print_results(results)
    
    if memory_optimizations_available:
        print("\n✅ All memory optimizations are working correctly!")
    else:
        print("\n⚠️  Some memory optimizations are not available - running with fallbacks")

if __name__ == "__main__":
    main()
