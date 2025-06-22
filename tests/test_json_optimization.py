#!/usr/bin/env python3
"""Test script for the new JSON serialization optimization."""

from __future__ import annotations

import asyncio
import time

import pytest

# Test data
SIMPLE_DATA = {'message': 'hello', 'count': 42, 'active': True}
COMPLEX_DATA = {
    'users': [
        {'id': i, 'name': f'User {i}', 'scores': [j * 2 for j in range(10)]}
        for i in range(100)
    ],
    'metadata': {
        'created_at': time.time(),
        'version': '1.0.0',
        'config': {'debug': True, 'timeout': 30},
    },
}
LARGE_ARRAY = [{'item': i, 'data': [j for j in range(50)]} for i in range(500)]


def test_rust_compilation():
    """Test that Rust extensions are properly compiled and available."""
    try:
        from velithon._velithon import ParallelJSONSerializer

        serializer = ParallelJSONSerializer()
        assert serializer is not None
        print('✅ Rust JSON serializer available')
        return True
    except ImportError:
        print('❌ Rust JSON serializer not available')
        return False


def test_basic_serialization():
    """Test basic JSON serialization functionality."""
    try:
        from velithon._velithon import ParallelJSONSerializer

        serializer = ParallelJSONSerializer()

        # Test simple data
        result = serializer.serialize(SIMPLE_DATA)
        assert isinstance(result, (bytes, list))
        print('✅ Basic serialization works')

        # Test complex data
        result = serializer.serialize(COMPLEX_DATA)
        assert isinstance(result, (bytes, list))
        print('✅ Complex data serialization works')

        return True
    except Exception as e:
        print(f'❌ Basic serialization failed: {e}')
        return False


def test_parallel_serialization():
    """Test parallel serialization with large data."""
    try:
        from velithon._velithon import ParallelJSONSerializer

        serializer = ParallelJSONSerializer(parallel_threshold=50)

        # Test with large array (should trigger parallel processing)
        start_time = time.perf_counter()
        result = serializer.serialize(LARGE_ARRAY, use_parallel=True)
        parallel_time = time.perf_counter() - start_time

        # Test with sequential processing
        start_time = time.perf_counter()
        result = serializer.serialize(LARGE_ARRAY, use_parallel=False)
        sequential_time = time.perf_counter() - start_time

        print('✅ Parallel serialization works')
        print(f'   Sequential: {sequential_time * 1000:.3f}ms')
        print(f'   Parallel:   {parallel_time * 1000:.3f}ms')

        if parallel_time < sequential_time:
            speedup = sequential_time / parallel_time
            print(f'   🏆 Speedup: {speedup:.2f}x')

        return True
    except Exception as e:
        print(f'❌ Parallel serialization failed: {e}')
        return False


def test_optimized_response():
    """Test the OptimizedJSONResponse class."""
    try:
        from velithon.json_responses import OptimizedJSONResponse

        # Test simple response
        response = OptimizedJSONResponse(SIMPLE_DATA)
        rendered = response.render(SIMPLE_DATA)
        assert isinstance(rendered, bytes)
        print('✅ OptimizedJSONResponse works')

        # Test performance stats
        stats = response.get_performance_stats()
        assert isinstance(stats, dict)
        assert 'render_time_ms' in stats
        print('✅ Performance stats available')

        return True
    except Exception as e:
        print(f'❌ OptimizedJSONResponse failed: {e}')
        return False


def test_batch_response():
    """Test the BatchJSONResponse class."""
    try:
        from velithon.json_responses import BatchJSONResponse

        # Test batch response
        objects = [{'id': i, 'value': i * 2} for i in range(100)]
        response = BatchJSONResponse(objects)
        rendered = response.render(objects)
        assert isinstance(rendered, bytes)
        print('✅ BatchJSONResponse works')

        # Test performance stats
        stats = response.get_performance_stats()
        assert isinstance(stats, dict)
        assert 'object_count' in stats
        print('✅ Batch performance stats available')

        return True
    except Exception as e:
        print(f'❌ BatchJSONResponse failed: {e}')
        return False


def test_error_handling():
    """Test error handling and fallback mechanisms."""
    try:
        from velithon.json_responses import OptimizedJSONResponse

        # Test with potentially problematic data
        class CustomObject:
            def __str__(self):
                return 'custom_object'

        custom_data = {'custom': CustomObject(), 'normal': 'data'}
        response = OptimizedJSONResponse(custom_data)
        rendered = response.render(custom_data)
        assert isinstance(rendered, bytes)
        print('✅ Error handling and fallback works')

        return True
    except Exception as e:
        print(f'❌ Error handling failed: {e}')
        return False


def test_cache_functionality():
    """Test caching functionality."""
    try:
        from velithon._velithon import ParallelJSONSerializer

        serializer = ParallelJSONSerializer(cache_size_limit=100)

        # Serialize the same data multiple times
        data = {'test': 'cache', 'number': 123}

        # First serialization
        result1 = serializer.serialize(data)

        # Second serialization (should potentially use cache)
        result2 = serializer.serialize(data)

        # Results should be identical
        assert result1 == result2

        # Check cache stats
        stats = serializer.get_cache_stats()
        assert isinstance(stats, dict)
        print('✅ Cache functionality works')

        return True
    except Exception as e:
        print(f'❌ Cache functionality failed: {e}')
        return False


@pytest.mark.asyncio
async def test_async_performance():
    """Test async performance with concurrent requests."""
    try:
        from velithon.json_responses import OptimizedJSONResponse

        async def create_response(data):
            response = OptimizedJSONResponse(data)
            return response.render(data)

        # Create multiple concurrent responses
        tasks = []
        for i in range(20):
            data = {'request_id': i, 'data': [j for j in range(100)]}
            task = asyncio.create_task(create_response(data))
            tasks.append(task)

        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        assert len(results) == 20
        assert all(isinstance(result, bytes) for result in results)

        print('✅ Async performance test passed')
        print(f'   20 concurrent responses in {total_time * 1000:.3f}ms')
        print(f'   Avg per response: {(total_time / 20) * 1000:.3f}ms')

        return True
    except Exception as e:
        print(f'❌ Async performance test failed: {e}')
        return False


def run_all_tests():
    """Run all tests and report results."""
    print('🧪 JSON Serialization Optimization Test Suite')
    print('=' * 60)

    tests = [
        ('Rust Compilation', test_rust_compilation),
        ('Basic Serialization', test_basic_serialization),
        ('Parallel Serialization', test_parallel_serialization),
        ('Optimized Response', test_optimized_response),
        ('Batch Response', test_batch_response),
        ('Error Handling', test_error_handling),
        ('Cache Functionality', test_cache_functionality),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f'\n🔬 Running: {test_name}')
        try:
            if test_func():
                passed += 1
            else:
                print(f'❌ {test_name} failed')
        except Exception as e:
            print(f'❌ {test_name} error: {e}')

    # Run async test
    print('\n🔬 Running: Async Performance')
    try:
        result = asyncio.run(test_async_performance())
        if result:
            passed += 1
        total += 1
    except Exception as e:
        print(f'❌ Async Performance error: {e}')
        total += 1

    print(f'\n📊 Test Results: {passed}/{total} passed')

    if passed == total:
        print('🎉 All tests passed! JSON optimization is working correctly.')
    else:
        print('⚠️  Some tests failed. Please check the implementation.')

        if passed == 0:
            print('\n🔧 Setup Instructions:')
            print('1. Install Rust: https://rustup.rs/')
            print('2. Install maturin: pip install maturin')
            print('3. Build extensions: maturin develop --release')
            print('4. Re-run tests')

    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
