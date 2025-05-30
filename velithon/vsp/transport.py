import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from .manager import VSPManager
from .protocol import VSPProtocol

logger = logging.getLogger(__name__)

class Transport(ABC):
    """Abstract Transport interface for VSP communication."""
    @abstractmethod
    async def connect(self, host: str, port: str) -> None:
        """Connect to the specified host and port."""
        pass

    @abstractmethod
    def send(self, message: bytes) -> None:
        """Send a VSP message."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""
        pass

    @abstractmethod
    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        pass

class TCPTransport(Transport):
    """TCP implementation of Transport."""
    def __init__(self, 
                manager: 'VSPManager'):
        self.transport: Optional[asyncio.Transport] = None
        self.protocol: Optional[VSPProtocol] = None
        self.manager = manager

    async def connect(self, host: str, port: int) -> None:
        try:
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_connection(
                lambda: VSPProtocol(self.manager), host, port
            )
            logger.debug(f"TCP connected to {host}:{port}")
        except (ConnectionRefusedError, OSError) as e:
            logger.error(f"TCP connection failed to {host}:{port}: {e}")
            raise

    def send(self, data: bytes) -> None:
        if self.transport is None or self.transport.is_closing():
            logger.error("Cannot send: TCP transport is closed or not connected")
            raise RuntimeError("Transport closed")
        self.transport.write(data)
        logger.debug(f"TCP sent data of length {len(data)}")

    def close(self) -> None:
        if self.transport and not self.transport.is_closing():
            self.transport.close()
            logger.debug("TCP transport closed")
        self.transport = None
        self.protocol = None

    def is_closed(self) -> bool:
        return self.transport is None or self.transport.is_closing()