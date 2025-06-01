"""
Transport implementations for VSP (Velithon Service Protocol).

This package contains various transport layer implementations including:
- TCP: Traditional TCP socket transport
- UDP: UDP datagram transport
- WebSocket: WebSocket transport for web applications
- HTTP2: HTTP/2 transport for REST-like communication
- gRPC: gRPC transport for high-performance RPC
- Message Queue: RabbitMQ/AMQP transport for asynchronous messaging

Each transport implements the Transport abstract base class and is automatically
registered with the TransportFactory when imported.
"""

# Import all transport implementations to register them
try:
    from .websocket import WebSocketTransport
except ImportError:
    pass  # websockets package not available

try:
    from .http2 import HTTP2Transport
except ImportError:
    pass  # aiohttp package not available

try:
    from .grpc_transport import GRPCTransport
except ImportError:
    pass  # grpcio package not available

try:
    from .message_queue import MessageQueueTransport
except ImportError:
    pass  # aio-pika package not available

__all__ = [
    'WebSocketTransport',
    'HTTP2Transport', 
    'GRPCTransport',
    'MessageQueueTransport'
]
