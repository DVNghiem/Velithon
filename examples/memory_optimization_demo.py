#!/usr/bin/env python3
"""
Memory Optimization Demo for Velithon
=====================================

This script demonstrates the memory optimization features implemented in Velithon.
"""

import json
import time
from velithon._velithon import StringInterner, MemoryAwareLRUCache, MemoryStats

def demo_memory_stats():
    """Demonstrate memory statistics tracking."""
    print("🔢 Memory Statistics Demo")
    print("-" * 40)
    
    stats = MemoryStats()
    
    # Simulate various allocations
    allocations = [1024, 2048, 4096, 8192, 1024, 2048]
    for i, size in enumerate(allocations):
        stats.record_allocation(size)
        print(f"  Allocation {i+1}: {size} bytes")
    
    print(f"\n  Current stats: {stats.get_stats()}")
    
    # Simulate some deallocations
    for size in allocations[:3]:
        stats.record_deallocation(size)
        print(f"  Deallocated: {size} bytes")
    
    final_stats = stats.get_stats()
    print(f"\n  Final stats: {final_stats}")
    print(f"  Peak memory: {final_stats['peak_allocated_mb']} MB")
    print(f"  Current memory: {final_stats['allocated_mb']} MB\n")

def demo_string_interner():
    """Demonstrate string interning for memory efficiency."""
    print("🔤 String Interner Demo")
    print("-" * 40)
    
    interner = StringInterner()
    
    # Common strings that would appear frequently in web applications
    common_strings = [
        "application/json", "Content-Type", "Authorization", "User-Agent",
        "application/json", "text/html", "Content-Type", "Cache-Control",
        "application/json", "Accept", "User-Agent", "text/html"
    ]
    
    print("  Interning common HTTP headers and content types...")
    start_time = time.time()
    
    interned_strings = []
    for s in common_strings:
        interned = interner.intern(s)
        interned_strings.append(interned)
    
    end_time = time.time()
    
    stats = interner.get_stats()
    print(f"  Processed {len(common_strings)} strings in {end_time - start_time:.4f}s")
    print(f"  Unique strings stored: {stats['current_strings']}")
    print(f"  Cache hit rate: {stats['hit_rate_percent']}%")
    print(f"  Memory saved by interning duplicates!\n")

def demo_lru_cache():
    """Demonstrate memory-aware LRU cache."""
    print("💾 Memory-Aware LRU Cache Demo")
    print("-" * 40)
    
    # Create a small cache for demo purposes
    cache = MemoryAwareLRUCache(max_entries=5, max_memory_mb=1)
    
    # Sample data that might be cached in a web application
    sample_data = {
        "user_profile": {"id": 123, "name": "John Doe", "email": "john@example.com"},
        "product_list": [{"id": i, "name": f"Product {i}", "price": i * 10} for i in range(10)],
        "config": {"theme": "dark", "language": "en", "features": ["feature1", "feature2"]},
        "stats": {"visits": 1000, "users": 250, "conversion": 0.05},
        "large_data": {"data": list(range(1000))}  # This might trigger eviction
    }
    
    print("  Caching sample application data...")
    
    # Cache the data
    for key, value in sample_data.items():
        json_str = json.dumps(value)
        try:
            cache.put(key, json_str)
            print(f"  ✓ Cached '{key}' ({len(json_str)} bytes)")
        except Exception as e:
            print(f"  ✗ Failed to cache '{key}': {e}")
    
    # Test retrieval
    print("\n  Testing cache retrieval...")
    for key in sample_data.keys():
        cached_value = cache.get(key)
        if cached_value:
            print(f"  ✓ Retrieved '{key}' from cache")
        else:
            print(f"  ✗ '{key}' not found in cache (may have been evicted)")
    
    stats = cache.get_stats()
    print(f"\n  Cache Statistics:")
    print(f"    Entries: {stats['entries']}")
    print(f"    Memory used: {stats['memory_mb']} MB")
    print(f"    Hit rate: {stats['hit_rate_percent']}%")
    print(f"    Evictions: {stats['evictions']}")
    print(f"    Memory evictions: {stats['memory_evictions']}\n")

def demo_performance_comparison():
    """Demonstrate performance benefits of memory optimizations."""
    print("⚡ Performance Comparison Demo")
    print("-" * 40)
    
    # String interning performance
    interner = StringInterner()
    test_strings = ["header_" + str(i % 100) for i in range(1000)]  # Many duplicates
    
    start_time = time.time()
    for s in test_strings:
        interner.intern(s)
    interner_time = time.time() - start_time
    
    stats = interner.get_stats()
    print(f"  String Interning:")
    print(f"    Processed 1000 strings with duplicates in {interner_time:.4f}s")
    print(f"    Hit rate: {stats['hit_rate_percent']}% (higher is better)")
    print(f"    Memory saved by deduplication!")
    
    # Cache performance
    cache = MemoryAwareLRUCache(max_entries=100, max_memory_mb=10)
    
    # Cache some data
    for i in range(50):
        cache.put(f"key_{i}", f"value_{i}_" + "x" * 100)
    
    # Time cache lookups
    start_time = time.time()
    hits = 0
    for i in range(100):
        if cache.get(f"key_{i % 50}"):
            hits += 1
    cache_time = time.time() - start_time
    
    cache_stats = cache.get_stats()
    print(f"\n  Memory-Aware Cache:")
    print(f"    100 lookups completed in {cache_time:.4f}s")
    print(f"    Hit rate: {cache_stats['hit_rate_percent']}%")
    print(f"    Automatic memory management prevents OOM errors!")

def main():
    """Run all memory optimization demos."""
    print("🚀 Velithon Memory Optimization Demo")
    print("=" * 50)
    print("Showcasing high-performance memory management features\n")
    
    demo_memory_stats()
    demo_string_interner()
    demo_lru_cache()
    demo_performance_comparison()
    
    print("🎉 Demo completed!")
    print("These optimizations help Velithon applications:")
    print("  • Reduce memory usage through string interning")
    print("  • Prevent memory leaks with automatic statistics")
    print("  • Handle large datasets with memory-aware caching") 
    print("  • Scale better under high load")

if __name__ == "__main__":
    main()
