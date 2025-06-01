#!/usr/bin/env python3
"""
Multi-Transport VSP Example

This example demonstrates how to use different transport types with VSP:
- TCP (default)
- UDP
- WebSocket
- HTTP/2
- gRPC
- Message Queue (RabbitMQ)

Each transport type has different characteristics and use cases.
"""

import asyncio
import logging
from velithon.vsp import VSPManager, ServiceMesh, ServiceInfo, TransportType

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Example services using different transports
async def run_tcp_service():
    """TCP Transport - Default, reliable, connection-oriented"""
    print("Starting TCP Service on localhost:8001...")
    
    manager = VSPManager(
        name="tcp-service",
        transport_type=TransportType.TCP
    )
    
    @manager.vsp_service("echo")
    async def echo(message: str) -> dict:
        return {"echo": message, "transport": "TCP"}
    
    @manager.vsp_service("health")
    async def health() -> dict:
        return {"status": "healthy", "transport": "TCP"}
    
    await manager.start_server("localhost", 8001)


async def run_udp_service():
    """UDP Transport - Fast, connectionless, suitable for high-throughput"""
    print("Starting UDP Service on localhost:8002...")
    
    manager = VSPManager(
        name="udp-service",
        transport_type=TransportType.UDP
    )
    
    @manager.vsp_service("fast_echo")
    async def fast_echo(message: str) -> dict:
        return {"echo": message, "transport": "UDP", "fast": True}
    
    @manager.vsp_service("health")
    async def health() -> dict:
        return {"status": "healthy", "transport": "UDP"}
    
    await manager.start_server("localhost", 8002)


async def run_websocket_service():
    """WebSocket Transport - Real-time, web-compatible, bidirectional"""
    try:
        print("Starting WebSocket Service on localhost:8003...")
        
        manager = VSPManager(
            name="websocket-service",
            transport_type=TransportType.WEBSOCKET
        )
        
        @manager.vsp_service("realtime_echo")
        async def realtime_echo(message: str) -> dict:
            return {"echo": message, "transport": "WebSocket", "realtime": True}
        
        @manager.vsp_service("health")
        async def health() -> dict:
            return {"status": "healthy", "transport": "WebSocket"}
        
        await manager.start_server("localhost", 8003)
    except ImportError:
        print("WebSocket dependencies not available. Install with: pip install websockets")


async def run_http2_service():
    """HTTP/2 Transport - REST-compatible, web-friendly, multiplexed"""
    try:
        print("Starting HTTP/2 Service on localhost:8004...")
        
        manager = VSPManager(
            name="http2-service",
            transport_type=TransportType.HTTP2
        )
        
        @manager.vsp_service("rest_echo")
        async def rest_echo(message: str) -> dict:
            return {"echo": message, "transport": "HTTP/2", "rest_compatible": True}
        
        @manager.vsp_service("health")
        async def health() -> dict:
            return {"status": "healthy", "transport": "HTTP/2"}
        
        await manager.start_server("localhost", 8004)
    except ImportError:
        print("HTTP/2 dependencies not available. Install with: pip install aiohttp")


async def run_grpc_service():
    """gRPC Transport - High-performance RPC, type-safe, streaming support"""
    try:
        print("Starting gRPC Service on localhost:8005...")
        
        manager = VSPManager(
            name="grpc-service",
            transport_type=TransportType.GRPC
        )
        
        @manager.vsp_service("rpc_echo")
        async def rpc_echo(message: str) -> dict:
            return {"echo": message, "transport": "gRPC", "high_performance": True}
        
        @manager.vsp_service("health")
        async def health() -> dict:
            return {"status": "healthy", "transport": "gRPC"}
        
        await manager.start_server("localhost", 8005)
    except ImportError:
        print("gRPC dependencies not available. Install with: pip install grpcio")


async def run_message_queue_service():
    """Message Queue Transport - Asynchronous, persistent, scalable"""
    try:
        print("Starting Message Queue Service on localhost:8006...")
        
        manager = VSPManager(
            name="mq-service",
            transport_type=TransportType.MESSAGE_QUEUE
        )
        
        @manager.vsp_service("async_echo")
        async def async_echo(message: str) -> dict:
            return {"echo": message, "transport": "Message Queue", "persistent": True}
        
        @manager.vsp_service("health")
        async def health() -> dict:
            return {"status": "healthy", "transport": "Message Queue"}
        
        await manager.start_server("localhost", 8006)
    except ImportError:
        print("Message Queue dependencies not available. Install with: pip install aio-pika")


async def run_client_tests():
    """Test client connecting to different transport types"""
    await asyncio.sleep(2)  # Wait for services to start
    
    # Setup service mesh with all transport types
    mesh = ServiceMesh(discovery_type="static")
    mesh.register(ServiceInfo("tcp-service", "localhost", 8001))
    mesh.register(ServiceInfo("udp-service", "localhost", 8002))
    mesh.register(ServiceInfo("websocket-service", "localhost", 8003))
    mesh.register(ServiceInfo("http2-service", "localhost", 8004))
    mesh.register(ServiceInfo("grpc-service", "localhost", 8005))
    mesh.register(ServiceInfo("mq-service", "localhost", 8006))
    
    # Test different transport types
    transport_configs = [
        (TransportType.TCP, "tcp-service", "echo"),
        (TransportType.UDP, "udp-service", "fast_echo"),
        # (TransportType.WEBSOCKET, "websocket-service", "realtime_echo"),
        # (TransportType.HTTP2, "http2-service", "rest_echo"),
        # (TransportType.GRPC, "grpc-service", "rpc_echo"),
        # (TransportType.MESSAGE_QUEUE, "mq-service", "async_echo"),
    ]
    
    for transport_type, service_name, endpoint in transport_configs:
        try:
            print(f"\nTesting {transport_type.value.upper()} transport...")
            
            client_manager = VSPManager(
                name="test-client",
                service_mesh=mesh,
                transport_type=transport_type
            )
            
            response = await client_manager.client.call(
                service_name, 
                endpoint, 
                {"message": f"Hello from {transport_type.value}!"}
            )
            
            print(f"✅ {transport_type.value.upper()} Response: {response}")
            
        except Exception as e:
            print(f"❌ {transport_type.value.upper()} Error: {e}")


async def main():
    """Run the multi-transport example"""
    print("🚀 VSP Multi-Transport Example")
    print("=" * 50)
    
    # Start services with different transports
    services = [
        run_tcp_service(),
        run_udp_service(),
        # run_websocket_service(),
        # run_http2_service(), 
        # run_grpc_service(),
        # run_message_queue_service(),
    ]
    
    # Start client tests
    client_task = asyncio.create_task(run_client_tests())
    
    # Run services and client
    try:
        await asyncio.gather(*services, client_task)
    except KeyboardInterrupt:
        print("\n👋 Shutting down services...")


if __name__ == "__main__":
    print("Transport Support Status:")
    print("- TCP: ✅ Always available")
    print("- UDP: ✅ Always available") 
    print("- WebSocket: ⚠️  Requires 'websockets' package")
    print("- HTTP/2: ⚠️  Requires 'aiohttp' package")
    print("- gRPC: ⚠️  Requires 'grpcio' package")
    print("- Message Queue: ⚠️  Requires 'aio-pika' package")
    print()
    
    asyncio.run(main())
