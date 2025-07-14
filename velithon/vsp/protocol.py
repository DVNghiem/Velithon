"""
Enhanced VSP Protocol implementation using QUIC transport and Protocol Buffers.

This module provides the new high-performance VSP protocol implementation that replaces
the old TCP asyncio approach with QUIC-based transport using Rust backend.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict
import json
import _velithon

if TYPE_CHECKING:
    from .manager import VSPManager
from .message import VSPError, VSPMessage

logger = logging.getLogger(__name__)


class VSPProtocol:
    """
    Enhanced VSP Protocol using QUIC transport with Protocol Buffers and compression.
    
    This replaces the old asyncio.Protocol-based implementation with a high-performance
    QUIC-based approach using our Rust backend.
    """

    def __init__(self, manager: 'VSPManager'):
        """Initialize the VSP protocol with the given manager."""
        self.manager = manager
        self.rust_client: _velithon.SimpleVSPClient | None = None
        self.connected = False
        self.host = ""
        self.port = 0
        self.compression_enabled = True
        self.background_tasks: set[asyncio.Task] = set()

    async def connect(self, host: str, port: int) -> None:
        """Establish connection using QUIC protocol."""
        try:
            self.rust_client = _velithon.SimpleVSPClient()
            result = self.rust_client.connect(host, port)
            
            self.connected = True
            self.host = host
            self.port = port
            
            logger.info(f'VSP Protocol connected to {host}:{port} via QUIC')
            logger.debug(f'Connection result: {result}')
            
        except Exception as e:
            logger.error(f'VSP Protocol connection failed to {host}:{port}: {e}')
            self.connected = False
            raise

    def connection_made(self, host: str, port: int) -> None:
        """Handle connection establishment."""
        self.host = host
        self.port = port
        self.connected = True
        logger.debug(f'VSP connection made to {host}:{port}')

    def connection_lost(self, exc: Exception | None) -> None:
        """Handle connection loss."""
        logger.debug(f'VSP connection lost: {exc}')
        self.connected = False
        if self.rust_client:
            try:
                self.rust_client.disconnect()
            except Exception as e:
                logger.warning(f'Error disconnecting Rust client: {e}')
        self.rust_client = None

    async def send_message_async(self, message: VSPMessage) -> _velithon.VspResponse:
        """
        Send a VSP message asynchronously using QUIC transport.
        
        Args:
            message: The VSP message to send
            
        Returns:
            The response from the remote service
            
        Raises:
            VSPError: If sending fails or client is not connected
        """
        if not self.rust_client or not self.connected:
            raise VSPError('Protocol not connected')

        try:
            # Convert VSPMessage to our Rust format
            message_data = self._serialize_message(message)
            
            # Add compression if enabled
            if self.compression_enabled and len(message_data) > 100:  # Only compress larger messages
                message_data = _velithon.compress_zstd(message_data)
                logger.debug(f'Compressed message data from {len(message_data)} bytes')

            # Send via Rust client
            response = self.rust_client.send_request(
                service_name=message.header.get('service', 'unknown'),
                method=message.header.get('endpoint', 'call'),
                data=message_data,
                headers={
                    'request_id': message.header.get('request_id', ''),
                    'content_type': 'application/vsp+json',
                    'compression': 'zstd' if self.compression_enabled else 'none'
                }
            )
            
            logger.debug(f'Sent VSP message {message.header.get("request_id")}, success: {response.is_success()}')
            return response
            
        except Exception as e:
            logger.error(f'Failed to send VSP message: {e}')
            raise VSPError(f'Send failed: {e}') from e

    def send_message(self, message: VSPMessage) -> None:
        """Send a message synchronously (creates async task)."""
        if not self.connected:
            raise VSPError('Protocol not connected')
        
        # Create background task for async sending
        task = asyncio.create_task(self._send_and_handle(message))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _send_and_handle(self, message: VSPMessage) -> None:
        """Send message and handle response in background."""
        try:
            response = await self.send_message_async(message)
            if response.is_success():
                # Handle the response
                await self._handle_response(message, response)
        except Exception as e:
            logger.error(f'Error in background message sending: {e}')

    async def _handle_response(self, original_message: VSPMessage, response: _velithon.VspResponse) -> None:
        """Handle response from the remote service."""
        try:
            # Decompress if needed
            response_data = response.data
            if hasattr(response, 'headers') and response.headers.get('compression') == 'zstd':
                response_data = _velithon.decompress_zstd(response_data)

            # Parse response data
            parsed_response = self._deserialize_response(response_data)
            
            # Create response message
            response_msg = VSPMessage(
                original_message.header['request_id'],
                original_message.header['service'],
                original_message.header['endpoint'],
                parsed_response,
                is_response=True,
            )
            
            # Notify manager
            if hasattr(self.manager, 'handle_response'):
                await self.manager.handle_response(response_msg)
                
        except Exception as e:
            logger.error(f'Error handling VSP response: {e}')

    async def handle_message(self, message: VSPMessage) -> None:
        """Handle incoming message (for server mode)."""
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

    def _serialize_message(self, message: VSPMessage) -> bytes:
        """Serialize VSP message to bytes."""
        try:
            # Convert to a format compatible with our Rust backend
            message_dict = {
                'header': message.header,
                'body': message.body,
                'timestamp': getattr(message, 'timestamp', None)
            }
            return json.dumps(message_dict).encode('utf-8')
        except Exception as e:
            raise VSPError(f'Message serialization failed: {e}') from e

    def _deserialize_response(self, data: bytes) -> dict:
        """Deserialize response data."""
        try:
            if isinstance(data, bytes):
                return json.loads(data.decode('utf-8'))
            return {'data': str(data)}
        except Exception as e:
            logger.warning(f'Failed to deserialize response: {e}')
            return {'raw_data': data.decode('utf-8', errors='replace')}

    def get_stats(self) -> dict[str, Any]:
        """Get protocol statistics."""
        return {
            'protocol_type': 'VSP-QUIC',
            'connected': self.connected,
            'host': self.host,
            'port': self.port,
            'compression_enabled': self.compression_enabled,
            'background_tasks': len(self.background_tasks),
        }

    def close(self) -> None:
        """Close the protocol connection."""
        if self.rust_client and self.connected:
            try:
                self.rust_client.disconnect()
                logger.debug('VSP Protocol connection closed')
            except Exception as e:
                logger.warning(f'Error closing VSP protocol: {e}')
        
        # Cancel background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        
        self.connected = False
        self.rust_client = None


# Legacy protocol for backwards compatibility
class LegacyVSPProtocol(asyncio.Protocol):
    """Legacy TCP-based VSP Protocol (deprecated)."""

    def __init__(self, manager: 'VSPManager'):
        """Initialize legacy protocol."""
        self.manager = manager
        self.transport: asyncio.Transport | None = None
        self.buffer = bytearray()
        logger.warning("LegacyVSPProtocol is deprecated. Use VSPProtocol with QUIC transport.")

    def connection_made(self, transport: asyncio.Transport) -> None:
        """Handle connection establishment."""
        self.transport = transport
        logger.debug(f'Legacy connection made: {transport.get_extra_info("peername")}')

    def connection_lost(self, exc: Exception | None) -> None:
        """Handle connection loss."""
        logger.debug(f'Legacy connection lost: {exc}')
        if self.transport:
            self.transport.close()

    def data_received(self, data: bytes) -> None:
        """Handle received data."""
        self.buffer.extend(data)
        while len(self.buffer) >= 4:
            length = int.from_bytes(self.buffer[:4], 'big')
            if len(self.buffer) < 4 + length:
                break

            message_data = self.buffer[4 : 4 + length]
            self.buffer = self.buffer[4 + length :]
            try:
                message = VSPMessage.from_bytes(message_data)
                asyncio.create_task(self.manager.enqueue_message(message, self))
            except VSPError as e:
                logger.error(f'Failed to process legacy message: {e}')

    def send_message(self, message: VSPMessage) -> None:
        """Send message via legacy transport."""
        if self.transport and not self.transport.is_closing():
            data = message.to_bytes()
            length = len(data).to_bytes(4, 'big')
            self.transport.write(length + data)
            logger.debug(f'Sent legacy message: {message.header}')
