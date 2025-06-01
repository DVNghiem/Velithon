import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Any, Dict

try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False

from ..abstract import Transport, TransportType, ConnectionConfig
from ..transport_factory import transport_registry

if TYPE_CHECKING:
    from ..manager import VSPManager

logger = logging.getLogger(__name__)


@transport_registry(TransportType.GRPC)
class GRPCTransport(Transport):
    """gRPC implementation of Transport."""

    def __init__(self, transport_type: TransportType = TransportType.GRPC):
        if not GRPC_AVAILABLE:
            raise ImportError("grpcio package is required for gRPC transport. Install with: pip install grpcio")
        
        super().__init__(transport_type)
        self.channel: Optional[aio.Channel] = None
        self.stub: Optional[Any] = None  # Will be properly typed when VSP service is defined
        self.manager: Optional["VSPManager"] = None
        self._connected: bool = False

    async def connect(self, config: ConnectionConfig, manager: "VSPManager") -> None:
        self.manager = manager
        
        try:
            # Build channel target
            target = f"{config.host}:{config.port}"
            
            # Create channel options
            options = [
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000)
            ]
            
            if config.ssl_context:
                # Use secure channel
                credentials = grpc.ssl_channel_credentials()
                self.channel = aio.secure_channel(target, credentials, options=options)
            else:
                # Use insecure channel
                self.channel = aio.insecure_channel(target, options=options)
            
            # Test connection
            await self.channel.channel_ready()
            self._connected = True
            
            # TODO: Create stub when VSP gRPC service is defined
            # self.stub = VSPServiceStub(self.channel)
            
            logger.debug(f"gRPC connected to {target}")
            
        except Exception as e:
            logger.error(f"gRPC connection failed to {config.host}:{config.port}: {e}")
            if self.channel:
                await self.channel.close()
                self.channel = None
            raise

    async def send(self, data: bytes) -> None:
        if not self._connected or self.channel is None:
            raise RuntimeError("gRPC transport not connected")
        
        try:
            # TODO: Implement when VSP gRPC service is defined
            # For now, this is a placeholder
            logger.debug(f"gRPC would send data of length {len(data)}")
            # response = await self.stub.SendMessage(MessageRequest(data=data))
        except Exception as e:
            logger.error(f"gRPC send error: {e}")
            raise

    async def receive(self) -> Optional[bytes]:
        if not self._connected or self.channel is None:
            return None
        
        try:
            # TODO: Implement when VSP gRPC service is defined
            # For now, this is a placeholder
            logger.debug("gRPC would receive data")
            # response = await self.stub.ReceiveMessage(Empty())
            # return response.data if response.data else None
            return None
        except Exception as e:
            logger.error(f"gRPC receive error: {e}")
            return None

    def close(self) -> None:
        if self.channel:
            asyncio.create_task(self.channel.close())
            logger.debug("gRPC transport closed")
        self.channel = None
        self.stub = None
        self._connected = False

    def is_closed(self) -> bool:
        return not self._connected or self.channel is None

    def supports_bidirectional(self) -> bool:
        return True  # gRPC supports bidirectional streaming

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            'connected': self._connected,
            'transport_type': self.transport_type.value
        }
