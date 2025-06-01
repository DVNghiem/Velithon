"""
VSP Configuration Management

This module provides configuration classes and utilities for managing
different transport types and their specific settings in the VSP system.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from .abstract import TransportType

logger = logging.getLogger(__name__)


@dataclass
class TransportConfig:
    """Base configuration class for all transport types."""
    
    host: str = "localhost"
    port: int = 0
    timeout: float = 30.0
    max_connections: int = 100
    extra_options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "max_connections": self.max_connections,
            **self.extra_options
        }


@dataclass
class TCPConfig(TransportConfig):
    """Configuration for TCP transport."""
    
    port: int = 8080
    keep_alive: bool = True
    nodelay: bool = True
    reuse_port: bool = True
    backlog: int = 128


@dataclass
class UDPConfig(TransportConfig):
    """Configuration for UDP transport."""
    
    port: int = 8081
    buffer_size: int = 8192
    broadcast: bool = False
    multicast_group: Optional[str] = None
    multicast_ttl: int = 1


@dataclass
class WebSocketConfig(TransportConfig):
    """Configuration for WebSocket transport."""
    
    port: int = 8082
    path: str = "/ws"
    subprotocols: list = field(default_factory=list)
    ping_interval: Optional[float] = 20.0
    ping_timeout: Optional[float] = 10.0
    close_timeout: Optional[float] = 10.0
    compression: Optional[str] = None  # 'deflate' or 'permessage-deflate'


@dataclass
class HTTP2Config(TransportConfig):
    """Configuration for HTTP/2 transport."""
    
    port: int = 8083
    ssl_context: Optional[Any] = None
    max_frame_size: int = 16384
    max_concurrent_streams: int = 100
    initial_window_size: int = 65535
    max_header_list_size: int = 8192


@dataclass
class GRPCConfig(TransportConfig):
    """Configuration for gRPC transport."""
    
    port: int = 8084
    ssl_context: Optional[Any] = None
    compression: Optional[str] = None  # 'gzip' or 'deflate'
    max_workers: int = 10
    keepalive_time_ms: int = 30000
    keepalive_timeout_ms: int = 5000
    keepalive_permit_without_calls: bool = True
    max_connection_idle_ms: Optional[int] = None
    max_connection_age_ms: Optional[int] = None


@dataclass
class MessageQueueConfig(TransportConfig):
    """Configuration for message queue transport."""
    
    port: int = 5672  # Default for RabbitMQ
    queue_name: str = "vsp_queue"
    exchange_name: str = "vsp_exchange"
    routing_key: str = "vsp"
    username: Optional[str] = None
    password: Optional[str] = None
    virtual_host: str = "/"
    connection_timeout: float = 10.0
    heartbeat: int = 600
    max_retries: int = 3
    retry_delay: float = 1.0


class ConfigManager:
    """Manages transport configurations for the VSP system."""
    
    def __init__(self):
        self._configs: Dict[TransportType, TransportConfig] = {}
        self._default_configs = {
            TransportType.TCP: TCPConfig(),
            TransportType.UDP: UDPConfig(),
            TransportType.WEBSOCKET: WebSocketConfig(),
            TransportType.HTTP2: HTTP2Config(),
            TransportType.GRPC: GRPCConfig(),
            TransportType.MESSAGE_QUEUE: MessageQueueConfig(),
        }
    
    def get_config(self, transport_type: TransportType) -> TransportConfig:
        """Get configuration for a specific transport type."""
        if transport_type in self._configs:
            return self._configs[transport_type]
        
        if transport_type in self._default_configs:
            return self._default_configs[transport_type]
        
        logger.warning(f"No configuration found for transport type {transport_type}, using base config")
        return TransportConfig()
    
    def set_config(self, transport_type: TransportType, config: TransportConfig):
        """Set configuration for a specific transport type."""
        self._configs[transport_type] = config
        logger.debug(f"Updated configuration for transport type {transport_type}")
    
    def configure_transport(
        self, 
        transport_type: TransportType, 
        **kwargs
    ) -> TransportConfig:
        """Configure a transport with the provided options."""
        config_class = self._get_config_class(transport_type)
        
        # Get existing config or default
        existing_config = self.get_config(transport_type)
        
        # Update with new values
        config_dict = existing_config.to_dict()
        config_dict.update(kwargs)
        
        # Create new config instance
        new_config = config_class(**{
            k: v for k, v in config_dict.items() 
            if k in config_class.__dataclass_fields__
        })
        
        # Store the new configuration
        self.set_config(transport_type, new_config)
        return new_config
    
    def _get_config_class(self, transport_type: TransportType) -> type:
        """Get the appropriate configuration class for a transport type."""
        config_classes = {
            TransportType.TCP: TCPConfig,
            TransportType.UDP: UDPConfig,
            TransportType.WEBSOCKET: WebSocketConfig,
            TransportType.HTTP2: HTTP2Config,
            TransportType.GRPC: GRPCConfig,
            TransportType.MESSAGE_QUEUE: MessageQueueConfig,
        }
        return config_classes.get(transport_type, TransportConfig)
    
    def reset_config(self, transport_type: TransportType):
        """Reset configuration for a transport type to default."""
        if transport_type in self._configs:
            del self._configs[transport_type]
            logger.debug(f"Reset configuration for transport type {transport_type} to default")
    
    def list_configs(self) -> Dict[TransportType, TransportConfig]:
        """List all configured transport types and their configurations."""
        result = {}
        for transport_type in TransportType:
            result[transport_type] = self.get_config(transport_type)
        return result


# Global configuration manager instance
config_manager = ConfigManager()


def configure_transport(
    transport_type: Union[TransportType, str], 
    **kwargs
) -> TransportConfig:
    """
    Configure a transport with the provided options.
    
    Args:
        transport_type: The transport type to configure
        **kwargs: Configuration options specific to the transport type
        
    Returns:
        The updated configuration object
        
    Example:
        configure_transport(TransportType.TCP, host="0.0.0.0", port=9090, keep_alive=False)
        configure_transport("websocket", path="/custom-ws", ping_interval=30.0)
    """
    if isinstance(transport_type, str):
        transport_type = TransportType[transport_type.upper()]
    
    return config_manager.configure_transport(transport_type, **kwargs)


def get_transport_config(
    transport_type: Union[TransportType, str]
) -> TransportConfig:
    """
    Get the current configuration for a transport type.
    
    Args:
        transport_type: The transport type to get configuration for
        
    Returns:
        The configuration object for the transport type
        
    Example:
        tcp_config = get_transport_config(TransportType.TCP)
        ws_config = get_transport_config("websocket")
    """
    if isinstance(transport_type, str):
        transport_type = TransportType[transport_type.upper()]
    
    return config_manager.get_config(transport_type)