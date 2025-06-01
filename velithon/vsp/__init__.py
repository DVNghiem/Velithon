import importlib.util

from .abstract import Discovery, LoadBalancer, Transport, TransportType, ConnectionConfig
from .client import VSPClient
from .connection_pool import ConnectionPool
from .discovery import ConsulDiscovery, DiscoveryType, MDNSDiscovery, StaticDiscovery
from .load_balancer import RoundRobinBalancer, WeightedBalancer
from .manager import VSPManager, WorkerType
from .mesh import ServiceMesh
from .message import VSPMessage
from .protocol import VSPProtocol
from .service import ServiceInfo
from .transport import TCPTransport, UDPTransport
from .transport_factory import TransportFactory
from .config import (
    ConfigManager, TransportConfig, TCPConfig, UDPConfig, 
    WebSocketConfig, HTTP2Config, GRPCConfig, MessageQueueConfig,
    configure_transport, get_transport_config, config_manager
)

# Import additional transports if available - this registers them with the factory
if importlib.util.find_spec("velithon.vsp.transports"):
    import velithon.vsp.transports  # noqa: F401

__all__ = [
    "VSPMessage",
    "VSPProtocol",
    "VSPClient",
    "VSPManager",
    "ServiceInfo",
    "ServiceMesh",
    "WorkerType",
    "DiscoveryType",
    "ConsulDiscovery",
    "MDNSDiscovery",
    "StaticDiscovery",
    "LoadBalancer",
    "RoundRobinBalancer",
    "WeightedBalancer",
    "Transport",
    "TransportType",
    "ConnectionConfig",
    "Discovery",
    "TCPTransport",
    "UDPTransport",
    "TransportFactory",
    "ConnectionPool",
    # Configuration classes
    "ConfigManager",
    "TransportConfig",
    "TCPConfig",
    "UDPConfig",
    "WebSocketConfig",
    "HTTP2Config", 
    "GRPCConfig",
    "MessageQueueConfig",
    "configure_transport",
    "get_transport_config",
    "config_manager",
]
