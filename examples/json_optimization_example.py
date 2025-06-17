#!/usr/bin/env python3
"""
Example demonstrating Velithon's high-performance JSON optimization feature.

This example shows how to use the OptimizedJSONResponse and BatchJSONResponse
classes for efficient JSON serialization with parallel processing.
"""

import time
import json
from velithon.json_responses import OptimizedJSONResponse, BatchJSONResponse


def generate_large_dataset(size: int) -> list[dict]:
    """Generate a large dataset for testing."""
    return [
        {
            'id': i,
            'name': f'user_{i}',
            'email': f'user_{i}@example.com',
            'profile': {
                'age': 20 + (i % 60),
                'country': ['US', 'UK', 'CA', 'DE', 'FR'][i % 5],
                'preferences': [f'pref_{j}' for j in range(i % 10)],
            },
            'orders': [
                {'order_id': f'order_{i}_{j}', 'amount': (i + j) * 10.5}
                for j in range(i % 5)
            ],
        }
        for i in range(size)
    ]


def compare_performance():
    """Compare standard JSON vs optimized JSON performance."""
    print('🚀 JSON Optimization Performance Comparison')
    print('=' * 60)

    # Test with different data sizes
    for size in [100, 1000, 5000]:
        print(f'\n📊 Testing with {size} records...')

        data = generate_large_dataset(size)

        # Standard JSON
        start = time.perf_counter()
        standard_result = json.dumps(data)
        standard_time = time.perf_counter() - start

        # Optimized JSON (with low threshold to force parallel)
        start = time.perf_counter()
        response = OptimizedJSONResponse(data, parallel_threshold=100)
        optimized_result = response.render(data)
        optimized_time = time.perf_counter() - start

        # Batch JSON
        start = time.perf_counter()
        batch_response = BatchJSONResponse(data, parallel_threshold=100)
        batch_result = batch_response.render(data)
        batch_time = time.perf_counter() - start

        print(
            f'   Standard JSON:  {standard_time:.4f}s ({len(standard_result):,} chars)'
        )
        print(
            f'   Optimized JSON: {optimized_time:.4f}s ({len(optimized_result):,} bytes)'
        )
        print(f'   Batch JSON:     {batch_time:.4f}s ({len(batch_result):,} bytes)')

        # Show performance stats
        print(f'   Optimized stats: {response.get_performance_stats()}')

        if optimized_time > 0:
            speedup = standard_time / optimized_time
            print(f'   Speedup: {speedup:.2f}x')


def demonstrate_features():
    """Demonstrate key features of the JSON optimization."""
    print('\n🔧 Feature Demonstration')
    print('=' * 60)

    # 1. Basic optimization
    print('\n1️⃣ Basic Optimization:')
    data = {'message': 'Hello, World!', 'numbers': list(range(100))}
    response = OptimizedJSONResponse(data)
    result = response.render(data)
    print(f'   Serialized {len(data["numbers"])} numbers')
    print(f'   Result size: {len(result)} bytes')

    # 2. Batch processing
    print('\n2️⃣ Batch Processing:')
    batch_data = [{'id': i, 'value': f'item_{i}'} for i in range(50)]
    batch_response = BatchJSONResponse(batch_data)
    batch_result = batch_response.render(batch_data)
    print(f'   Serialized {len(batch_data)} objects')
    print(f'   Result size: {len(batch_result)} bytes')

    # 3. Parallel threshold control
    print('\n3️⃣ Parallel Threshold Control:')
    large_dict = {f'key_{i}': f'value_{i}' for i in range(1000)}

    # High threshold (no parallel)
    response_sequential = OptimizedJSONResponse(large_dict, parallel_threshold=10000)
    start = time.perf_counter()
    result_sequential = response_sequential.render(large_dict)
    time_sequential = time.perf_counter() - start

    # Low threshold (force parallel)
    response_parallel = OptimizedJSONResponse(large_dict, parallel_threshold=100)
    start = time.perf_counter()
    result_parallel = response_parallel.render(large_dict)
    time_parallel = time.perf_counter() - start

    print(f'   Sequential (threshold=10000): {time_sequential:.4f}s')
    print(f'   Parallel (threshold=100):     {time_parallel:.4f}s')

    # 4. Performance monitoring
    print('\n4️⃣ Performance Monitoring:')
    stats = response_parallel.get_performance_stats()
    print('   Performance stats:')
    for key, value in stats.items():
        print(f'     {key}: {value}')


def main():
    """Main example execution."""
    print('🎯 Velithon JSON Optimization Example')
    print('=' * 60)

    demonstrate_features()
    compare_performance()

    print('\n✅ Example completed successfully!')
    print('\nKey takeaways:')
    print('• OptimizedJSONResponse provides automatic parallel processing')
    print('• BatchJSONResponse is optimized for arrays of objects')
    print('• Parallel thresholds can be tuned for optimal performance')
    print('• Performance stats help with monitoring and optimization')


if __name__ == '__main__':
    main()
