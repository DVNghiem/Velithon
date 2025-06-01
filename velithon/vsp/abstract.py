from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

from .service import ServiceInfo


class TransportType(Enum):
    """Supported transport types."""
    TCP = "tcp"
    UDP = "udp"
    WEBSOCKET = "websocket"
    HTTP2 = "http2"
    GRPC = "grpc"
    MESSAGE_QUEUE = "message_queue"


class ConnectionConfig:
    """Configuration for transport connections."""
    
    def __init__(
        self,
        host: str,
        port: Optional[int] = None,
        transport_type: TransportType = TransportType.TCP,
        **kwargs: Any
    ):
        self.host = host
        self.port = port
        self.transport_type = transport_type
        self.options = kwargs


class Transport(ABC):
    """Abstract Transport interface for VSP communication."""

    def __init__(self, transport_type: TransportType, **options: Any):
        self.transport_type = transport_type
        self.options = options
        self.connection_config: Optional[ConnectionConfig] = None

    @abstractmethod
    async def connect(self, config: ConnectionConfig) -> None:
        """Connect using the provided configuration."""
        pass

    @abstractmethod
    async def send(self, message: bytes) -> None:
        """Send a VSP message."""
        pass

    @abstractmethod
    async def receive(self) -> Optional[bytes]:
        """Receive a VSP message (for bidirectional transports)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport."""
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        pass

    @abstractmethod
    def supports_bidirectional(self) -> bool:
        """Check if transport supports bidirectional communication."""
        pass

    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging/monitoring."""
        pass


class Discovery(ABC):
    """Abstract Service Discovery interface."""

    @abstractmethod
    def register(self, service: ServiceInfo) -> None:
        """Register a service."""
        pass

    @abstractmethod
    async def query(self, service_name: str) -> List[ServiceInfo]:
        """Query service instances."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close discovery resources."""
        pass


class LoadBalancer(ABC):
    """Abstract Load Balancer interface."""

    @abstractmethod
    def select(self, instances: List[ServiceInfo]) -> ServiceInfo:
        """Select a service instance."""
        pass
