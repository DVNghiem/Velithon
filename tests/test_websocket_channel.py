"""Tests for WebSocket Channel functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.websocket.channel import Channel, ChannelMessage, ChannelState
from velithon.websocket.connection import WebSocket


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    websocket = MagicMock(spec=WebSocket)
    websocket.send_json = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()
    websocket.client = ('127.0.0.1', 8000)
    return websocket


@pytest.fixture
def channel():
    """Create a test channel."""
    return Channel('test_channel', max_connections=5)


class TestChannelMessage:
    """Test ChannelMessage class."""

    def test_message_creation(self):
        """Test creating a channel message."""
        message = ChannelMessage('test_event', {'key': 'value'})

        assert message.event == 'test_event'
        assert message.data == {'key': 'value'}
        assert message.sender_id is None
        assert message.message_id is not None
        assert message.timestamp is not None

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = ChannelMessage(
            'test_event',
            {'key': 'value'},
            sender_id='user123',
        )

        data = message.to_dict()

        assert data['event'] == 'test_event'
        assert data['data'] == {'key': 'value'}
        assert data['sender_id'] == 'user123'
        assert 'timestamp' in data
        assert 'message_id' in data

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            'event': 'test_event',
            'data': {'key': 'value'},
            'sender_id': 'user123',
            'timestamp': '2023-01-01T00:00:00',
            'message_id': 'msg123',
        }

        message = ChannelMessage.from_dict(data)

        assert message.event == 'test_event'
        assert message.data == {'key': 'value'}
        assert message.sender_id == 'user123'
        assert message.message_id == 'msg123'


class TestChannel:
    """Test Channel class."""

    def test_channel_creation(self, channel):
        """Test creating a channel."""
        assert channel.name == 'test_channel'
        assert channel.max_connections == 5
        assert channel.state == ChannelState.ACTIVE
        assert channel.connection_count == 0

    def test_channel_properties(self, channel):
        """Test channel properties."""
        stats = channel.stats

        assert 'current_connections' in stats
        assert 'total_connections' in stats
        assert 'messages_sent' in stats
        assert 'state' in stats
        assert stats['state'] == 'active'

    @pytest.mark.asyncio
    async def test_add_connection(self, channel, mock_websocket):
        """Test adding a connection to channel."""
        conn_id = await channel.add_connection(mock_websocket)

        assert conn_id in channel.list_connections()
        assert channel.connection_count == 1
        assert channel.get_connection(conn_id) == mock_websocket

    @pytest.mark.asyncio
    async def test_add_connection_with_metadata(self, channel, mock_websocket):
        """Test adding connection with metadata."""
        metadata = {'user_id': 'user123', 'role': 'member'}
        conn_id = await channel.add_connection(
            mock_websocket,
            metadata=metadata,
        )

        stored_metadata = channel.get_connection_metadata(conn_id)
        assert stored_metadata == metadata

    @pytest.mark.asyncio
    async def test_add_connection_max_limit(self, mock_websocket):
        """Test adding connections up to max limit."""
        channel = Channel('test', max_connections=2)

        # Add first connection
        await channel.add_connection(mock_websocket)
        assert channel.connection_count == 1

        # Add second connection
        mock_websocket2 = MagicMock(spec=WebSocket)
        mock_websocket2.client = ('127.0.0.1', 8001)
        await channel.add_connection(mock_websocket2)
        assert channel.connection_count == 2

        # Try to add third connection (should fail)
        mock_websocket3 = MagicMock(spec=WebSocket)
        mock_websocket3.client = ('127.0.0.1', 8002)
        with pytest.raises(ValueError, match='Channel .* is full'):
            await channel.add_connection(mock_websocket3)

    @pytest.mark.asyncio
    async def test_remove_connection(self, channel, mock_websocket):
        """Test removing a connection."""
        conn_id = await channel.add_connection(mock_websocket)
        assert channel.connection_count == 1

        removed = await channel.remove_connection(conn_id)
        assert removed is True
        assert channel.connection_count == 0
        assert conn_id not in channel.list_connections()

    @pytest.mark.asyncio
    async def test_remove_nonexistent_connection(self, channel):
        """Test removing a connection that doesn't exist."""
        removed = await channel.remove_connection('nonexistent')
        assert removed is False

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, channel, mock_websocket):
        """Test subscription management."""
        conn_id = await channel.add_connection(mock_websocket)

        # Subscribe to event
        subscribed = await channel.subscribe(conn_id, 'test_event')
        assert subscribed is True
        assert 'test_event' in channel.get_subscriptions(conn_id)

        # Unsubscribe from event
        unsubscribed = await channel.unsubscribe(conn_id, 'test_event')
        assert unsubscribed is True
        assert 'test_event' not in channel.get_subscriptions(conn_id)

    @pytest.mark.asyncio
    async def test_send_to_connection(self, channel, mock_websocket):
        """Test sending message to specific connection."""
        conn_id = await channel.add_connection(mock_websocket)

        # Send text message
        sent = await channel.send_to_connection(conn_id, 'Hello')
        assert sent is True
        mock_websocket.send_text.assert_called_once_with('Hello')

        # Send JSON message
        mock_websocket.send_json.reset_mock()
        message_data = {'type': 'test', 'data': 'value'}
        sent = await channel.send_to_connection(conn_id, message_data)
        assert sent is True
        mock_websocket.send_json.assert_called_once_with(message_data)

    @pytest.mark.asyncio
    async def test_broadcast(self, channel):
        """Test broadcasting message to all connections."""
        # Add multiple connections
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws1.send_text = AsyncMock()
        mock_ws1.client = ('127.0.0.1', 8001)

        mock_ws2 = MagicMock(spec=WebSocket)
        mock_ws2.send_text = AsyncMock()
        mock_ws2.client = ('127.0.0.1', 8002)

        await channel.add_connection(mock_ws1)
        await channel.add_connection(mock_ws2)

        # Broadcast message
        count = await channel.broadcast('Hello everyone')
        assert count == 2

        mock_ws1.send_text.assert_called_once_with('Hello everyone')
        mock_ws2.send_text.assert_called_once_with('Hello everyone')

    @pytest.mark.asyncio
    async def test_broadcast_with_exclusions(self, channel):
        """Test broadcasting with exclusions."""
        mock_ws1 = MagicMock(spec=WebSocket)
        mock_ws1.send_text = AsyncMock()
        mock_ws1.client = ('127.0.0.1', 8001)

        mock_ws2 = MagicMock(spec=WebSocket)
        mock_ws2.send_text = AsyncMock()
        mock_ws2.client = ('127.0.0.1', 8002)

        conn1 = await channel.add_connection(mock_ws1)
        await channel.add_connection(mock_ws2)

        # Broadcast excluding conn1
        count = await channel.broadcast('Hello', exclude={conn1})
        assert count == 1

        mock_ws1.send_text.assert_not_called()
        mock_ws2.send_text.assert_called_once_with('Hello')

    @pytest.mark.asyncio
    async def test_emit_event(self, channel, mock_websocket):
        """Test event emission to subscribed connections."""
        conn_id = await channel.add_connection(mock_websocket)
        await channel.subscribe(conn_id, 'test_event')

        count = await channel.emit_event('test_event', {'message': 'Hello'})
        assert count == 1

        # Check that message was sent
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['event'] == 'test_event'
        assert call_args['data'] == {'message': 'Hello'}

    @pytest.mark.asyncio
    async def test_emit_event_no_subscribers(self, channel, mock_websocket):
        """Test event emission with no subscribers."""
        await channel.add_connection(mock_websocket)
        # Don't subscribe to the event

        count = await channel.emit_event('test_event', {'message': 'Hello'})
        assert count == 0
        mock_websocket.send_json.assert_not_called()

    def test_event_handlers(self, channel):
        """Test event handler registration."""
        handler_calls = []

        def test_handler(channel_obj, event, data):
            handler_calls.append((event, data))

        # Register handler
        channel.on('test_event', test_handler)

        # Remove handler
        channel.off('test_event', test_handler)

        # Remove all handlers for event
        channel.on('test_event', test_handler)
        channel.off('test_event')

    def test_message_filters(self, channel):
        """Test message filtering."""

        # Add filter that blocks messages containing "spam"
        def spam_filter(message):
            return 'spam' not in str(message.data).lower()

        channel.add_message_filter(spam_filter)

        # Test that filter is applied
        test_message = ChannelMessage('test', {'text': 'this is spam'})
        assert not channel._should_deliver_message(test_message)

        clean_message = ChannelMessage('test', {'text': 'this is clean'})
        assert channel._should_deliver_message(clean_message)

    def test_message_history(self, channel):
        """Test message history buffer."""
        # Test getting empty history
        history = channel.get_message_history()
        assert len(history) == 0

        # Add some messages to buffer
        for i in range(5):
            message = ChannelMessage(f'event_{i}', {'count': i})
            channel._add_to_buffer(message)

        # Test getting full history
        history = channel.get_message_history()
        assert len(history) == 5

        # Test getting limited history
        history = channel.get_message_history(limit=3)
        assert len(history) == 3
        assert history[0].data['count'] == 2  # Last 3 messages

    @pytest.mark.asyncio
    async def test_channel_close(self, channel, mock_websocket):
        """Test closing a channel."""
        await channel.add_connection(mock_websocket)
        assert channel.state == ChannelState.ACTIVE

        await channel.close()

        assert channel.state == ChannelState.CLOSED
        assert channel.connection_count == 0
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_cleanup(self):
        """Test auto cleanup when no connections remain."""
        channel = Channel('test', auto_cleanup=True)
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client = ('127.0.0.1', 8000)

        conn_id = await channel.add_connection(mock_websocket)
        assert channel.state == ChannelState.ACTIVE

        # Remove the connection - should trigger auto cleanup
        await channel.remove_connection(conn_id)
        assert channel.state == ChannelState.CLOSED

    def test_channel_repr(self, channel):
        """Test channel string representation."""
        repr_str = repr(channel)
        assert 'test_channel' in repr_str
        assert 'connections=0' in repr_str
        assert 'state=active' in repr_str
