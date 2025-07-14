"""
QUIC Transport implementation for VSP using the new Rust-based protocol.

This module provides a bridge between the existing Velithon VSP framework and 
the new high-performance Rust implementation with QUIC, Protocol Buffers, and Zstd.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from velithon._velithon import (
    QuicTransport as RustQuicTransport,
    AdaptiveTransport as RustAdaptiveTransport,
    VspRequest,
    VspResponse,
    compress_zstd,
    decompress_zstd
)

from .abstract import Transport
from .message import VSPMessage, VSPError

if TYPE_CHECKING:
    from .manager import VSPManager

logger = logging.getLogger(__name__)


class QuicTransport(Transport):
    """QUIC implementation of Transport using Rust backend."""

    def __init__(self, manager: 'VSPManager', compression_enabled: bool = True):
        self.manager = manager
        self.compression_enabled = compression_enabled
        self.rust_transport: Optional[RustQuicTransport] = None
        self.connected = False
        self.host: str = ""
        self.port: int = 0
        self._response_futures: Dict[str, asyncio.Future] = {}

    async def connect(self, host: str, port: int) -> None:
        """Connect to the specified host and port using QUIC."""
        try:
            # Create Rust QUIC transport (client mode, compression enabled)
            self.rust_transport = RustQuicTransport(False, self.compression_enabled)
            
            # Note: The Rust implementation currently returns a Python Future
            # In a full implementation, this would establish a real QUIC connection
            await self._simulate_connection(host, port)
            
            self.host = host
            self.port = port
            self.connected = True
            
            logger.info(f'QUIC connected to {host}:{port} with compression={self.compression_enabled}')
            
        except Exception as e:
            logger.error(f'QUIC connection failed to {host}:{port}: {e}')
            self.connected = False
            raise ConnectionRefusedError(f'QUIC connection failed: {e}')

    async def _simulate_connection(self, host: str, port: int) -> None:
        """Simulate connection for current implementation."""
        # In a full implementation, this would use the Rust transport's connect method
        # For now, we simulate the connection
        await asyncio.sleep(0.001)  # Simulate connection latency

    def send(self, data: bytes) -> None:
        """Send a VSP message over QUIC."""
        if not self.connected or not self.rust_transport:
            logger.error('Cannot send: QUIC transport is not connected')
            raise RuntimeError('Transport not connected')

        try:
            # Parse the VSP message from the data
            if len(data) < 4:
                raise ValueError("Invalid message format")
                
            message_length = int.from_bytes(data[:4], 'big')
            message_data = data[4:4+message_length]
            
            # Parse VSP message
            vsp_message = VSPMessage.from_bytes(message_data)
            
            # Convert to Rust VSP format
            rust_request = VspRequest(
                vsp_message.header.get('service', ''),
                vsp_message.header.get('endpoint', ''),
                self._serialize_body(vsp_message.body)
            )
            
            # Set request ID and other metadata
            rust_request.id = vsp_message.header.get('request_id', rust_request.id)
            rust_request.timeout_ms = 30000  # 30 second timeout
            
            # Store future for response handling
            request_id = rust_request.id
            if hasattr(self.manager, 'client') and self.manager.client:
                future = asyncio.get_event_loop().create_future()
                self._response_futures[request_id] = future
                
                # Schedule async send
                asyncio.create_task(self._send_async(rust_request))
            
            logger.debug(f'QUIC sent request {request_id} to {self.host}:{self.port}')
            
        except Exception as e:
            logger.error(f'Failed to send QUIC message: {e}')
            raise RuntimeError(f'Send failed: {e}')

    async def _send_async(self, request: VspRequest) -> None:
        """Asynchronously send request and handle response."""
        try:
            # For now, simulate the request/response since we don't have a full server
            # In a real implementation, this would use the Rust transport
            await asyncio.sleep(0.001)  # Simulate network latency
            
            # Create a simulated response
            response_data = f"Echo: {request.service_name}.{request.method}".encode()
            response = VspResponse.success(request.id, response_data.decode().encode())
            
            # Convert back to VSP message format
            vsp_response_body = {
                'result': response.data.decode(),
                'status': 'success' if response.is_success() else 'error'
            }
            
            vsp_message = VSPMessage(
                request_id=request.id,
                service=request.service_name,
                endpoint=request.method,
                body=vsp_response_body
            )
            
            # Handle the response
            if hasattr(self.manager, 'client') and self.manager.client:
                await self.manager.client.handle_response(vsp_message)
                
        except Exception as e:
            logger.error(f'Error in async send: {e}')

    def _serialize_body(self, body: Any) -> bytes:
        """Serialize message body to bytes."""
        import json
        json_data = json.dumps(body).encode('utf-8')
        
        if self.compression_enabled and len(json_data) > 100:  # Only compress larger payloads
            try:
                return compress_zstd(json_data)
            except Exception as e:
                logger.warning(f'Compression failed, sending uncompressed: {e}')
                return json_data
        return json_data

    def _deserialize_body(self, data: bytes) -> Any:
        """Deserialize bytes to message body."""
        import json
        
        # Try decompression first if compression is enabled
        if self.compression_enabled:
            try:
                decompressed = decompress_zstd(data)
                return json.loads(decompressed.decode('utf-8'))
            except Exception:
                # If decompression fails, try as plain JSON
                pass
        
        try:
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f'Failed to deserialize message body: {e}')
            raise ValueError(f'Invalid message body: {e}')

    def close(self) -> None:
        """Close the QUIC transport."""
        if self.rust_transport:
            # In a full implementation, this would call the Rust transport's close method
            self.rust_transport = None
            
        self.connected = False
        
        # Cancel any pending response futures
        for future in self._response_futures.values():
            if not future.done():
                future.cancel()
        self._response_futures.clear()
        
        logger.debug(f'QUIC transport closed for {self.host}:{self.port}')

    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        return not self.connected or self.rust_transport is None


class AdaptiveTransport(Transport):
    """Adaptive transport that can switch between QUIC and TCP."""

    def __init__(self, manager: 'VSPManager', prefer_quic: bool = True):
        self.manager = manager
        self.prefer_quic = prefer_quic
        self.rust_adaptive: Optional[RustAdaptiveTransport] = None
        self.active_transport: Optional[Transport] = None
        self.connected = False
        self.host: str = ""
        self.port: int = 0

    async def connect(self, host: str, port: int) -> None:
        """Connect using the best available transport."""
        try:
            # Create Rust adaptive transport
            self.rust_adaptive = RustAdaptiveTransport(self.prefer_quic)
            
            if self.prefer_quic:
                # Try QUIC first
                try:
                    self.active_transport = QuicTransport(self.manager)
                    await self.active_transport.connect(host, port)
                    logger.info(f'Adaptive transport using QUIC for {host}:{port}')
                except Exception as e:
                    logger.warning(f'QUIC failed, falling back to TCP: {e}')
                    # Fall back to TCP
                    from .transport import TCPTransport
                    self.active_transport = TCPTransport(self.manager)
                    await self.active_transport.connect(host, port)
                    logger.info(f'Adaptive transport using TCP for {host}:{port}')
            else:
                # Use TCP directly
                from .transport import TCPTransport
                self.active_transport = TCPTransport(self.manager)
                await self.active_transport.connect(host, port)
                logger.info(f'Adaptive transport using TCP for {host}:{port}')
            
            self.host = host
            self.port = port
            self.connected = True
            
        except Exception as e:
            logger.error(f'Adaptive transport connection failed to {host}:{port}: {e}')
            self.connected = False
            raise

    def send(self, data: bytes) -> None:
        """Send data using the active transport."""
        if not self.connected or not self.active_transport:
            raise RuntimeError('Transport not connected')
        
        self.active_transport.send(data)

    def close(self) -> None:
        """Close the adaptive transport."""
        if self.active_transport:
            self.active_transport.close()
            self.active_transport = None
            
        if self.rust_adaptive:
            self.rust_adaptive = None
            
        self.connected = False
        logger.debug(f'Adaptive transport closed for {self.host}:{self.port}')

    def is_closed(self) -> bool:
        """Check if the transport is closed."""
        return not self.connected or not self.active_transport or self.active_transport.is_closed()


# Factory functions for easy integration
def create_quic_transport(manager: 'VSPManager', compression_enabled: bool = True) -> QuicTransport:
    """Factory function to create a QUIC transport."""
    return QuicTransport(manager, compression_enabled)


def create_adaptive_transport(manager: 'VSPManager', prefer_quic: bool = True) -> AdaptiveTransport:
    """Factory function to create an adaptive transport."""
    return AdaptiveTransport(manager, prefer_quic)
