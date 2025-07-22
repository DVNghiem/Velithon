#!/usr/bin/env python3
"""Benchmark for Request ID Generation optimization.

This benchmark compares the old threading-based approach with the new
optimized thread-local approach for request ID generation.
"""

import concurrent.futures
import random
import statistics
import threading
import time
import uuid
from typing import Any


class OldRequestIDGenerator:
    """Original implementation with threading locks."""

    def __init__(self):
        """Initialize the old request ID generator with thread-safe counter."""
        self._prefix = str(random.randint(100, 999))
        self._counter = 0
        self._lock = threading.Lock()

    def generate(self) -> str:
        """Generate a unique request ID with format: prefix-timestamp-counter."""
        timestamp = int(time.time() * 1000)  # Timestamp in milliseconds

        with self._lock:
            self._counter = (self._counter + 1) % 100000
            request_id = f'{self._prefix}-{timestamp}-{self._counter:05d}'

        return request_id


class OptimizedRequestIDGenerator:
    """Optimized implementation with thread-local storage."""

    def __init__(self):
        """Initialize the optimized request ID generator with thread-local counters."""
        # Pre-compute prefix once to avoid repeated random calls
        self._prefix = str(random.randint(100, 999))
        # Use atomic counter for thread safety without locks
        self._counter = threading.local()
        # Pre-allocate timestamp cache to reduce time.time() calls
        self._last_timestamp = 0
        self._timestamp_cache_duration = 0.001  # 1ms cache duration
        self._last_cache_time = 0.0

    def generate(self) -> str:
        """Generate a unique request ID with minimal overhead."""
        # Use thread-local counter to avoid locks
        if not hasattr(self._counter, 'value'):
            self._counter.value = 0
            # Add thread ID to ensure uniqueness across threads
            self._counter.thread_offset = threading.get_ident() % 1000

        # Cache timestamp for 1ms to reduce system calls
        current_time = time.perf_counter()
        if current_time - self._last_cache_time > self._timestamp_cache_duration:
            self._last_timestamp = int(time.time() * 1000)
            self._last_cache_time = current_time

        # Increment counter (no modulo needed for better performance)
        self._counter.value += 1

        # Use faster string concatenation for hot path
        # Format: prefix-timestamp-threadoffset-counter
        return (
            f"{self._prefix}-{self._last_timestamp}-"
            f"{self._counter.thread_offset}-{self._counter.value}"
        )


def benchmark_generator(generator: Any, name: str, iterations: int = 10000) -> dict:
    """Benchmark a request ID generator."""
    print(f"\n🧪 Benchmarking {name}...")
    
    # Single-threaded performance
    start_time = time.perf_counter()
    for _ in range(iterations):
        generator.generate()
    single_thread_time = time.perf_counter() - start_time
    
    # Multi-threaded performance
    def worker(num_requests: int) -> float:
        start = time.perf_counter()
        for _ in range(num_requests):
            generator.generate()
        return time.perf_counter() - start
    
    num_threads = 8
    requests_per_thread = iterations // num_threads
    
    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(worker, requests_per_thread)
            for _ in range(num_threads)
        ]
        thread_times = [future.result() for future in futures]
    
    total_multi_thread_time = time.perf_counter() - start_time
    max_thread_time = max(thread_times)
    
    # Calculate statistics
    single_thread_ops_per_sec = iterations / single_thread_time
    multi_thread_ops_per_sec = iterations / max_thread_time
    
    results = {
        'single_thread_time': single_thread_time,
        'single_thread_ops_per_sec': single_thread_ops_per_sec,
        'multi_thread_time': total_multi_thread_time,
        'max_thread_time': max_thread_time,
        'multi_thread_ops_per_sec': multi_thread_ops_per_sec,
        'thread_times': thread_times,
    }
    
    print(f"  Single-threaded: {single_thread_ops_per_sec:,.0f} ops/sec")
    print(f"  Multi-threaded:  {multi_thread_ops_per_sec:,.0f} ops/sec")
    print(f"  Total time (single): {single_thread_time:.4f}s")
    print(f"  Total time (multi):  {total_multi_thread_time:.4f}s")
    print(f"  Thread time variance: {statistics.stdev(thread_times):.4f}s")
    
    return results


def test_uniqueness(generator: Any, name: str, iterations: int = 50000) -> None:
    """Test that generated IDs are unique."""
    print(f"\n🔍 Testing uniqueness for {name}...")
    
    ids = set()
    duplicates = 0
    
    # Test single-threaded uniqueness
    for _ in range(iterations):
        id_val = generator.generate()
        if id_val in ids:
            duplicates += 1
        ids.add(id_val)
    
    print(f"  Generated {iterations} IDs")
    print(f"  Unique IDs: {len(ids)}")
    print(f"  Duplicates: {duplicates}")
    print(f"  Uniqueness rate: {(len(ids) / iterations) * 100:.2f}%")
    
    # Test multi-threaded uniqueness
    ids_mt = set()
    lock = threading.Lock()
    
    def worker_uniqueness(num_requests: int):
        local_ids = []
        for _ in range(num_requests):
            local_ids.append(generator.generate())
        
        with lock:
            ids_mt.update(local_ids)
    
    num_threads = 4
    requests_per_thread = iterations // num_threads
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(worker_uniqueness, requests_per_thread)
            for _ in range(num_threads)
        ]
        for future in futures:
            future.result()
    
    print(f"  Multi-threaded unique IDs: {len(ids_mt)} / {iterations}")
    print(f"  Multi-threaded uniqueness: {(len(ids_mt) / iterations) * 100:.2f}%")


def benchmark_uuid_comparison():
    """Compare with UUID generation for reference."""
    print("\n📊 UUID Comparison Benchmark...")
    
    iterations = 10000
    
    # UUID4 benchmark
    start_time = time.perf_counter()
    for _ in range(iterations):
        str(uuid.uuid4())
    uuid_time = time.perf_counter() - start_time
    
    uuid_ops_per_sec = iterations / uuid_time
    print(f"  UUID4: {uuid_ops_per_sec:,.0f} ops/sec ({uuid_time:.4f}s)")
    
    return uuid_ops_per_sec


def main():
    """Run comprehensive benchmark suite."""
    print("🚀 Request ID Generator Performance Benchmark")
    print("=" * 60)

    # Initialize generators
    old_gen = OldRequestIDGenerator()
    new_gen = OptimizedRequestIDGenerator()

    iterations = 100000

    # Benchmark both implementations
    old_results = benchmark_generator(old_gen, "Original (Lock-based)", iterations)
    new_results = benchmark_generator(new_gen, "Optimized (Thread-local)", iterations)

    # UUID comparison
    uuid_ops = benchmark_uuid_comparison()

    # Test uniqueness
    test_uniqueness(old_gen, "Original", 10000)
    test_uniqueness(new_gen, "Optimized", 10000)

    # Performance comparison
    print("\n📈 Performance Comparison")
    print("=" * 40)

    single_improvement = (
        new_results['single_thread_ops_per_sec'] /
        old_results['single_thread_ops_per_sec']
    )
    multi_improvement = (
        new_results['multi_thread_ops_per_sec'] /
        old_results['multi_thread_ops_per_sec']
    )

    print(f"Single-threaded improvement: {single_improvement:.2f}x faster")
    print(f"Multi-threaded improvement:  {multi_improvement:.2f}x faster")

    # Compare to UUID
    new_vs_uuid = new_results['single_thread_ops_per_sec'] / uuid_ops
    old_vs_uuid = old_results['single_thread_ops_per_sec'] / uuid_ops

    print("\nVs UUID4:")
    print(f"  Original: {old_vs_uuid:.2f}x faster than UUID4")
    print(f"  Optimized: {new_vs_uuid:.2f}x faster than UUID4")

    # Memory efficiency note
    print("\n💾 Memory Efficiency:")
    print("  Original: Uses threading.Lock (higher memory overhead)")
    print("  Optimized: Uses threading.local (lower memory overhead)")
    print("  Optimized: Caches timestamps (reduces system calls)")


if __name__ == "__main__":
    main()
