"""Transport layer for VSP (Velithon Service Protocol).

This module provides transport layer implementations for VSP including
TCP, WebSocket, and other transport protocols for service communication.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from .abstract import Transport
from .protocol import VSPProtocol

if TYPE_CHECKING:
    from .manager import VSPManager

logger = logging.getLogger(__name__)


class TCPTransport(Transport):
    """TCP implementation of Transport."""

    def __init__(self, manager: 'VSPManager'):
        """Initialize TCP transport with a reference to the VSPManager."""
        self.transport: asyncio.Transport | None = None
        self.protocol: VSPProtocol | None = None
        self.manager = manager

    async def connect(self, host: str, port: int) -> None:
        """Establish a TCP connection to the specified host and port."""
        try:
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_connection(
                lambda: VSPProtocol(self.manager), host, port
            )
            logger.debug(f'TCP connected to {host}:{port}')
        except (ConnectionRefusedError, OSError) as e:
            logger.error(f'TCP connection failed to {host}:{port}: {e}')
            raise

    def send(self, data: bytes) -> None:
        """Send data over the TCP transport."""
        if self.transport is None or self.transport.is_closing():
            logger.error('Cannot send: TCP transport is closed or not connected')
            raise RuntimeError('Transport closed')

        self.transport.write(data)
        logger.debug(f'TCP sent data of length {len(data)}')

    def close(self) -> None:
        """Close the TCP transport."""
        if self.transport and not self.transport.is_closing():
            self.transport.close()
            logger.debug('TCP transport closed')
        self.transport = None
        self.protocol = None

    def is_closed(self) -> bool:
        """Check if the TCP transport is closed."""
        return self.transport is None or self.transport.is_closing()
