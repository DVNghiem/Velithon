"""Tests for SSEResponse class."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.datastructures import Protocol
from velithon.responses import SSEResponse


@pytest.fixture
def mock_scope():
    """Create a mock scope for testing."""
    return {
        'type': 'http',
        'method': 'GET',
        'asgi': {'spec_version': '2.4'},
    }


@pytest.fixture
def mock_protocol():
    """Create a mock protocol for testing."""
    protocol = MagicMock(spec=Protocol)
    mock_trx = AsyncMock()
    protocol.response_stream.return_value = mock_trx
    return protocol


class TestSSEResponse:
    """Test SSEResponse class."""

    def test_sse_response_init_basic(self):
        """Test basic SSEResponse initialization."""

        async def generate():
            yield 'Hello'
            yield 'World'

        response = SSEResponse(generate())
        assert response.status_code == 200
        assert response.media_type == 'text/event-stream'
        headers_dict = dict(response.raw_headers)
        assert 'cache-control' in headers_dict

    def test_sse_response_init_with_headers(self):
        """Test SSEResponse initialization with custom headers."""

        async def generate():
            yield 'data'

        custom_headers = {'X-Custom': 'value'}
        response = SSEResponse(generate(), headers=custom_headers)

        headers_dict = dict(response.raw_headers)
        assert headers_dict['cache-control'] == 'no-cache'
        assert headers_dict['connection'] == 'keep-alive'
        assert headers_dict['x-custom'] == 'value'

    def test_sse_response_init_with_ping_interval(self):
        """Test SSEResponse initialization with ping interval."""

        async def generate():
            yield 'data'

        response = SSEResponse(generate(), ping_interval=30)
        assert response.ping_interval == 30

    def test_format_sse_event_string(self):
        """Test formatting string data as SSE event."""

        async def generate():
            yield 'test'

        response = SSEResponse(generate())
        formatted = response._format_sse_event('Hello World')
        assert formatted == 'data: Hello World\n\n'

    def test_format_sse_event_dict_with_data(self):
        """Test formatting dict with data field as SSE event."""

        async def generate():
            yield {'data': 'Hello'}

        response = SSEResponse(generate())
        formatted = response._format_sse_event({'data': 'Hello'})
        assert formatted == 'data: Hello\n\n'

    def test_format_sse_event_dict_with_all_fields(self):
        """Test formatting dict with all SSE fields."""

        async def generate():
            yield {'data': 'Hello', 'event': 'message', 'id': '123', 'retry': 5000}

        response = SSEResponse(generate())
        event_data = {'data': 'Hello', 'event': 'message', 'id': '123', 'retry': 5000}
        formatted = response._format_sse_event(event_data)

        assert 'data: Hello' in formatted
        assert 'event: message' in formatted
        assert 'id: 123' in formatted
        assert 'retry: 5000' in formatted
        assert formatted.endswith('\n\n')

    def test_format_sse_event_dict_as_json_data(self):
        """Test formatting regular dict as JSON data."""

        async def generate():
            yield {'name': 'John', 'age': 30}

        response = SSEResponse(generate())
        formatted = response._format_sse_event({'name': 'John', 'age': 30})

        # Should serialize the entire dict as JSON data
        assert (
            'data: {"name":"John","age":30}' in formatted
            or 'data: {"age":30,"name":"John"}' in formatted
        )
        assert formatted.endswith('\n\n')

    def test_format_sse_event_dict_with_non_string_data(self):
        """Test formatting dict with non-string data field."""

        async def generate():
            yield {'data': {'nested': 'value'}}

        response = SSEResponse(generate())
        formatted = response._format_sse_event({'data': {'nested': 'value'}})

        assert 'data: {"nested":"value"}' in formatted
        assert formatted.endswith('\n\n')

    def test_format_sse_event_object(self):
        """Test formatting arbitrary object as SSE event."""

        async def generate():
            yield [1, 2, 3]

        response = SSEResponse(generate())
        formatted = response._format_sse_event([1, 2, 3])
        assert formatted == 'data: [1,2,3]\n\n'

    def test_format_ping_event(self):
        """Test formatting ping event."""

        async def generate():
            yield 'data'

        response = SSEResponse(generate())
        ping = response._format_ping_event()
        assert ping == ': ping\n\n'

    @pytest.mark.asyncio
    async def test_sse_response_async_generator(self, mock_scope, mock_protocol):
        """Test SSEResponse with async generator."""

        async def generate():
            yield 'Hello'
            yield {'data': 'World', 'event': 'message'}
            yield {'name': 'test'}

        response = SSEResponse(generate())

        await response(mock_scope, mock_protocol)

        # Should call response_stream
        mock_protocol.response_stream.assert_called_once()

        # Should send formatted SSE events
        mock_trx = mock_protocol.response_stream.return_value
        assert mock_trx.send_bytes.call_count == 3

        # Check the calls
        calls = mock_trx.send_bytes.call_args_list
        assert calls[0][0][0] == b'data: Hello\n\n'
        assert calls[1][0][0] == b'data: World\nevent: message\n\n'
        # Third call should be JSON serialized
        assert b'data: {"name":"test"}' in calls[2][0][0]

    @pytest.mark.asyncio
    async def test_sse_response_sync_generator(self, mock_scope, mock_protocol):
        """Test SSEResponse with sync generator."""

        def generate():
            yield 'chunk1'
            yield 'chunk2'

        response = SSEResponse(generate())

        await response(mock_scope, mock_protocol)

        # Should call response_stream
        mock_protocol.response_stream.assert_called_once()

        mock_trx = mock_protocol.response_stream.return_value
        assert mock_trx.send_bytes.call_count == 2

    @pytest.mark.asyncio
    async def test_sse_response_with_ping_interval(self, mock_scope, mock_protocol):
        """Test SSEResponse with ping interval."""
        ping_sent = False

        async def generate():
            nonlocal ping_sent
            yield 'data1'
            # Wait a bit to let ping task run
            await asyncio.sleep(0.1)
            ping_sent = True
            yield 'data2'

        response = SSEResponse(generate(), ping_interval=0.05)  # 50ms ping interval

        await response(mock_scope, mock_protocol)

        mock_trx = mock_protocol.response_stream.return_value
        # Should have sent data + possible ping
        assert mock_trx.send_bytes.call_count >= 2

    @pytest.mark.asyncio
    async def test_sse_response_network_error(self, mock_scope, mock_protocol):
        """Test SSEResponse handling network errors."""

        async def generate():
            yield 'data'

        response = SSEResponse(generate())

        # Mock an OSError during streaming
        mock_trx = mock_protocol.response_stream.return_value
        mock_trx.send_bytes.side_effect = OSError('Network error')

        with pytest.raises(RuntimeError, match='Network error during SSE streaming'):
            await response(mock_scope, mock_protocol)

    @pytest.mark.asyncio
    async def test_sse_response_rsgi_protocol(self, mock_scope, mock_protocol):
        """Test SSEResponse with RSGI protocol."""

        async def generate():
            yield 'data'

        response = SSEResponse(generate())

        # Should call response_stream directly in RSGI
        await response(mock_scope, mock_protocol)

        mock_protocol.response_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_sse_response_empty_generator(self, mock_scope, mock_protocol):
        """Test SSEResponse with empty generator."""

        async def generate():
            return
            yield  # Never reached

        response = SSEResponse(generate())

        await response(mock_scope, mock_protocol)

        mock_protocol.response_stream.assert_called_once()
        mock_trx = mock_protocol.response_stream.return_value
        # Should not send any data
        mock_trx.send_bytes.assert_not_called()

    @pytest.mark.asyncio
    async def test_sse_response_unicode_content(self, mock_scope, mock_protocol):
        """Test SSEResponse with unicode content."""

        async def generate():
            yield 'Hello 世界'
            yield {'data': 'Héllo wörld'}

        response = SSEResponse(generate())

        await response(mock_scope, mock_protocol)

        mock_trx = mock_protocol.response_stream.return_value
        calls = mock_trx.send_bytes.call_args_list

        # Should properly encode unicode
        assert calls[0][0][0] == b'data: Hello \xe4\xb8\x96\xe7\x95\x8c\n\n'
        assert b'data: H\xc3\xa9llo w\xc3\xb6rld\n\n' in calls[1][0][0]

    def test_sse_response_custom_status_code(self):
        """Test SSEResponse with custom status code."""

        async def generate():
            yield 'data'

        response = SSEResponse(generate(), status_code=201)
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_sse_response_with_background_task(self, mock_scope, mock_protocol):
        """Test SSEResponse with background task."""
        task_executed = False

        def background_task():
            nonlocal task_executed
            task_executed = True

        async def generate():
            yield 'data'

        from velithon.background import BackgroundTask

        bg_task = BackgroundTask(background_task)
        response = SSEResponse(generate(), background=bg_task)

        await response(mock_scope, mock_protocol)

        # Background task should be executed
        assert task_executed

    @pytest.mark.asyncio
    async def test_sse_response_generator_exception(self, mock_scope, mock_protocol):
        """Test SSEResponse when generator raises exception."""

        async def generate():
            yield 'data1'
            raise ValueError('Generator error')

        response = SSEResponse(generate())

        with pytest.raises(ValueError, match='Generator error'):
            await response(mock_scope, mock_protocol)


if __name__ == '__main__':
    pytest.main([__file__])
