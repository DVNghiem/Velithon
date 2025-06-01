import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Any, Dict

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from ..abstract import Transport, TransportType, ConnectionConfig
from ..transport_factory import transport_registry

if TYPE_CHECKING:
    from ..manager import VSPManager

logger = logging.getLogger(__name__)


@transport_registry(TransportType.WEBSOCKET)
class WebSocketTransport(Transport):
    """WebSocket implementation of Transport."""

    def __init__(self, transport_type: TransportType = TransportType.WEBSOCKET):
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package is required for WebSocket transport. Install with: pip install websockets")
        
        super().__init__(transport_type)
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.manager: Optional["VSPManager"] = None

    async def connect(self, config: ConnectionConfig, manager: "VSPManager") -> None:
        self.manager = manager
        try:
            uri = f"ws://{config.host}:{config.port}"
            if config.ssl_context:
                uri = f"wss://{config.host}:{config.port}"
            
            connect_kwargs = {}
            if config.ssl_context:
                connect_kwargs['ssl'] = config.ssl_context
            if config.headers:
                connect_kwargs['extra_headers'] = config.headers
            if config.timeout:
                connect_kwargs['close_timeout'] = config.timeout
                
            self.websocket = await websockets.connect(uri, **connect_kwargs)
            logger.debug(f"WebSocket connected to {uri}")
        except Exception as e:
            logger.error(f"WebSocket connection failed to {config.host}:{config.port}: {e}")
            raise

    async def send(self, data: bytes) -> None:
        if self.websocket is None or self.websocket.closed:
            raise RuntimeError("WebSocket closed")
        
        await self.websocket.send(data)
        logger.debug(f"WebSocket sent data of length {len(data)}")

    async def receive(self) -> Optional[bytes]:
        if self.websocket is None or self.websocket.closed:
            return None
        
        try:
            message = await self.websocket.recv()
            if isinstance(message, str):
                return message.encode('utf-8')
            return message
        except ConnectionClosed:
            logger.debug("WebSocket connection closed")
            return None

    def close(self) -> None:
        if self.websocket and not self.websocket.closed:
            asyncio.create_task(self.websocket.close())
            logger.debug("WebSocket transport closed")
        self.websocket = None

    def is_closed(self) -> bool:
        return self.websocket is None or self.websocket.closed

    def supports_bidirectional(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        if self.websocket:
            return {
                'local_address': getattr(self.websocket, 'local_address', None),
                'remote_address': getattr(self.websocket, 'remote_address', None),
                'transport_type': self.transport_type.value
            }
        return {'transport_type': self.transport_type.value}
