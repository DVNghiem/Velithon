import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any
import _velithon

from .abstract import Transport
from .protocol import VSPProtocol

if TYPE_CHECKING:
    from .manager import VSPManager

logger = logging.getLogger(__name__)


class QuicTransport(Transport):
    """High-performance QUIC implementation of Transport using Rust backend."""

    def __init__(self, manager: 'VSPManager', compression_enabled: bool = True):
        self.manager = manager
        self.compression_enabled = compression_enabled
        self.rust_transport: Optional[_velithon.QuicTransport] = None
        self.rust_client: Optional[_velithon.SimpleVSPClient] = None
        self._connected = False
        self._host = ""
        self._port = 0

    async def connect(self, host: str, port: int) -> None:
        """Connect to the VSP service using QUIC protocol."""
        try:
            # Initialize Rust QUIC transport
            self.rust_transport = _velithon.QuicTransport(False, self.compression_enabled)
            self.rust_client = _velithon.SimpleVSPClient()
            
            # Connect using the Rust client
            result = self.rust_client.connect(host, port)
            
            self._connected = True
            self._host = host
            self._port = port
            
            logger.info(f'QUIC connected to {host}:{port} with compression={self.compression_enabled}')
            logger.debug(f'Connection result: {result}')
            
        except Exception as e:
            logger.error(f'QUIC connection failed to {host}:{port}: {e}')
            self._connected = False
            raise ConnectionRefusedError(f'Failed to connect via QUIC: {e}')

    def send(self, data: bytes) -> None:
        """Send data using QUIC transport with automatic compression."""
        if not self._connected or not self.rust_client:
            logger.error('Cannot send: QUIC transport is not connected')
            raise RuntimeError('Transport not connected')

        try:
            # Use the Rust client to send data
            # For now, we'll use a default service/method - this can be enhanced
            response = self.rust_client.send_request(
                service_name="vsp",
                method="message", 
                data=data,
                headers={"Content-Type": "application/vsp"}
            )
            
            logger.debug(f'QUIC sent data of length {len(data)}, got response: {response.is_success()}')
            
            # If we got a response, notify the manager
            if response.is_success() and self.manager:
                # Convert back to VSPMessage format for compatibility
                asyncio.create_task(self._handle_response(response))
                
        except Exception as e:
            logger.error(f'QUIC send failed: {e}')
            raise RuntimeError(f'Send failed: {e}')

    async def _handle_response(self, response) -> None:
        """Handle response from Rust transport and forward to manager."""
        try:
            # This would be enhanced to properly parse VSP messages
            # For now, we'll create a basic message structure
            if hasattr(self.manager, 'handle_response'):
                await self.manager.handle_response(response.data)
        except Exception as e:
            logger.error(f'Error handling QUIC response: {e}')

    def close(self) -> None:
        """Close the QUIC transport connection."""
        if self.rust_client and self._connected:
            try:
                self.rust_client.disconnect()
                logger.debug('QUIC transport closed')
            except Exception as e:
                logger.warning(f'Error closing QUIC transport: {e}')
        
        self._connected = False
        self.rust_transport = None
        self.rust_client = None

    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        return not self._connected or not self.rust_client

    def get_stats(self) -> Dict[str, Any]:
        """Get transport statistics."""
        if self.rust_client and self._connected:
            return {
                'transport_type': 'QUIC',
                'host': self._host,
                'port': self._port,
                'connected': self._connected,
                'compression_enabled': self.compression_enabled,
            }
        return {
            'transport_type': 'QUIC',
            'connected': False,
        }


class AdaptiveTransport(Transport):
    """Adaptive transport that intelligently selects the best protocol."""

    def __init__(self, manager: 'VSPManager', prefer_quic: bool = True):
        self.manager = manager
        self.prefer_quic = prefer_quic
        self.rust_transport: Optional[_velithon.AdaptiveTransport] = None
        self.rust_client: Optional[_velithon.SimpleVSPClient] = None
        self._connected = False
        self._active_protocol = None

    async def connect(self, host: str, port: int) -> None:
        """Connect using adaptive transport selection."""
        try:
            # Initialize Rust adaptive transport
            self.rust_transport = _velithon.AdaptiveTransport(self.prefer_quic)
            self.rust_client = _velithon.SimpleVSPClient()
            
            # Connect using adaptive selection
            result = self.rust_client.connect(host, port)
            
            self._connected = True
            self._active_protocol = "QUIC" if self.prefer_quic else "TCP"
            
            logger.info(f'Adaptive transport connected to {host}:{port} using {self._active_protocol}')
            logger.debug(f'Connection result: {result}')
            
        except Exception as e:
            logger.error(f'Adaptive connection failed to {host}:{port}: {e}')
            self._connected = False
            raise ConnectionRefusedError(f'Failed to connect adaptively: {e}')

    def send(self, data: bytes) -> None:
        """Send data using the active transport protocol."""
        if not self._connected or not self.rust_client:
            logger.error('Cannot send: Adaptive transport is not connected')
            raise RuntimeError('Transport not connected')

        try:
            response = self.rust_client.send_request(
                service_name="vsp",
                method="adaptive_message",
                data=data,
                headers={"Protocol": self._active_protocol}
            )
            
            logger.debug(f'Adaptive transport ({self._active_protocol}) sent data of length {len(data)}')
            
            if response.is_success() and self.manager:
                asyncio.create_task(self._handle_response(response))
                
        except Exception as e:
            logger.error(f'Adaptive send failed: {e}')
            raise RuntimeError(f'Send failed: {e}')

    async def _handle_response(self, response) -> None:
        """Handle response from adaptive transport."""
        try:
            if hasattr(self.manager, 'handle_response'):
                await self.manager.handle_response(response.data)
        except Exception as e:
            logger.error(f'Error handling adaptive response: {e}')

    def close(self) -> None:
        """Close the adaptive transport connection."""
        if self.rust_client and self._connected:
            try:
                self.rust_client.disconnect()
                logger.debug(f'Adaptive transport ({self._active_protocol}) closed')
            except Exception as e:
                logger.warning(f'Error closing adaptive transport: {e}')
        
        self._connected = False
        self._active_protocol = None
        self.rust_transport = None
        self.rust_client = None

    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        return not self._connected or not self.rust_client

    def get_stats(self) -> Dict[str, Any]:
        """Get adaptive transport statistics."""
        return {
            'transport_type': 'Adaptive',
            'active_protocol': self._active_protocol,
            'connected': self._connected,
            'prefer_quic': self.prefer_quic,
        }


# Legacy TCP transport for backwards compatibility
class TCPTransport(Transport):
    """Legacy TCP implementation of Transport (deprecated)."""

    def __init__(self, manager: 'VSPManager'):
        self.transport: asyncio.Transport | None = None
        self.protocol: VSPProtocol | None = None
        self.manager = manager
        logger.warning("TCPTransport is deprecated. Please use QuicTransport or AdaptiveTransport for better performance.")

    async def connect(self, host: str, port: int) -> None:
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
        if self.transport is None or self.transport.is_closing():
            logger.error('Cannot send: TCP transport is closed or not connected')
            raise RuntimeError('Transport closed')

        self.transport.write(data)
        logger.debug(f'TCP sent data of length {len(data)}')

    def close(self) -> None:
        if self.transport and not self.transport.is_closing():
            self.transport.close()
            logger.debug('TCP transport closed')
        self.transport = None
        self.protocol = None

    def is_closed(self) -> bool:
        return self.transport is None or self.transport.is_closing()

    def get_stats(self) -> Dict[str, Any]:
        return {
            'transport_type': 'TCP',
            'connected': not self.is_closed(),
        }
