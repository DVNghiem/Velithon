"""Protocol implementation for VSP (Velithon Service Protocol).

This module provides the core VSP protocol implementation including
message formats, handshaking, and protocol state management.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import VSPManager
from .message import VSPError, VSPMessage

logger = logging.getLogger(__name__)


class VSPProtocol(asyncio.Protocol):
    """Asyncio protocol implementation for Velithon Service Protocol (VSP).

    Handles connection lifecycle, message parsing, and communication with the VSPManager.
    Responsible for receiving, processing, and sending VSP messages over the network.
    """  # noqa: E501

    def __init__(self, manager: 'VSPManager'):
        """Initialize the VSPProtocol with a reference to the VSPManager.

        Args:
            manager (VSPManager): The manager responsible for handling VSP messages and connections.

        """  # noqa: E501
        self.manager = manager
        self.transport: asyncio.Transport | None = None
        self.buffer = bytearray()

    def connection_made(self, transport: asyncio.Transport) -> None:
        """Establish a connection.

        Args:
            transport (asyncio.Transport): The transport representing the connection.

        """
        self.transport = transport
        logger.debug(f'Connection made: {transport.get_extra_info("peername")}')

    def connection_lost(self, exc: Exception | None) -> None:
        """Handle the loss of a connection.

        Args:
            exc (Exception | None): The exception that caused the connection to be lost, if any.

        """  # noqa: E501
        logger.debug(f'Connection lost: {exc}')
        if self.transport:
            self.transport.close()

    def data_received(self, data: bytes) -> None:
        """Handle incoming data from the transport."""
        self.buffer.extend(data)
        while len(self.buffer) >= 4:
            length = int.from_bytes(self.buffer[:4], 'big')
            # Check if we have enough data for the complete message
            if len(self.buffer) < 4 + length:
                break  # Wait for more data

            message_data = self.buffer[4 : 4 + length]
            self.buffer = self.buffer[4 + length :]
            try:
                message = VSPMessage.from_bytes(message_data)
                # Create task but don't await to avoid blocking the protocol
                asyncio.create_task(self.manager.enqueue_message(message, self))  # noqa: RUF006
            except VSPError as e:
                logger.error(f'Failed to process message: {e}')
                # Continue processing other messages even if one fails

    async def handle_message(self, message: VSPMessage) -> None:
        """Handle a received VSP message."""
        try:
            response = await self.manager.handle_vsp_endpoint(
                message.header['endpoint'], message.body
            )
            response_msg = VSPMessage(
                message.header['request_id'],
                message.header['service'],
                message.header['endpoint'],
                response,
                is_response=True,
            )
            self.send_message(response_msg)
        except VSPError as e:
            logger.error(f'Error handling message: {e}')
            error_msg = VSPMessage(
                message.header['request_id'],
                message.header['service'],
                message.header['endpoint'],
                {'error': str(e)},
                is_response=True,
            )
            self.send_message(error_msg)

    def send_message(self, message: VSPMessage) -> None:
        """Send a VSP message over the transport."""
        if self.transport and not self.transport.is_closing():
            data = message.to_bytes()
            length = len(data).to_bytes(4, 'big')
            self.transport.write(length + data)
            logger.debug(f'Sent message: {message.header}')
