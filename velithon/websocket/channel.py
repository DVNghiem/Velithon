"""WebSocket Channel implementation for Velithon.

Channels provide a communication abstraction over WebSocket connections,
allowing for event-based messaging and subscription patterns.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from velithon.websocket.connection import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ChannelState(Enum):
    """Channel state enumeration."""

    CREATED = 'created'
    ACTIVE = 'active'
    CLOSED = 'closed'
    ERROR = 'error'


class ChannelMessage:
    """Represents a message in a channel."""

    def __init__(
        self,
        event: str,
        data: Any = None,
        timestamp: datetime | None = None,
        sender_id: str | None = None,
        message_id: str | None = None,
    ):
        """Initialize a channel message.

        Args:
            event: Event name
            data: Message data
            timestamp: Message timestamp (defaults to current time)
            sender_id: ID of the sender
            message_id: Unique message ID (auto-generated if not provided)

        """
        self.event = event
        self.data = data
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.sender_id = sender_id
        self.message_id = message_id or self._generate_message_id()

    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        import uuid

        return str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'event': self.event,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'sender_id': self.sender_id,
            'message_id': self.message_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelMessage:
        """Create message from dictionary."""
        timestamp = None
        if data.get('timestamp'):
            from datetime import datetime

            timestamp = datetime.fromisoformat(data['timestamp'])

        return cls(
            event=data['event'],
            data=data.get('data'),
            timestamp=timestamp,
            sender_id=data.get('sender_id'),
            message_id=data.get('message_id'),
        )


class Channel:
    """WebSocket Channel for managing communication between clients.

    A Channel provides:
    - Event-based messaging
    - Subscription/unsubscription management
    - Message filtering and routing
    - Connection lifecycle management
    """

    def __init__(
        self,
        name: str,
        max_connections: int = 1000,
        message_buffer_size: int = 100,
        auto_cleanup: bool = True,
    ):
        """Initialize a WebSocket channel.

        Args:
            name: Channel name
            max_connections: Maximum number of concurrent connections
            message_buffer_size: Size of message history buffer
            auto_cleanup: Whether to auto-close when no connections remain

        """
        self.name = name
        self.max_connections = max_connections
        self.message_buffer_size = message_buffer_size
        self.auto_cleanup = auto_cleanup

        self.state = ChannelState.CREATED
        self.created_at = datetime.now(timezone.utc)

        # Connection management
        self._connections: dict[str, WebSocket] = {}
        self._connection_metadata: dict[str, dict[str, Any]] = {}
        self._connection_subscriptions: dict[str, set[str]] = {}

        # Event handlers
        self._event_handlers: dict[str, list[Callable]] = {}

        # Message handling
        self._message_buffer: list[ChannelMessage] = []
        self._message_filters: list[Callable[[ChannelMessage], bool]] = []

        # Statistics
        self._stats = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
        }

        self.state = ChannelState.ACTIVE
        logger.info(f"Channel '{name}' created")

    @property
    def connection_count(self) -> int:
        """Get current connection count."""
        return len(self._connections)

    @property
    def stats(self) -> dict[str, Any]:
        """Get channel statistics."""
        return {
            **self._stats,
            'current_connections': self.connection_count,
            'buffer_size': len(self._message_buffer),
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
        }

    def _generate_connection_id(self, websocket: WebSocket) -> str:
        """Generate unique connection ID."""
        import uuid

        base_id = str(uuid.uuid4())[:8]
        client_info = (
            f'{websocket.client[0]}:{websocket.client[1]}'
            if websocket.client
            else 'unknown'
        )
        return f'{base_id}_{client_info}'

    async def add_connection(
        self,
        websocket: WebSocket,
        connection_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a WebSocket connection to the channel.

        Args:
            websocket: WebSocket connection
            connection_id: Optional custom connection ID
            metadata: Optional connection metadata

        Returns:
            Connection ID

        Raises:
            ValueError: If channel is full or connection already exists

        """
        if self.state != ChannelState.ACTIVE:
            raise ValueError(f'Cannot add connection to {self.state.value} channel')

        if len(self._connections) >= self.max_connections:
            raise ValueError(
                f"Channel '{self.name}' is full (max: {self.max_connections})"
            )

        conn_id = connection_id or self._generate_connection_id(websocket)

        if conn_id in self._connections:
            raise ValueError(f"Connection '{conn_id}' already exists in channel")

        self._connections[conn_id] = websocket
        self._connection_metadata[conn_id] = metadata or {}
        self._connection_subscriptions[conn_id] = set()

        self._stats['total_connections'] += 1
        self._stats['current_connections'] = len(self._connections)

        # Emit connection event
        await self._emit_event(
            'connection.joined',
            {
                'connection_id': conn_id,
                'metadata': self._connection_metadata[conn_id],
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Connection '{conn_id}' added to channel '{self.name}'")
        return conn_id

    async def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection from the channel.

        Args:
            connection_id: Connection ID to remove

        Returns:
            True if connection was removed, False if not found

        """
        if connection_id not in self._connections:
            return False

        # Clean up subscriptions
        self._connection_subscriptions.pop(connection_id, None)

        # Get metadata before removing
        metadata = self._connection_metadata.pop(connection_id, {})

        # Remove connection
        self._connections.pop(connection_id)

        self._stats['current_connections'] = len(self._connections)

        # Emit disconnection event
        await self._emit_event(
            'connection.left',
            {
                'connection_id': connection_id,
                'metadata': metadata,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Connection '{connection_id}' removed from channel '{self.name}'")

        # Auto-cleanup if enabled and no connections
        if self.auto_cleanup and not self._connections:
            await self.close()

        return True

    def get_connection(self, connection_id: str) -> WebSocket | None:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def get_connection_metadata(self, connection_id: str) -> dict[str, Any] | None:
        """Get connection metadata."""
        return self._connection_metadata.get(connection_id)

    def list_connections(self) -> list[str]:
        """List all connection IDs."""
        return list(self._connections.keys())

    async def subscribe(self, connection_id: str, event: str) -> bool:
        """Subscribe a connection to an event.

        Args:
            connection_id: Connection ID
            event: Event name to subscribe to

        Returns:
            True if subscribed, False if connection not found

        """
        if connection_id not in self._connections:
            return False

        self._connection_subscriptions[connection_id].add(event)
        logger.debug(
            f"Connection '{connection_id}' subscribed to '{event}' in channel '{self.name}'"
        )
        return True

    async def unsubscribe(self, connection_id: str, event: str) -> bool:
        """Unsubscribe a connection from an event.

        Args:
            connection_id: Connection ID
            event: Event name to unsubscribe from

        Returns:
            True if unsubscribed, False if connection not found or not subscribed

        """
        if connection_id not in self._connection_subscriptions:
            return False

        subscriptions = self._connection_subscriptions[connection_id]
        if event in subscriptions:
            subscriptions.remove(event)
            logger.debug(
                f"Connection '{connection_id}' unsubscribed from '{event}' in channel '{self.name}'"
            )
            return True

        return False

    def get_subscriptions(self, connection_id: str) -> set[str]:
        """Get all subscriptions for a connection."""
        return self._connection_subscriptions.get(connection_id, set()).copy()

    async def send_to_connection(
        self,
        connection_id: str,
        message: str | dict[str, Any] | ChannelMessage,
    ) -> bool:
        """Send a message to a specific connection.

        Args:
            connection_id: Target connection ID
            message: Message to send

        Returns:
            True if sent successfully, False otherwise

        """
        websocket = self._connections.get(connection_id)
        if not websocket:
            return False

        try:
            if isinstance(message, ChannelMessage):
                await websocket.send_json(message.to_dict())
            elif isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))

            self._stats['messages_sent'] += 1
            return True

        except (WebSocketDisconnect, ConnectionError, Exception) as e:
            logger.warning(
                f"Failed to send message to connection '{connection_id}': {e}"
            )
            # Remove dead connection
            await self.remove_connection(connection_id)
            self._stats['errors'] += 1
            return False

    async def broadcast(
        self,
        message: str | dict[str, Any] | ChannelMessage,
        exclude: set[str] | None = None,
        include_only: set[str] | None = None,
    ) -> int:
        """Broadcast a message to all or selected connections.

        Args:
            message: Message to broadcast
            exclude: Connection IDs to exclude
            include_only: Only send to these connection IDs

        Returns:
            Number of connections that received the message

        """
        if self.state != ChannelState.ACTIVE:
            return 0

        exclude = exclude or set()
        target_connections = set(self._connections.keys())

        if include_only is not None:
            target_connections &= include_only
            # If include_only is empty, no connections should receive the message
            if not include_only:
                return 0

        target_connections -= exclude

        success_count = 0
        failed_connections = []

        for conn_id in target_connections:
            if await self.send_to_connection(conn_id, message):
                success_count += 1
            else:
                failed_connections.append(conn_id)

        # Clean up failed connections
        for conn_id in failed_connections:
            await self.remove_connection(conn_id)

        return success_count

    async def emit_event(
        self,
        event: str,
        data: Any = None,
        target_connections: set[str] | None = None,
    ) -> int:
        """Emit an event to subscribed connections.

        Args:
            event: Event name
            data: Event data
            target_connections: Specific connections to target (optional)

        Returns:
            Number of connections that received the event

        """
        message = ChannelMessage(event=event, data=data)

        # Add to message buffer
        self._add_to_buffer(message)

        # Find subscribed connections
        subscribed_connections = set()
        for conn_id, subscriptions in self._connection_subscriptions.items():
            if event in subscriptions:
                subscribed_connections.add(conn_id)

        # Filter by target connections if specified
        if target_connections:
            subscribed_connections &= target_connections

        # Apply message filters
        if not self._should_deliver_message(message):
            return 0

        # Broadcast to subscribed connections
        return await self.broadcast(message, include_only=subscribed_connections)

    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit internal event for system events."""
        # Call event handlers
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(self, event, data)
                else:
                    handler(self, event, data)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {e}")
                self._stats['errors'] += 1

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable | None = None) -> None:
        """Remove an event handler."""
        if event in self._event_handlers:
            if handler:
                try:
                    self._event_handlers[event].remove(handler)
                except ValueError:
                    pass
            else:
                self._event_handlers[event].clear()

    def add_message_filter(self, filter_func: Callable[[ChannelMessage], bool]) -> None:
        """Add a message filter function."""
        self._message_filters.append(filter_func)

    def _should_deliver_message(self, message: ChannelMessage) -> bool:
        """Check if message should be delivered based on filters."""
        for filter_func in self._message_filters:
            try:
                if not filter_func(message):
                    return False
            except Exception as e:
                logger.error(f'Error in message filter: {e}')
                self._stats['errors'] += 1
        return True

    def _add_to_buffer(self, message: ChannelMessage) -> None:
        """Add message to buffer with size limit."""
        self._message_buffer.append(message)
        if len(self._message_buffer) > self.message_buffer_size:
            self._message_buffer.pop(0)
        self._stats['messages_received'] += 1

    def get_message_history(self, limit: int | None = None) -> list[ChannelMessage]:
        """Get message history from buffer."""
        if limit:
            return self._message_buffer[-limit:]
        return self._message_buffer.copy()

    async def close(self) -> None:
        """Close the channel and disconnect all connections."""
        if self.state == ChannelState.CLOSED:
            return

        self.state = ChannelState.CLOSED

        # Notify all connections about channel closure
        close_message = ChannelMessage(
            event='channel.closing',
            data={'reason': 'Channel is being closed'},
        )

        await self.broadcast(close_message)

        # Close all connections
        for conn_id in list(self._connections.keys()):
            websocket = self._connections[conn_id]
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing connection '{conn_id}': {e}")
            finally:
                await self.remove_connection(conn_id)

        # Clear all data
        self._connections.clear()
        self._connection_metadata.clear()
        self._connection_subscriptions.clear()
        self._event_handlers.clear()
        self._message_buffer.clear()
        self._message_filters.clear()

        logger.info(f"Channel '{self.name}' closed")

    def __repr__(self) -> str:
        """Return string representation of the channel."""
        return (
            f"Channel(name='{self.name}', connections={self.connection_count}, "
            f'state={self.state.value})'
        )
