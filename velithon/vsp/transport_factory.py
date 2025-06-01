"""Transport factory for creating different transport implementations."""

import logging
from typing import Dict, Type, Any, List, Optional

from .abstract import Transport, TransportType, ConnectionConfig

logger = logging.getLogger(__name__)


class TransportFactory:
    """Factory for creating transport instances."""
    
    _transport_registry: Dict[TransportType, Type[Transport]] = {}
    
    @classmethod
    def register_transport(cls, transport_type: TransportType, transport_class: Type[Transport]) -> None:
        """Register a transport implementation."""
        cls._transport_registry[transport_type] = transport_class
        logger.debug(f"Registered transport: {transport_type.value} -> {transport_class.__name__}")
    
    @classmethod
    def create_transport(
        cls,
        transport_type: TransportType,
        config: ConnectionConfig,
        **options: Any
    ) -> Transport:
        """Create a transport instance."""
        if transport_type not in cls._transport_registry:
            raise ValueError(f"Transport type {transport_type.value} is not registered")
        
        transport_class = cls._transport_registry[transport_type]
        return transport_class(transport_type=transport_type, **options)
    
    @classmethod
    def get_available_transports(cls) -> List[TransportType]:
        """Get list of available transport types."""
        return list(cls._transport_registry.keys())
    
    @classmethod
    def create_connection_config(
        cls,
        host: str,
        port: Optional[int] = None,
        transport_type: TransportType = TransportType.TCP,
        **options: Any
    ) -> ConnectionConfig:
        """Create a connection configuration."""
        return ConnectionConfig(host=host, port=port, transport_type=transport_type, **options)


def transport_registry(transport_type: TransportType):
    """Decorator to register transport implementations."""
    def decorator(cls: Type[Transport]) -> Type[Transport]:
        TransportFactory.register_transport(transport_type, cls)
        return cls
    return decorator
