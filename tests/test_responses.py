"""Tests for response classes including StreamingResponse and FileResponse."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from velithon.datastructures import Protocol
from velithon.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)


@pytest.fixture
def mock_scope():
    """Create a mock scope for testing."""
    return {
        "type": "http",
        "method": "GET",
        "proto": "http",
        "asgi": {"spec_version": "2.4"},
        "headers": [],
        "query_string": b"",
        "path": "/",
    }


@pytest.fixture
def mock_protocol():
    """Create a mock protocol for testing."""
    protocol = MagicMock(spec=Protocol)
    protocol.response_bytes = MagicMock()
    protocol.response_stream = MagicMock()
    
    # Mock the stream transaction
    mock_trx = MagicMock()
    mock_trx.send_bytes = AsyncMock()
    protocol.response_stream.return_value = mock_trx
    
    return protocol


class TestResponse:
    """Test basic Response class."""

    def test_response_init(self):
        """Test Response initialization."""
        response = Response("Hello", status_code=200)
        assert response.status_code == 200
        assert response.body == b"Hello"
        assert response.media_type is None

    def test_response_with_media_type(self):
        """Test Response with media type."""
        response = Response("Hello", media_type="text/plain")
        assert response.media_type == "text/plain"

    @pytest.mark.asyncio
    async def test_response_call(self, mock_scope, mock_protocol):
        """Test Response.__call__."""
        response = Response("Hello")
        await response(mock_scope, mock_protocol)
        
        mock_protocol.response_bytes.assert_called_once()
        args, kwargs = mock_protocol.response_bytes.call_args
        assert args[0] == 200  # status
        assert args[2] == b"Hello"  # body


class TestJSONResponse:
    """Test JSONResponse class."""

    def test_json_response_init(self):
        """Test JSONResponse initialization."""
        data = {"message": "Hello"}
        response = JSONResponse(data)
        assert response.status_code == 200
        assert response.media_type == "application/json"

    def test_json_response_render(self):
        """Test JSONResponse rendering."""
        data = {"message": "Hello", "count": 42}
        response = JSONResponse(data)
        # The body should be valid JSON bytes
        import orjson
        parsed = orjson.loads(response.body)
        assert parsed == data


class TestFileResponse:
    """Test FileResponse class."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello, World! This is test content.")
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def temp_binary_file(self):
        """Create a temporary binary file for testing."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            f.write(b"Binary content: \x00\x01\x02\x03\x04\x05")
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_file_response_init(self, temp_file):
        """Test FileResponse initialization."""
        response = FileResponse(temp_file)
        assert response.path == temp_file
        assert response.status_code == 200
        assert response.filename is None
        assert "application/octet-stream" in response.media_type or "text/plain" in response.media_type

    def test_file_response_with_filename(self, temp_file):
        """Test FileResponse with custom filename."""
        response = FileResponse(temp_file, filename="download.txt")
        assert response.filename == "download.txt"

    def test_file_response_with_media_type(self, temp_file):
        """Test FileResponse with custom media type."""
        response = FileResponse(temp_file, media_type="text/plain")
        assert response.media_type == "text/plain"

    def test_file_response_headers(self, temp_file):
        """Test FileResponse headers."""
        response = FileResponse(temp_file, filename="test.txt")
        
        # Check if content-disposition is set
        headers_dict = dict(response.raw_headers)
        assert "content-disposition" in headers_dict
        assert "attachment; filename=\"test.txt\"" in headers_dict["content-disposition"]

    @pytest.mark.asyncio
    async def test_file_response_existing_file(self, temp_file, mock_scope, mock_protocol):
        """Test FileResponse with existing file."""
        response = FileResponse(temp_file)
        
        await response(mock_scope, mock_protocol)
        
        # Should call response_stream since it's not a HEAD request
        mock_protocol.response_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_response_head_request(self, temp_file, mock_scope, mock_protocol):
        """Test FileResponse with HEAD request."""
        mock_scope["method"] = "HEAD"
        response = FileResponse(temp_file)
        
        await response(mock_scope, mock_protocol)
        
        # Should call response_bytes for HEAD request
        mock_protocol.response_bytes.assert_called_once()
        args, kwargs = mock_protocol.response_bytes.call_args
        assert args[2] == b""  # Empty body for HEAD

    @pytest.mark.asyncio
    async def test_file_response_nonexistent_file(self, mock_scope, mock_protocol):
        """Test FileResponse with non-existent file."""
        response = FileResponse("/nonexistent/file.txt")
        
        await response(mock_scope, mock_protocol)
        
        # Should call response_bytes with 404
        mock_protocol.response_bytes.assert_called_once()
        args, kwargs = mock_protocol.response_bytes.call_args
        assert args[0] == 404  # status

    @pytest.mark.asyncio
    async def test_file_response_directory(self, mock_scope, mock_protocol):
        """Test FileResponse with directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            response = FileResponse(temp_dir)
            
            await response(mock_scope, mock_protocol)
            
            # Should call response_bytes with 404
            mock_protocol.response_bytes.assert_called_once()
            args, kwargs = mock_protocol.response_bytes.call_args
            assert args[0] == 404  # status

    @pytest.mark.asyncio
    async def test_file_response_streaming(self, temp_binary_file, mock_scope, mock_protocol):
        """Test FileResponse file streaming."""
        response = FileResponse(temp_binary_file)
        
        with patch('anyio.open_file') as mock_open:
            mock_file = AsyncMock()
            mock_file.read.side_effect = [
                b"Binary content: ",
                b"\x00\x01\x02\x03\x04\x05",
                b""  # End of file
            ]
            mock_open.return_value.__aenter__.return_value = mock_file
            
            await response(mock_scope, mock_protocol)
            
            # Should have called read multiple times
            assert mock_file.read.call_count >= 2
            
            # Should have called send_bytes for each chunk
            mock_trx = mock_protocol.response_stream.return_value
            assert mock_trx.send_bytes.call_count >= 2

    @pytest.mark.asyncio
    async def test_file_response_io_error(self, temp_file, mock_scope, mock_protocol):
        """Test FileResponse handling IO errors."""
        response = FileResponse(temp_file)
        
        with patch('anyio.open_file') as mock_open:
            mock_open.side_effect = IOError("Permission denied")
            
            with pytest.raises(RuntimeError, match="Error reading file"):
                await response(mock_scope, mock_protocol)


class TestStreamingResponse:
    """Test StreamingResponse class."""

    def test_streaming_response_init_with_async_iterable(self):
        """Test StreamingResponse with async iterable."""
        async def generate():
            yield "chunk1"
            yield "chunk2"
        
        response = StreamingResponse(generate())
        assert response.status_code == 200

    def test_streaming_response_init_with_sync_iterable(self):
        """Test StreamingResponse with sync iterable."""
        def generate():
            yield "chunk1"
            yield "chunk2"
        
        response = StreamingResponse(generate())
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_streaming_response_async_generator(self, mock_scope, mock_protocol):
        """Test StreamingResponse with async generator."""
        async def generate():
            yield "Hello"
            yield " "
            yield "World"
        
        response = StreamingResponse(generate(), media_type="text/plain")
        
        await response(mock_scope, mock_protocol)
        
        # Should call response_stream
        mock_protocol.response_stream.assert_called_once()
        
        # Should send each chunk
        mock_trx = mock_protocol.response_stream.return_value
        assert mock_trx.send_bytes.call_count == 3

    @pytest.mark.asyncio
    async def test_streaming_response_sync_generator(self, mock_scope, mock_protocol):
        """Test StreamingResponse with sync generator."""
        def generate():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        response = StreamingResponse(generate())
        
        await response(mock_scope, mock_protocol)
        
        # Should call response_stream
        mock_protocol.response_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_response_bytes_chunks(self, mock_scope, mock_protocol):
        """Test StreamingResponse with bytes chunks."""
        async def generate():
            yield b"binary"
            yield b"data"
        
        response = StreamingResponse(generate())
        
        await response(mock_scope, mock_protocol)
        
        mock_trx = mock_protocol.response_stream.return_value
        mock_trx.send_bytes.assert_any_call(b"binary")
        mock_trx.send_bytes.assert_any_call(b"data")

    @pytest.mark.asyncio
    async def test_streaming_response_string_encoding(self, mock_scope, mock_protocol):
        """Test StreamingResponse encodes strings to bytes."""
        async def generate():
            yield "Hello"
            yield "World"
        
        response = StreamingResponse(generate())
        
        await response(mock_scope, mock_protocol)
        
        mock_trx = mock_protocol.response_stream.return_value
        # Should encode strings to bytes
        mock_trx.send_bytes.assert_any_call(b"Hello")
        mock_trx.send_bytes.assert_any_call(b"World")

    @pytest.mark.asyncio
    async def test_streaming_response_network_error(self, mock_scope, mock_protocol):
        """Test StreamingResponse handling network errors."""
        async def generate():
            yield "data"
        
        response = StreamingResponse(generate())
        
        # Mock an OSError during streaming
        mock_trx = mock_protocol.response_stream.return_value
        mock_trx.send_bytes.side_effect = OSError("Network error")
        
        with pytest.raises(RuntimeError, match="Network error during streaming"):
            await response(mock_scope, mock_protocol)

    @pytest.mark.asyncio
    async def test_streaming_response_old_asgi_version(self, mock_scope, mock_protocol):
        """Test StreamingResponse with older ASGI version."""
        mock_scope["asgi"]["spec_version"] = "2.0"  # Older version
        
        async def generate():
            yield "data"
        
        response = StreamingResponse(generate())
        
        with patch('anyio.create_task_group') as mock_task_group:
            mock_tg = AsyncMock()
            mock_task_group.return_value.__aenter__.return_value = mock_tg
            
            await response(mock_scope, mock_protocol)
            
            # Should use task group for older ASGI
            mock_task_group.assert_called_once()


class TestRedirectResponse:
    """Test RedirectResponse class."""

    def test_redirect_response_init(self):
        """Test RedirectResponse initialization."""
        response = RedirectResponse("/new-location")
        assert response.status_code == 307
        assert response.body == b""

    def test_redirect_response_custom_status(self):
        """Test RedirectResponse with custom status code."""
        response = RedirectResponse("/new-location", status_code=301)
        assert response.status_code == 301

    def test_redirect_response_headers(self):
        """Test RedirectResponse sets location header."""
        response = RedirectResponse("/new-location")
        headers_dict = dict(response.raw_headers)
        assert "location" in headers_dict
        assert headers_dict["location"] == "/new-location"

    def test_redirect_response_url_encoding(self):
        """Test RedirectResponse URL encoding."""
        response = RedirectResponse("/path with spaces?param=value")
        headers_dict = dict(response.raw_headers)
        # Should properly encode the URL
        assert "location" in headers_dict


class TestResponseIntegration:
    """Integration tests for response classes."""

    @pytest.mark.asyncio
    async def test_background_task_execution(self, mock_scope, mock_protocol):
        """Test that background tasks are executed."""
        task_executed = False
        
        def background_task():
            nonlocal task_executed
            task_executed = True
        
        from velithon.background import BackgroundTask
        bg_task = BackgroundTask(background_task)
        
        response = Response("Hello", background=bg_task)
        await response(mock_scope, mock_protocol)
        
        assert task_executed

    @pytest.mark.asyncio
    async def test_response_headers_merge(self):
        """Test response headers merging."""
        response = Response(
            "Hello",
            headers={"X-Custom": "value"},
            media_type="text/plain"
        )
        
        headers_dict = dict(response.raw_headers)
        assert headers_dict["x-custom"] == "value"
        assert headers_dict["content-type"] == "text/plain; charset=utf-8"
        assert headers_dict["server"] == "velithon"

    @pytest.mark.asyncio
    async def test_file_response_with_range_headers(self, mock_scope, mock_protocol):
        """Test FileResponse with range request support (basic test)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("0123456789" * 100)  # 1000 bytes
            temp_path = Path(f.name)
        
        try:
            response = FileResponse(temp_path)
            await response(mock_scope, mock_protocol)
            
            # Basic test - should call response_stream
            mock_protocol.response_stream.assert_called_once()
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
