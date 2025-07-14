"""Enhanced VSP (Velithon Service Protocol) Example.

Uses QUIC, Protocol Buffers, and Zstd compression.

This example demonstrates:
1. QUIC-based transport with automatic TCP fallback
2. Protocol Buffer message serialization with compression
3. Smart service discovery and load balancing
4. Request-response patterns with caching and retry mechanisms
5. Circuit breaker pattern for fault tolerance
6. Background health monitoring
"""

import asyncio
import json
import time

import velithon_quic as vq  # The compiled Rust extension

async def setup_service_registry():
    """Set up service registry with health monitoring."""
    print("🔧 Setting up service registry...")
    
    # Create service registry with caching
    registry = vq.ServiceRegistry(
        cache_ttl_seconds=300,  # 5 minutes cache
        health_check_interval_seconds=30  # Health check every 30 seconds
    )
    
    # Register some example services
    services = [
        vq.ServiceInfo("user-service", "localhost", 8001, weight=1.0),
        vq.ServiceInfo("user-service", "localhost", 8002, weight=1.5),
        vq.ServiceInfo("order-service", "localhost", 8003, weight=1.0),
        vq.ServiceInfo("payment-service", "localhost", 8004, weight=2.0),
    ]
    
    for service in services:
        await registry.register_service(service)
        print(f"   ✅ Registered {service.name} at {service.endpoint()}")
    
    # Start background health monitoring
    print("🔍 Starting health monitoring...")
    await registry.start_health_monitoring()
    
    return registry

async def setup_smart_load_balancer():
    """Set up smart load balancer with different algorithms."""
    print("⚖️ Setting up smart load balancer...")
    
    # Create load balancer with weighted round-robin algorithm
    balancer = vq.SmartLoadBalancer("weighted_round_robin")
    
    return balancer

async def setup_vsp_client():
    """Set up VSP client with advanced features."""
    print("🚀 Setting up VSP client...")
    
    # Create client with comprehensive configuration
    client = vq.VSPClient(
        timeout_ms=30000,                    # 30 second timeout
        max_retries=3,                       # 3 retry attempts
        cache_ttl_seconds=300,               # 5 minute response cache
        circuit_breaker_threshold=5,         # Open circuit after 5 failures
        enable_compression=True,             # Enable Zstd compression
        enable_adaptive_transport=True       # Auto switch between TCP/QUIC
    )
    
    return client

async def demonstrate_request_response_pattern(client):
    """Demonstrate request-response pattern with caching and retries."""
    print("\n📨 Demonstrating request-response pattern...")
    
    try:
        # Example 1: User service request with caching
        user_data = json.dumps({"user_id": 12345, "action": "get_profile"}).encode()
        
        print("   📤 Sending user profile request...")
        start_time = time.time()
        
        response = await client.send_request(
            service_name="user-service",
            method="get_profile",
            data=user_data,
            headers={"Content-Type": "application/json", "X-Request-ID": "req-001"},
            timeout_ms=5000,
            cache_key="user:12345:profile",  # Custom cache key
            enable_cache=True
        )
        
        elapsed_time = time.time() - start_time
        
        if response.is_success():
            print(f"   ✅ Response received in {elapsed_time:.3f}s")
            print(f"   📊 Status: {response.status_code}")
            print(f"   ⚡ Processing time: {response.processing_time_us}μs")
            print(f"   📦 Response size: {len(response.data)} bytes")
        else:
            print(f"   ❌ Request failed: {response.error_message}")
            
        # Example 2: Same request (should hit cache)
        print("   📤 Sending same request (should hit cache)...")
        start_time = time.time()
        
        cached_response = await client.send_request(
            service_name="user-service",
            method="get_profile",
            data=user_data,
            cache_key="user:12345:profile",
            enable_cache=True
        )
        
        elapsed_time = time.time() - start_time
        print(f"   ⚡ Cached response in {elapsed_time:.3f}s (much faster!)")
        
    except Exception as e:
        print(f"   ❌ Request failed: {e}")

async def demonstrate_fire_and_forget(client):
    """Demonstrate fire-and-forget messaging."""
    print("\n🔥 Demonstrating fire-and-forget messaging...")
    
    try:
        # Send analytics event without waiting for response
        event_data = json.dumps({
            "event_type": "user_action",
            "user_id": 12345,
            "action": "page_view",
            "timestamp": time.time(),
            "metadata": {"page": "/dashboard", "session_id": "sess-001"}
        }).encode()
        
        print("   📤 Sending analytics event (fire-and-forget)...")
        
        await client.send_async(
            service_name="analytics-service",
            method="track_event",
            data=event_data,
            headers={"Content-Type": "application/json"}
        )
        
        print("   ✅ Event sent successfully (no response expected)")
        
    except Exception as e:
        print(f"   ❌ Failed to send event: {e}")

async def demonstrate_quic_transport():
    """Demonstrate direct QUIC transport usage."""
    print("\n🌐 Demonstrating QUIC transport...")
    
    try:
        # Create QUIC transport with compression
        quic_transport = vq.QuicTransport(is_server=False, compression_type="zstd")
        
        print("   🔗 Connecting to QUIC server...")
        await quic_transport.connect("localhost", 9000)
        
        if quic_transport.is_connected():
            print("   ✅ Connected to QUIC server")
            
            # Get connection statistics
            stats = quic_transport.get_stats()
            print(f"   📊 Connection stats:")
            print(f"      RTT: {stats.get('rtt_ms', 0):.2f}ms")
            print(f"      Congestion window: {stats.get('cwnd', 0)}")
            print(f"      Sent packets: {stats.get('sent_packets', 0)}")
            print(f"      Lost packets: {stats.get('lost_packets', 0)}")
            
            # Send a request
            test_data = b"Hello QUIC world!"
            print(f"   📤 Sending test data: {test_data}")
            
            response = await quic_transport.send_request(
                service_name="test-service",
                method="echo",
                data=test_data,
                timeout_ms=5000
            )
            
            print(f"   📨 Received response: {response.data}")
            
        quic_transport.close()
        print("   🔌 Connection closed")
        
    except Exception as e:
        print(f"   ❌ QUIC demonstration failed: {e}")

async def demonstrate_adaptive_transport():
    """Demonstrate adaptive transport (auto TCP/QUIC switching)."""
    print("\n🔄 Demonstrating adaptive transport...")
    
    try:
        # Create adaptive transport
        adaptive_transport = vq.AdaptiveTransport()
        
        print("   🔗 Connecting with adaptive transport...")
        await adaptive_transport.connect("localhost", 8080)
        
        # Check which transport was selected
        current_transport = adaptive_transport.adapt_transport()
        print(f"   📡 Selected transport: {current_transport}")
        
        # Simulate network condition changes and adaptation
        print("   🔄 Simulating network condition changes...")
        for i in range(3):
            await asyncio.sleep(1)
            transport_type = adaptive_transport.adapt_transport()
            print(f"      Adaptation {i+1}: {transport_type}")
        
    except Exception as e:
        print(f"   ❌ Adaptive transport demonstration failed: {e}")

async def demonstrate_service_discovery(registry):
    """Demonstrate service discovery with caching."""
    print("\n🔍 Demonstrating service discovery...")
    
    try:
        # Discover user services
        print("   🔎 Discovering user services...")
        user_services = await registry.discover_services(
            service_name="user-service",
            tags=None,
            max_results=5
        )
        
        print(f"   ✅ Found {len(user_services)} user service instances:")
        for service in user_services:
            print(f"      - {service.name} at {service.endpoint()} (weight: {service.weight})")
        
        # Discover with retry mechanism
        print("   🔄 Getting service with retry mechanism...")
        service = await registry.get_service_with_retry(
            service_name="payment-service",
            max_retries=3
        )
        
        print(f"   ✅ Selected service: {service.name} at {service.endpoint()}")
        
        # Show cache statistics
        cache_stats = await registry.get_cache_stats()
        print(f"   📊 Cache statistics:")
        print(f"      Total entries: {cache_stats.get('total_entries', 0)}")
        print(f"      Total hits: {cache_stats.get('total_hits', 0)}")
        print(f"      Expired entries: {cache_stats.get('expired_entries', 0)}")
        
    except Exception as e:
        print(f"   ❌ Service discovery failed: {e}")

async def demonstrate_circuit_breaker(client):
    """Demonstrate circuit breaker pattern."""
    print("\n⚡ Demonstrating circuit breaker pattern...")
    
    try:
        # Get circuit breaker status
        cb_status = await client.get_circuit_breaker_status()
        print(f"   📊 Circuit breaker status: {cb_status}")
        
        # Simulate service failures to trigger circuit breaker
        print("   💥 Simulating service failures...")
        for i in range(3):
            try:
                await client.send_request(
                    service_name="failing-service",
                    method="test",
                    data=b"test",
                    timeout_ms=1000  # Short timeout to force failure
                )
            except Exception as e:
                print(f"      Attempt {i+1} failed: {type(e).__name__}")
        
        # Check circuit breaker status after failures
        cb_status_after = await client.get_circuit_breaker_status()
        print(f"   📊 Circuit breaker status after failures: {cb_status_after}")
        
    except Exception as e:
        print(f"   ❌ Circuit breaker demonstration failed: {e}")

async def show_performance_metrics(client):
    """Show performance metrics and statistics."""
    print("\n📊 Performance Metrics:")
    
    try:
        # Cache statistics
        cache_stats = await client.get_cache_stats()
        print(f"   Response Cache:")
        print(f"      Entries: {cache_stats.get('total_entries', 0)}")
        print(f"      Hits: {cache_stats.get('total_hits', 0)}")
        print(f"      Expired: {cache_stats.get('expired_entries', 0)}")
        
        # Circuit breaker status
        cb_status = await client.get_circuit_breaker_status()
        print(f"   Circuit Breakers: {len(cb_status)} services monitored")
        for service, status in cb_status.items():
            print(f"      {service}: {status.get('state', 'Unknown')}")
        
    except Exception as e:
        print(f"   ❌ Failed to get metrics: {e}")

async def main():
    """Main demonstration function."""
    print("🎯 Enhanced VSP Protocol Demonstration")
    print("=====================================")
    
    try:
        # Setup components
        registry = await setup_service_registry()
        balancer = await setup_smart_load_balancer()
        client = await setup_vsp_client()
        
        # Run demonstrations
        await demonstrate_service_discovery(registry)
        await demonstrate_request_response_pattern(client)
        await demonstrate_fire_and_forget(client)
        await demonstrate_quic_transport()
        await demonstrate_adaptive_transport()
        await demonstrate_circuit_breaker(client)
        
        # Show performance metrics
        await show_performance_metrics(client)
        
        print("\n✅ All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
