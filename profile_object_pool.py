#!/usr/bin/env python3
"""
Profile the object pool performance to identify bottlenecks.
"""
import time
from velithon.optimizations import ObjectPool, get_dict_from_pool, return_dict_to_pool

# Test parameters
iterations = 100000
pool_times = []
direct_times = []

# Test object pool performance
print("Testing object pool performance...")
for _ in range(5):  # Run multiple tests to get reliable results
    start = time.perf_counter()
    for i in range(iterations):
        d = get_dict_from_pool()
        d['test'] = i
        return_dict_to_pool(d)
    end = time.perf_counter()
    pool_times.append(end - start)

# Test direct dict creation performance
print("Testing direct dict creation...")
for _ in range(5):  # Run multiple tests to get reliable results
    start = time.perf_counter()
    for i in range(iterations):
        d = {}
        d['test'] = i
        # No cleanup needed
    end = time.perf_counter()
    direct_times.append(end - start)

# Calculate average times
avg_pool_time = sum(pool_times) / len(pool_times)
avg_direct_time = sum(direct_times) / len(direct_times)

print(f"\nResults for {iterations} iterations:")
print(f"Object pool access time: {avg_pool_time*1000:.2f}ms")
print(f"Direct dict creation time: {avg_direct_time*1000:.2f}ms")
print(f"Performance ratio: {avg_direct_time/avg_pool_time:.2f}x (>1 means pool is faster)")
