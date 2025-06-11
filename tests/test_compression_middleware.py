import gzip
from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.datastructures import Headers
from velithon.middleware.compression import CompressionLevel, CompressionMiddleware


@pytest.fixture
def mock_app():
    """Create a mock ASGI application."""
    return AsyncMock()


@pytest.fixture
def compression_middleware(mock_app):
    """Create a CompressionMiddleware instance with default settings."""
    return CompressionMiddleware(mock_app)


@pytest.fixture
def mock_scope():
    """Create a mock HTTP scope."""
    scope = MagicMock()
    scope.proto = "http"
    scope.headers = Headers([])
    return scope


@pytest.fixture
def mock_protocol():
    """Create a mock protocol."""
    protocol = MagicMock()
    protocol.response_start = AsyncMock()
    protocol.response_body = AsyncMock()
    return protocol


class TestCompressionMiddleware:
    """Test cases for CompressionMiddleware."""
    
    @pytest.mark.asyncio
    async def test_non_http_requests_passthrough(self, compression_middleware, mock_app, mock_protocol):
        """Test that non-HTTP requests pass through without compression."""
        scope = MagicMock()
        scope.proto = "websocket"
        
        await compression_middleware(scope, mock_protocol)
        
        mock_app.assert_called_once_with(scope, mock_protocol)
    
    @pytest.mark.asyncio
    async def test_no_gzip_support_passthrough(self, compression_middleware, mock_app, mock_scope, mock_protocol):
        """Test that requests without gzip support pass through without compression."""
        mock_scope.headers = Headers([("accept-encoding", "deflate, br")])
        
        await compression_middleware(mock_scope, mock_protocol)
        
        mock_app.assert_called_once_with(mock_scope, mock_protocol)
    
    @pytest.mark.asyncio
    async def test_gzip_support_wraps_protocol(self, compression_middleware, mock_app, mock_scope, mock_protocol):
        """Test that requests with gzip support get wrapped protocol."""
        mock_scope.headers = Headers([("accept-encoding", "gzip, deflate")])
        
        await compression_middleware(mock_scope, mock_protocol)
        
        # Should call app with wrapped protocol
        mock_app.assert_called_once()
        call_args = mock_app.call_args
        assert call_args[0][0] == mock_scope
        # The protocol should be wrapped
        wrapped_protocol = call_args[0][1]
        assert wrapped_protocol != mock_protocol
        assert hasattr(wrapped_protocol, 'protocol')
    
    def test_should_compress_content_type(self, compression_middleware):
        """Test compression decision based on content type."""
        # Should compress JSON
        assert compression_middleware.should_compress("application/json", 1000)
        
        # Should compress HTML
        assert compression_middleware.should_compress("text/html; charset=utf-8", 1000)
        
        # Should not compress images
        assert not compression_middleware.should_compress("image/jpeg", 1000)
        
        # Should not compress already compressed content
        assert not compression_middleware.should_compress("application/gzip", 1000)
    
    def test_should_compress_size_threshold(self, compression_middleware):
        """Test compression decision based on content size."""
        # Should not compress small content
        assert not compression_middleware.should_compress("application/json", 100)
        
        # Should compress large content
        assert compression_middleware.should_compress("application/json", 1000)
    
    def test_custom_compressible_types(self, mock_app):
        """Test custom compressible types configuration."""
        custom_types = {"application/custom", "text/special"}
        middleware = CompressionMiddleware(mock_app, compressible_types=custom_types)
        
        # Should compress custom types
        assert middleware.should_compress("application/custom", 1000)
        assert middleware.should_compress("text/special", 1000)
        
        # Should not compress default types
        assert not middleware.should_compress("application/json", 1000)
    
    def test_custom_minimum_size(self, mock_app):
        """Test custom minimum size configuration."""
        middleware = CompressionMiddleware(mock_app, minimum_size=1000)
        
        # Should not compress below threshold
        assert not middleware.should_compress("application/json", 500)
        
        # Should compress above threshold
        assert middleware.should_compress("application/json", 1500)
    
    def test_compression_levels(self, mock_app):
        """Test different compression levels."""
        fast_middleware = CompressionMiddleware(mock_app, compression_level=CompressionLevel.FASTEST)
        balanced_middleware = CompressionMiddleware(mock_app, compression_level=CompressionLevel.BALANCED)
        best_middleware = CompressionMiddleware(mock_app, compression_level=CompressionLevel.BEST)
        
        assert fast_middleware.compression_level == 1
        assert balanced_middleware.compression_level == 6
        assert best_middleware.compression_level == 9


class TestCompressionProtocol:
    """Test cases for CompressionProtocol."""
    
    @pytest.fixture
    def compression_protocol(self, compression_middleware, mock_protocol):
        """Create a CompressionProtocol instance."""
        from velithon.middleware.compression import CompressionProtocol
        return CompressionProtocol(mock_protocol, compression_middleware)
    
    @pytest.mark.asyncio
    async def test_response_start_stores_headers(self, compression_protocol):
        """Test that response_start properly stores headers and status."""
        headers = [
            ("content-type", "application/json"),
            ("content-length", "1000"),
        ]
        
        await compression_protocol.response_start(200, headers)
        
        assert compression_protocol._response_started
        assert compression_protocol._status == 200
        assert compression_protocol._content_type == "application/json"
        assert compression_protocol._content_length == 1000
    
    @pytest.mark.asyncio
    async def test_response_body_collects_data(self, compression_protocol):
        """Test that response_body collects body data."""
        # Simulate response start
        await compression_protocol.response_start(200, [("content-type", "application/json")])
        
        # Send body in chunks
        await compression_protocol.response_body(b"Hello, ", more_body=True)
        await compression_protocol.response_body(b"World!", more_body=False)
        
        # Check that data was collected
        assert len(compression_protocol._body_parts) == 2
        assert b"".join(compression_protocol._body_parts) == b"Hello, World!"
    
    @pytest.mark.asyncio
    async def test_compression_applied_for_compressible_content(self, compression_protocol, mock_protocol):
        """Test that compression is applied for compressible content."""
        # Large JSON content that should be compressed
        large_json = b'{"message": "' + b"x" * 1000 + b'"}'
        
        headers = [
            ("content-type", "application/json"),
            ("content-length", str(len(large_json))),
        ]
        
        await compression_protocol.response_start(200, headers)
        await compression_protocol.response_body(large_json, more_body=False)
        
        # Verify that response_start and response_body were called on the wrapped protocol
        mock_protocol.response_start.assert_called_once()
        mock_protocol.response_body.assert_called_once()
        
        # Check that compression headers were added
        call_args = mock_protocol.response_start.call_args
        response_headers = dict(call_args[0][1])
        
        assert "content-encoding" in response_headers
        assert response_headers["content-encoding"] == "gzip"
        assert "vary" in response_headers
        assert response_headers["vary"] == "Accept-Encoding"
    
    @pytest.mark.asyncio
    async def test_no_compression_for_small_content(self, compression_protocol, mock_protocol):
        """Test that small content is not compressed."""
        small_json = b'{"msg": "hi"}'
        
        headers = [
            ("content-type", "application/json"),
            ("content-length", str(len(small_json))),
        ]
        
        await compression_protocol.response_start(200, headers)
        await compression_protocol.response_body(small_json, more_body=False)
        
        # Check that original headers were preserved (no compression)
        call_args = mock_protocol.response_start.call_args
        response_headers = dict(call_args[0][1])
        
        assert "content-encoding" not in response_headers
    
    @pytest.mark.asyncio
    async def test_no_compression_for_non_compressible_content(self, compression_protocol, mock_protocol):
        """Test that non-compressible content is not compressed."""
        large_image = b"x" * 2000  # Large but non-compressible content
        
        headers = [
            ("content-type", "image/jpeg"),
            ("content-length", str(len(large_image))),
        ]
        
        await compression_protocol.response_start(200, headers)
        await compression_protocol.response_body(large_image, more_body=False)
        
        # Check that original headers were preserved (no compression)
        call_args = mock_protocol.response_start.call_args
        response_headers = dict(call_args[0][1])
        
        assert "content-encoding" not in response_headers
    
    def test_compress_content_produces_valid_gzip(self, compression_protocol):
        """Test that _compress_content produces valid gzip data."""
        original_content = b"Hello, World!" * 100  # Repeat to make it compressible
        
        compressed = compression_protocol._compress_content(original_content)
        
        # Verify it's valid gzip by decompressing
        decompressed = gzip.decompress(compressed)
        assert decompressed == original_content
        
        # Verify compression actually reduced size
        assert len(compressed) < len(original_content)
    
    def test_update_headers_for_compression(self, compression_protocol):
        """Test that headers are correctly updated for compression."""
        compression_protocol._original_headers = [
            ("content-type", "application/json"),
            ("content-length", "1000"),
            ("cache-control", "no-cache"),
        ]
        
        compressed_body = b"compressed data"
        
        updated_headers = compression_protocol._update_headers_for_compression(compressed_body)
        headers_dict = dict(updated_headers)
        
        # Check that content-length was updated
        assert headers_dict["content-length"] == str(len(compressed_body))
        
        # Check that compression headers were added
        assert headers_dict["content-encoding"] == "gzip"
        assert headers_dict["vary"] == "Accept-Encoding"
        
        # Check that other headers were preserved
        assert headers_dict["content-type"] == "application/json"
        assert headers_dict["cache-control"] == "no-cache"
    
    @pytest.mark.asyncio
    async def test_getattr_delegation(self, compression_protocol, mock_protocol):
        """Test that unknown attributes are delegated to the wrapped protocol."""
        # Set an arbitrary attribute on the mock protocol
        mock_protocol.custom_method = MagicMock(return_value="test")
        
        # Access it through the compression protocol
        result = compression_protocol.custom_method()
        
        assert result == "test"
        mock_protocol.custom_method.assert_called_once()


@pytest.mark.asyncio
async def test_integration_with_real_content():
    """Integration test with real content compression."""
    # Create a simple ASGI app that returns JSON
    async def simple_app(scope, protocol):
        headers = [
            ("content-type", "application/json"),
        ]
        await protocol.response_start(200, headers)
        
        # Send large JSON content
        large_json = b'{"data": "' + b"x" * 1000 + b'"}'
        await protocol.response_body(large_json, more_body=False)
    
    # Create compression middleware
    middleware = CompressionMiddleware(simple_app, minimum_size=100)
    
    # Mock scope with gzip support
    scope = MagicMock()
    scope.proto = "http"
    scope.headers = Headers([("accept-encoding", "gzip, deflate")])
    
    # Mock protocol to capture response
    captured_headers = None
    captured_body = None
    
    async def mock_response_start(status, headers):
        nonlocal captured_headers
        captured_headers = headers
    
    async def mock_response_body(body, more_body=False):
        nonlocal captured_body
        captured_body = body
    
    protocol = MagicMock()
    protocol.response_start = mock_response_start
    protocol.response_body = mock_response_body
    
    # Run the middleware
    await middleware(scope, protocol)
    
    # Verify compression was applied
    headers_dict = dict(captured_headers)
    assert headers_dict["content-encoding"] == "gzip"
    
    # Verify the body was compressed and is valid gzip
    decompressed = gzip.decompress(captured_body)
    assert b'"data"' in decompressed
    assert len(captured_body) < len(decompressed)  # Compression reduced size
