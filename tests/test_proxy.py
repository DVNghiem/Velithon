#!/usr/bin/env python3
"""
Test script for the Velithon proxy functionality.
"""
import asyncio
from velithon.middleware.proxy import ProxyClient, ProxyLoadBalancer

async def test_proxy_client():
    """Test basic proxy client functionality."""
    print("Testing ProxyClient...")
    
    # Create a proxy client
    proxy = ProxyClient("https://httpbin.org", timeout_ms=10000)
    
    # Test circuit breaker status
    status = await proxy.get_circuit_breaker_status()
    print(f"Circuit breaker status: {status}")
    
    # Test HTTP request
    try:
        result = await proxy.forward_request("GET", "/get", query_params={"test": "value"})
        status_code, headers, body = result
        print(f"Request successful: Status {status_code}")
        print(f"Response headers count: {len(headers)}")
        print(f"Response body length: {len(body)} bytes")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("ProxyClient test completed.\n")

async def test_load_balancer():
    """Test load balancer functionality."""
    print("Testing ProxyLoadBalancer...")
    
    # Create a load balancer with multiple targets
    targets = [
        "https://httpbin.org",
        "https://api.github.com",
        "https://jsonplaceholder.typicode.com"
    ]
    
    lb = ProxyLoadBalancer(targets, strategy="round_robin")
    
    # Test getting next targets
    for i in range(5):
        target = await lb.get_next_target()
        print(f"Round {i+1}: {target}")
    
    # Test health status
    health_status = await lb.get_health_status()
    print(f"Health status: {health_status}")
    
    print("ProxyLoadBalancer test completed.\n")

async def test_random_strategy():
    """Test random load balancing strategy."""
    print("Testing random load balancing...")
    
    targets = ["server1", "server2", "server3"]
    lb = ProxyLoadBalancer(targets, strategy="random")
    
    selected_targets = []
    for i in range(10):
        target = await lb.get_next_target()
        selected_targets.append(target)
    
    print(f"Random selections: {selected_targets}")
    print("Random strategy test completed.\n")

async def main():
    """Run all tests."""
    print("=== Velithon Proxy Feature Test ===\n")
    
    await test_proxy_client()
    await test_load_balancer() 
    await test_random_strategy()
    
    print("=== All tests completed ===")

if __name__ == "__main__":
    asyncio.run(main())
