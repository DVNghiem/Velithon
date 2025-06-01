import asyncio
import json
import logging
from typing import TYPE_CHECKING, Optional, Any, Dict

try:
    import aiohttp
    from aiohttp import ClientSession, ClientTimeout
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from ..abstract import Transport, TransportType, ConnectionConfig
from ..transport_factory import transport_registry

if TYPE_CHECKING:
    from ..manager import VSPManager

logger = logging.getLogger(__name__)


@transport_registry(TransportType.HTTP2)
class HTTP2Transport(Transport):
    """HTTP/2 implementation of Transport using aiohttp."""

    def __init__(self, transport_type: TransportType = TransportType.HTTP2):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp package is required for HTTP2 transport. Install with: pip install aiohttp")
        
        super().__init__(transport_type)
        self.session: Optional[ClientSession] = None
        self.base_url: str = ""
        self.manager: Optional["VSPManager"] = None
        self._connected: bool = False

    async def connect(self, config: ConnectionConfig, manager: "VSPManager") -> None:
        self.manager = manager
        
        try:
            # Create HTTP/2 session
            timeout = ClientTimeout(total=config.timeout or 30)
            connector = aiohttp.TCPConnector(
                ssl=config.ssl_context,
                enable_cleanup_closed=True
            )
            
            self.session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers=config.headers or {}
            )
            
            # Build base URL
            scheme = "https" if config.ssl_context else "http"
            self.base_url = f"{scheme}://{config.host}:{config.port}"
            
            # Test connection with a health check
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    self._connected = True
                    logger.debug(f"HTTP/2 connected to {self.base_url}")
                else:
                    raise ConnectionError(f"Health check failed with status {response.status}")
                    
        except Exception as e:
            logger.error(f"HTTP/2 connection failed to {config.host}:{config.port}: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            raise

    async def send(self, data: bytes) -> None:
        if not self._connected or self.session is None or self.session.closed:
            raise RuntimeError("HTTP/2 transport not connected")
        
        try:
            # Send data as POST request
            async with self.session.post(
                f"{self.base_url}/vsp/message",
                data=data,
                headers={'Content-Type': 'application/octet-stream'}
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP/2 send failed with status {response.status}")
                logger.debug(f"HTTP/2 sent data of length {len(data)}")
        except Exception as e:
            logger.error(f"HTTP/2 send error: {e}")
            raise

    async def receive(self) -> Optional[bytes]:
        if not self._connected or self.session is None or self.session.closed:
            return None
        
        try:
            # Poll for messages
            async with self.session.get(f"{self.base_url}/vsp/poll") as response:
                if response.status == 200:
                    data = await response.read()
                    if data:
                        logger.debug(f"HTTP/2 received data of length {len(data)}")
                        return data
                elif response.status == 204:
                    # No content - no messages available
                    return None
                else:
                    logger.warning(f"HTTP/2 receive got status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"HTTP/2 receive error: {e}")
            return None

    def close(self) -> None:
        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            logger.debug("HTTP/2 transport closed")
        self.session = None
        self._connected = False

    def is_closed(self) -> bool:
        return not self._connected or self.session is None or self.session.closed

    def supports_bidirectional(self) -> bool:
        return False  # HTTP/2 is request-response, not truly bidirectional

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            'base_url': self.base_url,
            'connected': self._connected,
            'transport_type': self.transport_type.value
        }
