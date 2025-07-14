"""VSP (Velithon Service Protocol) - High-performance QUIC-based service communication.

This module provides a complete service mesh solution with QUIC transport,
automatic discovery, load balancing, and health monitoring.
"""

from velithon._velithon import RoundRobinBalancer, ServiceInfo, WeightedBalancer

from .abstract import Discovery, Transport
from .client import VSPClient
from .connection_pool import ConnectionPool
from .discovery import ConsulDiscovery, DiscoveryType, MDNSDiscovery, StaticDiscovery
from .manager import VSPManager, WorkerType
from .mesh import ServiceMesh
from .message import VSPMessage
from .protocol import VSPProtocol, LegacyVSPProtocol
from .transport import QuicTransport, AdaptiveTransport, TCPTransport

__all__ = [
    'AdaptiveTransport',
    'ConnectionPool',
    'ConsulDiscovery',
    'Discovery',
    'DiscoveryType',
    'LegacyVSPProtocol',
    'MDNSDiscovery',
    'QuicTransport',
    'RoundRobinBalancer',
    'ServiceInfo',
    'ServiceMesh',
    'StaticDiscovery',
    'TCPTransport',
    'Transport',
    'VSPClient',
    'VSPManager',
    'VSPMessage',
    'VSPProtocol',
    'WeightedBalancer',
    'WorkerType',
]

# Deprecation warnings for TCP usage
import warnings

def create_tcp_transport(*args, **kwargs):
    """Deprecated: Use QuicTransport or AdaptiveTransport instead."""
    warnings.warn(
        "TCPTransport is deprecated. Use QuicTransport for better performance "
        "or AdaptiveTransport for automatic protocol selection.",
        DeprecationWarning,
        stacklevel=2
    )
    return TCPTransport(*args, **kwargs)
