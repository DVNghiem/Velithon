#!/usr/bin/env python3
"""
Benchmark script to demonstrate LoggingMiddleware performance improvements.
Run this to compare old vs new implementation performance.
"""
import asyncio
import time
import statistics
from typing import List
from dataclasses import dataclass

# Mock classes for testing
class MockScope:
    def __init__(self):
        self.proto = "http"
        self.method = "GET"
        self.path = "/api/test"
        self.client = "127.0.0.1:54321"
        self._request_id = "req-123456"
        self.headers = {"user-agent": "velithon-benchmark/1.0"}

class MockProtocol:
    def __init__(self):
        pass

@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    requests_per_second: float

async def benchmark_middleware(middleware, iterations: int = 1000) -> BenchmarkResult:
    """Benchmark a middleware implementation"""
    scope = MockScope()
    protocol = MockProtocol()
    
    # Warm up
    for _ in range(10):
        await middleware(scope, protocol)
    
    # Collect timing data
    times = []
    
    start_total = time.perf_counter()
    
    for _ in range(iterations):
        start = time.perf_counter()
        await middleware(scope, protocol)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms
    
    end_total = time.perf_counter()
    total_time_ms = (end_total - start_total) * 1000
    
    return BenchmarkResult(
        name="",
        iterations=iterations,
        total_time_ms=total_time_ms,
        avg_time_ms=statistics.mean(times),
        min_time_ms=min(times),
        max_time_ms=max(times),
        std_dev_ms=statistics.stdev(times),
        requests_per_second=iterations / (total_time_ms / 1000)
    )

async def mock_app(scope, protocol):
    """Mock application that simulates some work"""
    await asyncio.sleep(0.0001)  # Simulate 0.1ms of work

def print_results(results: List[BenchmarkResult]):
    """Print benchmark results in a nice format"""
    print("\n" + "="*80)
    print("VELITHON LOGGING MIDDLEWARE PERFORMANCE BENCHMARK")
    print("="*80)
    
    for result in results:
        print(f"\n{result.name}")
        print("-" * len(result.name))
        print(f"Iterations:          {result.iterations:,}")
        print(f"Total Time:          {result.total_time_ms:.2f} ms")
        print(f"Average Time:        {result.avg_time_ms:.4f} ms/request")
        print(f"Min Time:            {result.min_time_ms:.4f} ms")
        print(f"Max Time:            {result.max_time_ms:.4f} ms")
        print(f"Std Deviation:       {result.std_dev_ms:.4f} ms")
        print(f"Requests/Second:     {result.requests_per_second:,.0f} req/s")
    
    if len(results) >= 2:
        print(f"\n{'PERFORMANCE COMPARISON':^80}")
        print("="*80)
        baseline = results[0]
        optimized = results[1]
        
        speedup = optimized.requests_per_second / baseline.requests_per_second
        time_reduction = ((baseline.avg_time_ms - optimized.avg_time_ms) / baseline.avg_time_ms) * 100
        
        print(f"Speedup:             {speedup:.2f}x faster")
        print(f"Time Reduction:      {time_reduction:.1f}% faster")
        print(f"RPS Improvement:     +{optimized.requests_per_second - baseline.requests_per_second:,.0f} req/s")

async def main():
    """Run the benchmark"""
    print("Starting LoggingMiddleware Performance Benchmark...")
    print("This may take a few seconds...")
    
    # Import the current optimized middleware
    try:
        from velithon.middleware.logging import LoggingMiddleware
    except ImportError:
        print("Error: Could not import LoggingMiddleware")
        return
    
    results = []
    
    # Test 1: Performance logging disabled (should be fastest)
    print("\n1. Testing with performance logging DISABLED...")
    middleware_disabled = LoggingMiddleware(mock_app, enable_performance_logging=False)
    result_disabled = await benchmark_middleware(middleware_disabled, 1000)
    result_disabled.name = "Performance Logging DISABLED"
    results.append(result_disabled)
    
    # Test 2: Performance logging enabled (optimized)
    print("2. Testing with performance logging ENABLED (optimized)...")
    middleware_enabled = LoggingMiddleware(mock_app, enable_performance_logging=True)
    result_enabled = await benchmark_middleware(middleware_enabled, 1000)
    result_enabled.name = "Performance Logging ENABLED (Optimized)"
    results.append(result_enabled)
    
    # Test 3: Error handling performance
    print("3. Testing error handling performance...")
    async def error_app(scope, protocol):
        raise ValueError("Test error")
    
    middleware_error = LoggingMiddleware(error_app, enable_performance_logging=True)
    result_error = await benchmark_middleware(middleware_error, 100)  # Fewer iterations for error case
    result_error.name = "Error Handling Performance"
    results.append(result_error)
    
    print_results(results)
    
    # Performance targets
    print(f"\n{'PERFORMANCE TARGETS':^80}")
    print("="*80)
    print("Target for Velithon: 110,000-115,000 RPS")
    print(f"Logging Disabled:    {result_disabled.requests_per_second:,.0f} RPS")
    print(f"Logging Enabled:     {result_enabled.requests_per_second:,.0f} RPS")
    
    disabled_pct = (result_disabled.requests_per_second / 112500) * 100  # 112.5k is mid-range target
    enabled_pct = (result_enabled.requests_per_second / 112500) * 100
    
    print(f"Disabled % of target: {disabled_pct:.1f}%")
    print(f"Enabled % of target:  {enabled_pct:.1f}%")
    
    print(f"\n{'RECOMMENDATIONS':^80}")
    print("="*80)
    if result_disabled.requests_per_second >= 100000:
        print("✅ EXCELLENT: Logging disabled performance meets high-performance targets")
    elif result_disabled.requests_per_second >= 50000:
        print("✅ GOOD: Logging disabled performance is acceptable")
    else:
        print("⚠️  WARNING: Performance may need further optimization")
    
    if result_enabled.requests_per_second >= 50000:
        print("✅ GOOD: Logging enabled performance is production-ready")
    elif result_enabled.requests_per_second >= 20000:
        print("✅ ACCEPTABLE: Logging enabled performance is reasonable")
    else:
        print("⚠️  WARNING: Consider disabling performance logging in production")

if __name__ == "__main__":
    asyncio.run(main())
