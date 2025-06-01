import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Any, Dict

from .abstract import Transport, TransportType, ConnectionConfig
from .protocol import VSPProtocol
from .transport_factory import transport_registry

if TYPE_CHECKING:
    from .manager import VSPManager

logger = logging.getLogger(__name__)


@transport_registry(TransportType.TCP)
class TCPTransport(Transport):
    """TCP implementation of Transport."""

    def __init__(self, transport_type: TransportType = TransportType.TCP):
        super().__init__(transport_type)
        self.transport: Optional[asyncio.Transport] = None
        self.protocol: Optional[VSPProtocol] = None
        self.manager: Optional["VSPManager"] = None

    async def connect(self, config: ConnectionConfig, manager: "VSPManager") -> None:
        self.manager = manager
        try:
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_connection(
                lambda: VSPProtocol(manager), config.host, config.port
            )
            logger.debug(f"TCP connected to {config.host}:{config.port}")
        except (ConnectionRefusedError, OSError) as e:
            logger.error(f"TCP connection failed to {config.host}:{config.port}: {e}")
            raise

    async def send(self, data: bytes) -> None:
        if self.transport is None or self.transport.is_closing():
            logger.error("Cannot send: TCP transport is closed or not connected")
            raise RuntimeError("Transport closed")

        self.transport.write(data)
        logger.debug(f"TCP sent data of length {len(data)}")

    async def receive(self) -> Optional[bytes]:
        """TCP receives data through protocol callbacks, not direct receive calls"""
        # TCP transport uses protocol callbacks for data reception
        return None

    def close(self) -> None:
        if self.transport and not self.transport.is_closing():
            self.transport.close()
            logger.debug("TCP transport closed")
        self.transport = None
        self.protocol = None

    def is_closed(self) -> bool:
        return self.transport is None or self.transport.is_closing()

    def supports_bidirectional(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        if self.transport:
            peername = self.transport.get_extra_info('peername')
            sockname = self.transport.get_extra_info('sockname')
            return {
                'local_address': sockname,
                'remote_address': peername,
                'transport_type': self.transport_type.value
            }
        return {'transport_type': self.transport_type.value}


@transport_registry(TransportType.UDP)
class UDPTransport(Transport):
    """UDP implementation of Transport."""

    def __init__(self, transport_type: TransportType = TransportType.UDP):
        super().__init__(transport_type)
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[asyncio.DatagramProtocol] = None
        self.remote_addr: Optional[tuple] = None
        self.manager: Optional["VSPManager"] = None

    async def connect(self, config: ConnectionConfig, manager: "VSPManager") -> None:
        self.manager = manager
        self.remote_addr = (config.host, config.port)
        
        try:
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_datagram_endpoint(
                lambda: UDPProtocol(manager),
                remote_addr=self.remote_addr
            )
            logger.debug(f"UDP connected to {config.host}:{config.port}")
        except (OSError, asyncio.TimeoutError) as e:
            logger.error(f"UDP connection failed to {config.host}:{config.port}: {e}")
            raise

    async def send(self, data: bytes) -> None:
        if self.transport is None or self.transport.is_closing():
            raise RuntimeError("Transport closed")
        
        self.transport.sendto(data, self.remote_addr)
        logger.debug(f"UDP sent data of length {len(data)}")

    async def receive(self) -> Optional[bytes]:
        """UDP receives data through protocol callbacks"""
        return None

    def close(self) -> None:
        if self.transport and not self.transport.is_closing():
            self.transport.close()
            logger.debug("UDP transport closed")
        self.transport = None
        self.protocol = None

    def is_closed(self) -> bool:
        return self.transport is None or self.transport.is_closing()

    def supports_bidirectional(self) -> bool:
        return True

    def get_connection_info(self) -> Dict[str, Any]:
        return {
            'remote_address': self.remote_addr,
            'transport_type': self.transport_type.value
        }


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP Protocol for handling datagram reception."""
    
    def __init__(self, manager: "VSPManager"):
        self.manager = manager
        
    def datagram_received(self, data: bytes, addr) -> None:
        logger.debug(f"UDP received data from {addr}: {len(data)} bytes")
        # Handle the received datagram
        if hasattr(self.manager, 'handle_data'):
            self.manager.handle_data(data)
