import gzip
import io
import typing
from enum import Enum

from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import BaseHTTPMiddleware


class CompressionLevel(Enum):
    """Compression levels for gzip compression."""

    FASTEST = 1
    BALANCED = 6
    BEST = 9


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that compresses HTTP responses using gzip compression.
    
    This middleware automatically compresses responses when:
    - The client accepts gzip encoding (via Accept-Encoding header)
    - The response content type is compressible
    - The response body is large enough to benefit from compression
    
    Args:
        app: The ASGI application to wrap
        minimum_size: Minimum response size in bytes to enable compression (default: 500)
        compression_level: Compression level to use (default: CompressionLevel.BALANCED)
        compressible_types: Set of content types that should be compressed
    """
    
    # Default content types that benefit from compression
    DEFAULT_COMPRESSIBLE_TYPES = {
        "text/html",
        "text/plain", 
        "text/css",
        "text/javascript",
        "text/xml",
        "application/json",
        "application/javascript",
        "application/xml",
        "application/rss+xml",
        "application/atom+xml",
        "image/svg+xml",
    }
    
    def __init__(
        self,
        app: typing.Any,
        minimum_size: int = 500,
        compression_level: CompressionLevel = CompressionLevel.BALANCED,
        compressible_types: typing.Optional[typing.Set[str]] = None,
    ) -> None:
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level.value
        self.compressible_types = compressible_types or self.DEFAULT_COMPRESSIBLE_TYPES
        
    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        # Check if client accepts gzip encoding
        accept_encoding = scope.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await self.app(scope, protocol)
            
        # Wrap the protocol to capture response data
        wrapped_protocol = CompressionProtocol(protocol, self)
        await self.app(scope, wrapped_protocol)
        
    def should_compress(self, content_type: str, content_length: int) -> bool:
        """
        Determine if the response should be compressed based on content type and size.
        
        Args:
            content_type: The response content type
            content_length: The response content length in bytes
            
        Returns:
            True if the response should be compressed, False otherwise
        """
        if content_length < self.minimum_size:
            return False
            
        # Extract the main content type (ignore charset and other parameters)
        main_content_type = content_type.split(";")[0].strip().lower()
        return main_content_type in self.compressible_types
        

class CompressionProtocol:
    """
    Protocol wrapper that handles response compression.
    """
    
    def __init__(self, protocol: Protocol, middleware: CompressionMiddleware):
        self.protocol = protocol
        self.middleware = middleware
        self._response_started = False
        self._headers_sent = False
        self._content_type = ""
        self._content_length = 0
        self._body_parts: typing.List[bytes] = []
        
    def __getattr__(self, name: str) -> typing.Any:
        """Delegate all other attributes to the wrapped protocol."""
        return getattr(self.protocol, name)
        
    async def response_start(
        self, 
        status: int, 
        headers: typing.List[typing.Tuple[str, str]]
    ) -> None:
        """Handle response start, examining headers to determine if compression should be applied."""
        self._response_started = True
        
        # Convert headers to a more manageable format
        headers_dict = {key.lower(): value for key, value in headers}
        
        # Get content type and length
        self._content_type = headers_dict.get("content-type", "")
        content_length_str = headers_dict.get("content-length", "0")
        
        try:
            self._content_length = int(content_length_str)
        except (ValueError, TypeError):
            self._content_length = 0
            
        # Store original headers for potential modification
        self._original_headers = headers
        self._status = status
        
    async def response_body(
        self, 
        body: bytes, 
        more_body: bool = False
    ) -> None:
        """Handle response body, collecting data for potential compression."""
        if not self._response_started:
            # If response_start wasn't called, just pass through
            return await self.protocol.response_body(body, more_body)
            
        # Collect body parts
        if body:
            self._body_parts.append(body)
            
        # If this is the last chunk, decide whether to compress
        if not more_body:
            await self._finalize_response()
            
    async def _finalize_response(self) -> None:
        """Finalize the response, applying compression if appropriate."""
        # Combine all body parts
        full_body = b"".join(self._body_parts)
        actual_length = len(full_body)
        
        # Determine if we should compress
        should_compress = self.middleware.should_compress(self._content_type, actual_length)
        
        if should_compress and full_body:
            # Compress the content
            compressed_body = self._compress_content(full_body)
            
            # Update headers for compressed response
            headers = self._update_headers_for_compression(compressed_body)
            
            # Send compressed response
            await self.protocol.response_start(self._status, headers)
            await self.protocol.response_body(compressed_body, more_body=False)
        else:
            # Send original response
            await self.protocol.response_start(self._status, self._original_headers)
            await self.protocol.response_body(full_body, more_body=False)
            
    def _compress_content(self, content: bytes) -> bytes:
        """Compress content using gzip."""
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=self.middleware.compression_level) as gz_file:
            gz_file.write(content)
        return buffer.getvalue()
        
    def _update_headers_for_compression(self, compressed_body: bytes) -> typing.List[typing.Tuple[str, str]]:
        """Update headers for compressed response."""
        updated_headers = []
        content_length_updated = False
        
        for key, value in self._original_headers:
            key_lower = key.lower()
            
            if key_lower == "content-length":
                # Update content length to compressed size
                updated_headers.append((key, str(len(compressed_body))))
                content_length_updated = True
            elif key_lower == "content-encoding":
                # Don't add duplicate content-encoding headers
                continue
            else:
                updated_headers.append((key, value))
                
        # Add compression headers
        updated_headers.append(("content-encoding", "gzip"))
        updated_headers.append(("vary", "Accept-Encoding"))
        
        # Add content-length if it wasn't present in original headers
        if not content_length_updated:
            updated_headers.append(("content-length", str(len(compressed_body))))
            
        return updated_headers
