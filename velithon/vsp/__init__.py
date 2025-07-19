"""Velithon Service Protocol (VSP) implementation.

VSP provides high-performance inter-service communication with features like
service discovery, connection pooling, and load balancing.
"""

from velithon._velithon import RoundRobinBalancer, ServiceInfo, WeightedBalancer

from .abstract import Discovery, Transport
from .client import VSPClient
from .connection_pool import ConnectionPool
from .discovery import ConsulDiscovery, DiscoveryType, MDNSDiscovery, StaticDiscovery
from .manager import VSPManager, WorkerType
from .mesh import ServiceMesh
from .message import VSPMessage
from .protocol import VSPProtocol
from .transport import TCPTransport

__all__ = [
    'ConnectionPool',
    'ConsulDiscovery',
    'Discovery',
    'DiscoveryType',
    'LoadBalancer',
    'MDNSDiscovery',
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
