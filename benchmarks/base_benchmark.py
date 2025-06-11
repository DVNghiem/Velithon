"""
Base benchmark utilities for Velithon performance testing.

This module provides common benchmarking patterns and utilities to eliminate
duplication across benchmark implementations.
"""

import asyncio
import statistics
import time
import tracemalloc
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List


class TimingResult:
    """Structured result for timing operations."""
    
    def __init__(self, times: List[float], result: Any = None):
        self.times = times
        self.result = result
        self._stats = None
    
    @property
    def stats(self) -> Dict[str, float]:
        """Calculate statistics on demand."""
        if self._stats is None:
            sorted_times = sorted(self.times)
            self._stats = {
                'mean': statistics.mean(self.times),
                'median': statistics.median(self.times),
                'min': min(self.times),
                'max': max(self.times),
                'std_dev': statistics.stdev(self.times) if len(self.times) > 1 else 0.0,
                'p95': sorted_times[int(len(sorted_times) * 0.95)],
                'p99': sorted_times[int(len(sorted_times) * 0.99)],
                'count': len(self.times)
            }
        return self._stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'times': self.times,
            'result': self.result,
            **self.stats
        }


class BenchmarkTimer:
    """Unified timer for benchmarking operations."""
    
    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
    
    def time_function(self, func: Callable, *args, **kwargs) -> TimingResult:
        """Time a synchronous function execution."""
        times = []
        result = None
        
        for _ in range(self.iterations):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        return TimingResult(times, result)
    
    async def time_async_function(self, coro_func: Callable, *args, **kwargs) -> TimingResult:
        """Time an async function execution."""
        times = []
        result = None
        
        for _ in range(self.iterations):
            start = time.perf_counter()
            result = await coro_func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)
        
        return TimingResult(times, result)
    
    async def time_concurrent_execution(
        self, 
        coro_func: Callable, 
        concurrency: int = 100,
        *args, **kwargs
    ) -> TimingResult:
        """Time concurrent execution of async functions."""
        tasks = [coro_func(*args, **kwargs) for _ in range(concurrency)]
        
        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        end = time.perf_counter()
        
        total_time = end - start
        return TimingResult([total_time], {
            'total_time': total_time,
            'tasks_count': concurrency,
            'throughput': concurrency / total_time,
            'avg_task_time': total_time / concurrency,
            'results': results
        })


class MemoryProfiler:
    """Memory usage profiling utility."""
    
    def __init__(self):
        self.is_profiling = False
    
    def start_profiling(self):
        """Start memory profiling."""
        tracemalloc.start()
        self.is_profiling = True
    
    def stop_profiling(self) -> Dict[str, float]:
        """Stop profiling and return memory statistics."""
        if not self.is_profiling:
            raise RuntimeError("Profiling not started")
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.is_profiling = False
        
        return {
            'current_bytes': current,
            'peak_bytes': peak,
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024
        }
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Profile memory usage of a function."""
        self.start_profiling()
        try:
            result = func(*args, **kwargs)
            memory_stats = self.stop_profiling()
            return {
                'result': result,
                'memory': memory_stats
            }
        except Exception:
            if self.is_profiling:
                tracemalloc.stop()
                self.is_profiling = False
            raise


class BaseBenchmark(ABC):
    """Abstract base class for benchmark implementations."""
    
    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        self.timer = BenchmarkTimer(iterations)
        self.memory_profiler = MemoryProfiler()
        self.results = {}
    
    def print_timing_results(self, name: str, timing_result: TimingResult, unit: str = "ms"):
        """Print formatted timing results."""
        stats = timing_result.stats
        multiplier = 1000 if unit == "ms" else 1000000 if unit == "μs" else 1
        
        print(f"  {name}:")
        print(f"    Mean: {stats['mean'] * multiplier:.3f}{unit}")
        print(f"    P95:  {stats['p95'] * multiplier:.3f}{unit}")
        print(f"    P99:  {stats['p99'] * multiplier:.3f}{unit}")
        print(f"    Std:  {stats['std_dev'] * multiplier:.3f}{unit}")
    
    def print_memory_results(self, name: str, memory_stats: Dict[str, float]):
        """Print formatted memory results."""
        print(f"  {name}:")
        print(f"    Current: {memory_stats['current_mb']:.3f} MB")
        print(f"    Peak:    {memory_stats['peak_mb']:.3f} MB")
    
    def print_throughput_results(self, name: str, throughput: float, unit: str = "ops/sec"):
        """Print formatted throughput results."""
        print(f"  {name}: {throughput:,.0f} {unit}")
    
    def calculate_speedup(self, baseline: float, optimized: float) -> float:
        """Calculate speedup ratio."""
        return baseline / optimized if optimized > 0 else 0.0
    
    def save_results(self, filename: str):
        """Save benchmark results to JSON file."""
        import json
        
        # Convert TimingResult objects to dictionaries
        serializable_results = {}
        for key, value in self.results.items():
            if isinstance(value, TimingResult):
                serializable_results[key] = value.to_dict()
            else:
                serializable_results[key] = value
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'iterations': self.iterations,
                'results': serializable_results
            }, f, indent=2, default=str)
    
    @abstractmethod
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run the benchmark suite. Must be implemented by subclasses."""
        pass


class ResponseBenchmarkMixin:
    """Mixin for common response benchmarking patterns."""
    
    def benchmark_json_response_creation(self, data: Dict[str, Any]) -> TimingResult:
        """Benchmark JSON response creation with standard data."""
        from velithon.responses import JSONResponse
        
        def create_json_response():
            return JSONResponse(data)
        
        return self.timer.time_function(create_json_response)
    
    def benchmark_text_response_creation(self, text: str = "Hello, World!") -> TimingResult:
        """Benchmark plain text response creation."""
        from velithon.responses import PlainTextResponse
        
        def create_text_response():
            return PlainTextResponse(text)
        
        return self.timer.time_function(create_text_response)
    
    async def benchmark_concurrent_response_creation(
        self, 
        data: Dict[str, Any],
        concurrency: int = 100
    ) -> TimingResult:
        """Benchmark concurrent response creation."""
        from velithon.responses import JSONResponse
        
        async def create_response():
            response = JSONResponse(data)
            return response.body
        
        return await self.timer.time_concurrent_execution(create_response, concurrency)


class CacheBenchmarkMixin:
    """Mixin for cache performance benchmarking."""
    
    def benchmark_lru_cache_performance(self, cache_size: int = 128) -> Dict[str, TimingResult]:
        """Benchmark LRU cache performance."""
        from functools import lru_cache
        
        @lru_cache(maxsize=cache_size)
        def cached_computation(n: int) -> int:
            return sum(i * i for i in range(n))
        
        def uncached_computation(n: int) -> int:
            return sum(i * i for i in range(n))
        
        # Warm up cache
        for i in range(10):
            cached_computation(i)
        
        cached_result = self.timer.time_function(lambda: cached_computation(100))
        uncached_result = self.timer.time_function(lambda: uncached_computation(100))
        
        return {
            'cached': cached_result,
            'uncached': uncached_result,
            'speedup': self.calculate_speedup(
                uncached_result.stats['mean'], 
                cached_result.stats['mean']
            )
        }


# Standard test data generators
def generate_test_user_data(count: int = 100) -> Dict[str, Any]:
    """Generate standard test user data."""
    return {
        "users": [
            {
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "active": True,
                "score": 95.5 + (i % 10),
                "tags": ["python", "web", "async"]
            }
            for i in range(count)
        ],
        "total": count,
        "page": 1,
        "timestamp": time.time()
    }


def generate_test_api_response(size: str = "medium") -> Dict[str, Any]:
    """Generate test API response data of different sizes."""
    sizes = {
        "small": 10,
        "medium": 100,
        "large": 1000,
        "xlarge": 10000
    }
    
    count = sizes.get(size, 100)
    return {
        "data": list(range(count)),
        "metadata": {
            "size": size,
            "count": count,
            "generated_at": time.time()
        },
        "status": "success"
    }