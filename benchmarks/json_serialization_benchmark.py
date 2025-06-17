#!/usr/bin/env python3
"""Benchmark script for testing the new Rust-based JSON serialization optimization."""

from __future__ import annotations

import asyncio
import random
import string
import time
from typing import Any

# Standard library JSON
from velithon.responses import JSONResponse as StandardJSONResponse

# New optimized JSON responses (will be available after compilation)
try:
    from velithon.json_responses import (
        BatchJSONResponse,
        OptimizedJSONResponse,
    )

    HAS_OPTIMIZED = True
except ImportError:
    HAS_OPTIMIZED = False
    print(
        '⚠️  Optimized JSON responses not available. '
        'Please compile Rust extensions first.'
    )


def generate_large_dict(size: int) -> dict[str, Any]:
    """Generate a large dictionary for testing."""
    return {
        f'key_{i}': {
            'id': i,
            'name': f'Item {i}',
            'description': ''.join(random.choices(string.ascii_letters, k=50)),
            'tags': [f'tag_{j}' for j in range(5)],
            'metadata': {
                'created_at': time.time(),
                'updated_at': time.time(),
                'version': random.randint(1, 100),
            },
            'values': [random.uniform(0, 100) for _ in range(10)],
        }
        for i in range(size)
    }


def generate_large_list(size: int) -> list[dict[str, Any]]:
    """Generate a large list of objects for testing."""
    return [
        {
            'id': i,
            'name': f'User {i}',
            'email': f'user{i}@example.com',
            'age': random.randint(18, 80),
            'preferences': {
                'theme': random.choice(['light', 'dark']),
                'language': random.choice(['en', 'es', 'fr', 'de']),
                'notifications': random.choice([True, False]),
            },
            'scores': [random.uniform(0, 100) for _ in range(20)],
            'history': [f'action_{j}' for j in range(random.randint(5, 15))],
        }
        for i in range(size)
    ]


def benchmark_standard_json(data: Any, iterations: int = 100) -> dict[str, float]:
    """Benchmark standard JSON response."""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        response = StandardJSONResponse(data)
        rendered = response.render(data)
        end = time.perf_counter()
        times.append(end - start)

    return {
        'mean_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'total_time': sum(times),
        'data_size': len(str(data)),
        'output_size': len(rendered) if 'rendered' in locals() else 0,
    }


def benchmark_optimized_json(
    data: Any, iterations: int = 100, parallel_threshold: int = 100
) -> dict[str, float]:
    """Benchmark optimized JSON response."""
    if not HAS_OPTIMIZED:
        return {'error': 'Optimized JSON not available'}

    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        response = OptimizedJSONResponse(data, parallel_threshold=parallel_threshold)
        rendered = response.render(data)
        end = time.perf_counter()
        times.append(end - start)

    return {
        'mean_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'total_time': sum(times),
        'data_size': len(str(data)),
        'output_size': len(rendered) if 'rendered' in locals() else 0,
    }


def benchmark_batch_json(objects: list[Any], iterations: int = 100) -> dict[str, float]:
    """Benchmark batch JSON response."""
    if not HAS_OPTIMIZED:
        return {'error': 'Optimized JSON not available'}

    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        response = BatchJSONResponse(objects)
        rendered = response.render(objects)
        end = time.perf_counter()
        times.append(end - start)

    return {
        'mean_time': sum(times) / len(times),
        'min_time': min(times),
        'max_time': max(times),
        'total_time': sum(times),
        'object_count': len(objects),
        'output_size': len(rendered) if 'rendered' in locals() else 0,
    }


def print_benchmark_results(name: str, results: dict[str, float]):
    """Print benchmark results in a formatted way."""
    print(f'\n📊 {name}')
    print('-' * 60)

    if 'error' in results:
        print(f'❌ {results["error"]}')
        return

    mean_ms = results['mean_time'] * 1000
    min_ms = results['min_time'] * 1000
    max_ms = results['max_time'] * 1000
    total_ms = results['total_time'] * 1000

    print(f'⏱️  Mean time:    {mean_ms:.3f}ms')
    print(f'⚡ Min time:     {min_ms:.3f}ms')
    print(f'🐌 Max time:     {max_ms:.3f}ms')
    print(f'🕒 Total time:   {total_ms:.3f}ms')

    if 'data_size' in results:
        print(f'📦 Data size:    {results["data_size"]:,} chars')
    if 'output_size' in results:
        print(f'💾 Output size:  {results["output_size"]:,} bytes')
    if 'object_count' in results:
        print(f'🔢 Object count: {results["object_count"]:,}')


def run_benchmarks():
    """Run comprehensive benchmarks comparing standard vs optimized JSON."""
    print('🚀 JSON Serialization Benchmark Suite')
    print('=' * 60)

    # Test data sizes
    test_sizes = [10, 100, 1000, 5000]

    print('\n🧪 Testing Large Dictionary Serialization')
    print('=' * 60)

    for size in test_sizes:
        print(f'\n📋 Testing with {size:,} dictionary entries...')
        data = generate_large_dict(size)

        # Standard JSON
        std_results = benchmark_standard_json(data, iterations=10)
        print_benchmark_results(f'Standard JSON ({size:,} entries)', std_results)

        # Optimized JSON with auto-detection
        if HAS_OPTIMIZED:
            opt_results = benchmark_optimized_json(
                data, iterations=10, parallel_threshold=50
            )
            print_benchmark_results(f'Optimized JSON ({size:,} entries)', opt_results)

            # Calculate speedup
            if std_results['mean_time'] > 0:
                speedup = std_results['mean_time'] / opt_results['mean_time']
                print(f'🏆 Speedup: {speedup:.2f}x')

    print('\n🧪 Testing Large List Serialization')
    print('=' * 60)

    for size in test_sizes:
        print(f'\n📋 Testing with {size:,} list items...')
        data = generate_large_list(size)

        # Standard JSON
        std_results = benchmark_standard_json(data, iterations=10)
        print_benchmark_results(f'Standard JSON ({size:,} items)', std_results)

        # Optimized JSON
        if HAS_OPTIMIZED:
            opt_results = benchmark_optimized_json(
                data, iterations=10, parallel_threshold=50
            )
            print_benchmark_results(f'Optimized JSON ({size:,} items)', opt_results)

            # Batch JSON
            batch_results = benchmark_batch_json(data, iterations=10)
            print_benchmark_results(f'Batch JSON ({size:,} items)', batch_results)

            # Calculate speedups
            if std_results['mean_time'] > 0:
                opt_speedup = std_results['mean_time'] / opt_results['mean_time']
                batch_speedup = std_results['mean_time'] / batch_results['mean_time']
                print(f'🏆 Optimized Speedup: {opt_speedup:.2f}x')
                print(f'🏆 Batch Speedup: {batch_speedup:.2f}x')

    print('\n🧪 Testing Parallel Threshold Impact')
    print('=' * 60)

    if HAS_OPTIMIZED:
        large_data = generate_large_list(2000)
        thresholds = [10, 50, 100, 500, 1000]

        for threshold in thresholds:
            print(f'\n📋 Testing with parallel threshold: {threshold}')
            results = benchmark_optimized_json(
                large_data, iterations=5, parallel_threshold=threshold
            )
            print_benchmark_results(f'Threshold {threshold}', results)

    print('\n✅ Benchmark Complete!')

    if not HAS_OPTIMIZED:
        print('\n🔧 To enable optimized JSON serialization:')
        print('1. Ensure Rust toolchain is installed')
        print('2. Run: cargo build --release')
        print('3. Run: maturin develop --release')
        print('4. Re-run this benchmark')


async def async_benchmark():
    """Run async benchmarks for concurrent JSON processing."""
    if not HAS_OPTIMIZED:
        print('⚠️  Async benchmarks require optimized JSON extensions')
        return

    print('\n🔄 Async Concurrent JSON Benchmark')
    print('=' * 60)

    # Generate test data
    datasets = [generate_large_dict(500) for _ in range(20)]

    # Benchmark concurrent standard JSON
    start_time = time.perf_counter()
    tasks = []
    for data in datasets:
        task = asyncio.create_task(
            asyncio.to_thread(lambda d: StandardJSONResponse(d).render(d), data)
        )
        tasks.append(task)

    await asyncio.gather(*tasks)
    std_time = time.perf_counter() - start_time

    # Benchmark concurrent optimized JSON
    start_time = time.perf_counter()
    tasks = []
    for data in datasets:
        task = asyncio.create_task(
            asyncio.to_thread(lambda d: OptimizedJSONResponse(d).render(d), data)
        )
        tasks.append(task)

    await asyncio.gather(*tasks)
    opt_time = time.perf_counter() - start_time

    print(f'⏱️  Standard JSON (20 concurrent):  {std_time:.3f}s')
    print(f'⚡ Optimized JSON (20 concurrent): {opt_time:.3f}s')
    print(f'🏆 Concurrent speedup: {std_time / opt_time:.2f}x')


if __name__ == '__main__':
    # Run synchronous benchmarks
    run_benchmarks()

    # Run async benchmarks
    if HAS_OPTIMIZED:
        print('\n' + '=' * 60)
        asyncio.run(async_benchmark())
