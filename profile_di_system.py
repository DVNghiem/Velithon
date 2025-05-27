#!/usr/bin/env python3
"""
Profile the dependency injection system to identify bottlenecks.
"""
import time
import asyncio
from velithon.di import ServiceContainer, Provide, Provider, SingletonProvider, cached_signature

# Test class for DI testing
class TestService:
    def __init__(self, value="default"):
        self.value = value
        
    def get_value(self):
        return self.value

# Create test container
container = ServiceContainer()
container.register(TestService, SingletonProvider(TestService))

# Test parameters
iterations = 10000

async def test_di_performance():
    # Test cached_signature performance
    sig_times = []
    print("Testing signature caching performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            sig = cached_signature(TestService)
        end = time.perf_counter()
        sig_times.append(end - start)
    
    # Test service resolution performance
    resolution_times = []
    print("Testing service resolution performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations):
            service = await container.resolve(TestService)
        end = time.perf_counter()
        resolution_times.append(end - start)
    
    # Calculate average times
    avg_sig_time = sum(sig_times) / len(sig_times)
    avg_resolution_time = sum(resolution_times) / len(resolution_times)
    
    print(f"\nResults for {iterations} iterations:")
    print(f"Signature caching time: {avg_sig_time*1000:.2f}ms")
    print(f"Service resolution time: {avg_resolution_time*1000:.2f}ms")
    print(f"Time per resolution: {avg_resolution_time*1000000/iterations:.2f}μs")

if __name__ == "__main__":
    asyncio.run(test_di_performance())
