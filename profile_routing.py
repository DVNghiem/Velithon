#!/usr/bin/env python3
"""
Profile the routing system to identify bottlenecks.
"""
import time
import asyncio
from velithon.routing import Router
from velithon.requests import Request
from velithon.responses import JSONResponse
from velithon.datastructures import Scope, Protocol

# Test parameters
iterations = 10000

# Mock protocol to avoid implementation details
class MockProtocol(Protocol):
    async def send(self, data):
        pass

async def test_handler(request: Request):
    return JSONResponse({"message": "Hello World"})

async def profile_router():
    # Create test router with multiple paths
    router = Router()
    
    # Add routes
    for i in range(100):
        router.add_route(f"/test/path/{i}", test_handler)
    
    router.add_route("/api/users", test_handler)
    router.add_route("/api/users/{user_id:int}", test_handler)
    router.add_route("/api/users/{user_id:int}/posts", test_handler)
    router.add_route("/api/users/{user_id:int}/posts/{post_id:int}", test_handler)
    
    # Create test scopes
    direct_scope = Scope({"type": "http", "method": "GET", "path": "/test/path/50"})
    param_scope = Scope({"type": "http", "method": "GET", "path": "/api/users/123/posts/456"})
    not_found_scope = Scope({"type": "http", "method": "GET", "path": "/unknown/path"})
    
    # Mock protocol for testing
    protocol = MockProtocol()
    
    # Test direct path routing
    direct_times = []
    print("Testing direct path routing performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations // 10):  # Reduce iterations as this is a full request
            await router(direct_scope, protocol)
        end = time.perf_counter()
        direct_times.append(end - start)
    
    # Test parameterized path routing
    param_times = []
    print("Testing parameterized path routing performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations // 10):  # Reduce iterations as this is a full request
            await router(param_scope, protocol)
        end = time.perf_counter()
        param_times.append(end - start)
    
    # Test 404 path routing
    not_found_times = []
    print("Testing 404 path routing performance...")
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(iterations // 10):  # Reduce iterations as this is a full request
            await router(not_found_scope, protocol)
        end = time.perf_counter()
        not_found_times.append(end - start)
    
    # Calculate average times
    avg_direct_time = sum(direct_times) / len(direct_times)
    avg_param_time = sum(param_times) / len(param_times)
    avg_not_found_time = sum(not_found_times) / len(not_found_times)
    
    scaled_iterations = iterations // 10
    
    print(f"\nResults for {scaled_iterations} iterations:")
    print(f"Direct path routing time: {avg_direct_time*1000:.2f}ms ({avg_direct_time*1000000/scaled_iterations:.2f}μs per lookup)")
    print(f"Parameterized path routing time: {avg_param_time*1000:.2f}ms ({avg_param_time*1000000/scaled_iterations:.2f}μs per lookup)")
    print(f"404 path routing time: {avg_not_found_time*1000:.2f}ms ({avg_not_found_time*1000000/scaled_iterations:.2f}μs per lookup)")
    
    # Calculate throughput
    print(f"\nEstimated throughput (local, no network):")
    print(f"Direct path: {scaled_iterations/avg_direct_time:.0f} req/s")
    print(f"Parameterized path: {scaled_iterations/avg_param_time:.0f} req/s")

if __name__ == "__main__":
    asyncio.run(profile_router())
