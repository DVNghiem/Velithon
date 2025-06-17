"""WebSocket Room management implementation for Velithon.

Provides room-based WebSocket connection management with support for:
- Room creation and management
- User join/leave operations
- Room-specific messaging and events
- User permissions and roles
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from velithon.websocket.channel import Channel, ChannelMessage
from velithon.websocket.connection import WebSocket

logger = logging.getLogger(__name__)


class RoomState(Enum):
    """Room state enumeration."""

    CREATED = 'created'
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    CLOSED = 'closed'


class UserRole(Enum):
    """User role enumeration."""

    GUEST = 'guest'
    MEMBER = 'member'
    MODERATOR = 'moderator'
    ADMIN = 'admin'
    OWNER = 'owner'


class RoomUser:
    """Represents a user in a room."""

    def __init__(
        self,
        user_id: str,
        connection_id: str,
        websocket: WebSocket,
        role: UserRole = UserRole.MEMBER,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize a room user.

        Args:
            user_id: Unique user identifier
            connection_id: WebSocket connection ID
            websocket: WebSocket connection
            role: User role in the room
            metadata: Additional user metadata

        """
        self.user_id = user_id
        self.connection_id = connection_id
        self.websocket = websocket
        self.role = role
        self.metadata = metadata or {}
        self.joined_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has required permission level."""
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.MEMBER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3,
            UserRole.OWNER: 4,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert user to dictionary representation."""
        return {
            'user_id': self.user_id,
            'connection_id': self.connection_id,
            'role': self.role.value,
            'metadata': self.metadata,
            'joined_at': self.joined_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
        }


class Room:
    """WebSocket Room for managing groups of connected users.

    A Room provides:
    - User management with roles and permissions
    - Room-specific messaging and events
    - Message history and persistence
    - Moderation capabilities
    - Custom room settings and metadata
    """

    def __init__(
        self,
        room_id: str,
        name: str,
        max_users: int = 100,
        require_auth: bool = False,
        default_role: UserRole = UserRole.MEMBER,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize a WebSocket room.

        Args:
            room_id: Unique room identifier
            name: Human-readable room name
            max_users: Maximum number of users allowed
            require_auth: Whether authentication is required to join
            default_role: Default role for new users
            metadata: Additional room metadata

        """
        self.room_id = room_id
        self.name = name
        self.max_users = max_users
        self.require_auth = require_auth
        self.default_role = default_role
        self.metadata = metadata or {}

        self.state = RoomState.CREATED
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)

        # User management
        self._users: dict[str, RoomUser] = {}  # user_id -> RoomUser
        self._connections: dict[str, str] = {}  # connection_id -> user_id

        # Channel for messaging
        self._channel = Channel(
            name=f'room_{room_id}',
            max_connections=max_users,
            auto_cleanup=False,
        )

        # Room settings
        self._settings = {
            'allow_anonymous': not require_auth,
            'message_history_limit': 100,
            'slow_mode_interval': 0,  # Seconds between messages per user
            'mute_list': set(),  # Muted user IDs
            'ban_list': set(),  # Banned user IDs
        }

        # Message history
        self._message_history: list[dict[str, Any]] = []

        # Event handlers
        self._event_handlers: dict[str, list[Callable]] = {}

        # Statistics
        self._stats = {
            'total_joins': 0,
            'total_leaves': 0,
            'total_messages': 0,
            'total_kicks': 0,
            'total_bans': 0,
        }

        # User activity tracking
        self._user_last_message: dict[str, datetime] = {}

        self.state = RoomState.ACTIVE
        logger.info(f"Room '{room_id}' ({name}) created")

    @property
    def user_count(self) -> int:
        """Get current user count."""
        return len(self._users)

    @property
    def is_full(self) -> bool:
        """Check if room is at capacity."""
        return self.user_count >= self.max_users

    @property
    def stats(self) -> dict[str, Any]:
        """Get room statistics."""
        return {
            **self._stats,
            'room_id': self.room_id,
            'name': self.name,
            'state': self.state.value,
            'current_users': self.user_count,
            'max_users': self.max_users,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
        }

    def get_settings(self) -> dict[str, Any]:
        """Get room settings."""
        return {
            **self._settings,
            'mute_list': list(self._settings['mute_list']),
            'ban_list': list(self._settings['ban_list']),
        }

    def update_settings(self, settings: dict[str, Any]) -> None:
        """Update room settings."""
        for key, value in settings.items():
            if key in self._settings:
                if key in ('mute_list', 'ban_list'):
                    self._settings[key] = (
                        set(value) if isinstance(value, list) else value
                    )
                else:
                    self._settings[key] = value

    async def add_user(
        self,
        user_id: str,
        websocket: WebSocket,
        connection_id: str,
        role: UserRole | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RoomUser:
        """Add a user to the room.

        Args:
            user_id: Unique user identifier
            websocket: WebSocket connection
            connection_id: Connection identifier
            role: User role (uses default if None)
            metadata: User metadata

        Returns:
            RoomUser instance

        Raises:
            ValueError: If room is full, user is banned, or already in room

        """
        if self.state != RoomState.ACTIVE:
            raise ValueError(f'Cannot join {self.state.value} room')

        if self.is_full:
            raise ValueError(f"Room '{self.room_id}' is full")

        if user_id in self._settings['ban_list']:
            raise ValueError(f"User '{user_id}' is banned from room")

        if user_id in self._users:
            raise ValueError(f"User '{user_id}' is already in room")

        # Create room user
        room_user = RoomUser(
            user_id=user_id,
            connection_id=connection_id,
            websocket=websocket,
            role=role or self.default_role,
            metadata=metadata,
        )

        # Add to room
        self._users[user_id] = room_user
        self._connections[connection_id] = user_id

        # Add to channel
        await self._channel.add_connection(
            websocket=websocket,
            connection_id=connection_id,
            metadata={'user_id': user_id, 'role': room_user.role.value},
        )

        # Update statistics
        self._stats['total_joins'] += 1
        self.last_activity = datetime.now(timezone.utc)

        # Emit user joined event
        await self._emit_event(
            'user.joined',
            {
                'user': room_user.to_dict(),
                'room_id': self.room_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"User '{user_id}' joined room '{self.room_id}'")
        return room_user

    async def remove_user(self, user_id: str, reason: str = 'left') -> bool:
        """Remove a user from the room.

        Args:
            user_id: User ID to remove
            reason: Reason for removal

        Returns:
            True if user was removed, False if not found

        """
        room_user = self._users.get(user_id)
        if not room_user:
            return False

        # Remove from channel
        await self._channel.remove_connection(room_user.connection_id)

        # Remove from room
        del self._users[user_id]
        self._connections.pop(room_user.connection_id, None)

        # Clean up activity tracking
        self._user_last_message.pop(user_id, None)

        # Update statistics
        if reason == 'kicked':
            self._stats['total_kicks'] += 1
        elif reason == 'banned':
            self._stats['total_bans'] += 1
        else:
            self._stats['total_leaves'] += 1

        self.last_activity = datetime.now(timezone.utc)

        # Emit user left event
        await self._emit_event(
            'user.left',
            {
                'user': room_user.to_dict(),
                'reason': reason,
                'room_id': self.room_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"User '{user_id}' {reason} room '{self.room_id}'")
        return True

    def get_user(self, user_id: str) -> RoomUser | None:
        """Get a user by ID."""
        return self._users.get(user_id)

    def get_user_by_connection(self, connection_id: str) -> RoomUser | None:
        """Get a user by connection ID."""
        user_id = self._connections.get(connection_id)
        return self._users.get(user_id) if user_id else None

    def list_users(self) -> list[RoomUser]:
        """List all users in the room."""
        return list(self._users.values())

    def get_users_by_role(self, role: UserRole) -> list[RoomUser]:
        """Get users with specific role."""
        return [user for user in self._users.values() if user.role == role]

    async def update_user_role(
        self,
        user_id: str,
        new_role: UserRole,
        moderator_id: str | None = None,
    ) -> bool:
        """Update a user's role.

        Args:
            user_id: User ID to update
            new_role: New role to assign
            moderator_id: ID of user making the change

        Returns:
            True if role was updated, False if user not found

        """
        room_user = self._users.get(user_id)
        if not room_user:
            return False

        old_role = room_user.role
        room_user.role = new_role

        # Update channel metadata
        channel_metadata = self._channel.get_connection_metadata(
            room_user.connection_id
        )
        if channel_metadata:
            channel_metadata['role'] = new_role.value

        # Emit role change event
        await self._emit_event(
            'user.role_changed',
            {
                'user_id': user_id,
                'old_role': old_role.value,
                'new_role': new_role.value,
                'moderator_id': moderator_id,
                'room_id': self.room_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(
            f"User '{user_id}' role changed from {old_role.value} to {new_role.value} "
            f"in room '{self.room_id}'"
        )
        return True

    async def send_message(
        self,
        sender_id: str,
        content: str,
        message_type: str = 'text',
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Send a message in the room.

        Args:
            sender_id: ID of the user sending the message
            content: Message content
            message_type: Type of message (text, image, etc.)
            metadata: Additional message metadata

        Returns:
            True if message was sent, False otherwise

        """
        sender = self._users.get(sender_id)
        if not sender:
            return False

        # Check if user is muted
        if sender_id in self._settings['mute_list']:
            return False

        # Check slow mode
        slow_mode_interval = self._settings['slow_mode_interval']
        if slow_mode_interval > 0:
            last_message = self._user_last_message.get(sender_id)
            if last_message:
                time_since_last = (
                    datetime.now(timezone.utc) - last_message
                ).total_seconds()
                if time_since_last < slow_mode_interval:
                    return False

        # Create message
        message = {
            'id': self._generate_message_id(),
            'room_id': self.room_id,
            'sender_id': sender_id,
            'sender_role': sender.role.value,
            'content': content,
            'type': message_type,
            'metadata': metadata or {},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        # Add to history
        self._add_to_history(message)

        # Update activity tracking
        sender.update_activity()
        self._user_last_message[sender_id] = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)

        # Broadcast message
        channel_message = ChannelMessage(
            event='room.message',
            data=message,
            sender_id=sender_id,
        )

        await self._channel.broadcast(channel_message)

        # Update statistics
        self._stats['total_messages'] += 1

        # Emit message event
        await self._emit_event('message.sent', message)

        return True

    async def broadcast_system_message(
        self,
        content: str,
        message_type: str = 'system',
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a system message to all users."""
        message = {
            'id': self._generate_message_id(),
            'room_id': self.room_id,
            'sender_id': 'system',
            'sender_role': 'system',
            'content': content,
            'type': message_type,
            'metadata': metadata or {},
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        # Add to history
        self._add_to_history(message)

        # Broadcast message
        channel_message = ChannelMessage(
            event='room.system_message',
            data=message,
        )

        await self._channel.broadcast(channel_message)

        # Update statistics
        self._stats['total_messages'] += 1

    async def kick_user(
        self, user_id: str, moderator_id: str, reason: str = ''
    ) -> bool:
        """Kick a user from the room.

        Args:
            user_id: User ID to kick
            moderator_id: ID of the moderator performing the kick
            reason: Reason for kicking

        Returns:
            True if user was kicked, False otherwise

        """
        # Check if user exists
        if user_id not in self._users:
            return False

        # Check if moderator has permission
        moderator = self._users.get(moderator_id)
        if not moderator or not moderator.has_permission(UserRole.MODERATOR):
            return False

        # Cannot kick users of equal or higher role
        target_user = self._users[user_id]
        if not moderator.has_permission(target_user.role):
            return False

        # Send kick message to user
        await self.send_private_message(
            target_id=user_id,
            content=f'You have been kicked from the room. Reason: {reason}',
            sender_id='system',
        )

        # Remove user
        await self.remove_user(user_id, reason='kicked')

        # Broadcast kick notification
        await self.broadcast_system_message(
            f'User {user_id} was kicked from the room. Reason: {reason}',
            metadata={'moderator_id': moderator_id, 'reason': reason},
        )

        return True

    async def ban_user(self, user_id: str, moderator_id: str, reason: str = '') -> bool:
        """Ban a user from the room.

        Args:
            user_id: User ID to ban
            moderator_id: ID of the moderator performing the ban
            reason: Reason for banning

        Returns:
            True if user was banned, False otherwise

        """
        # Check if moderator has permission
        moderator = self._users.get(moderator_id)
        if not moderator or not moderator.has_permission(UserRole.MODERATOR):
            return False

        # Check if user is in room and permission check
        if user_id in self._users:
            target_user = self._users[user_id]
            if not moderator.has_permission(target_user.role):
                return False

            # Send ban message to user
            await self.send_private_message(
                target_id=user_id,
                content=f'You have been banned from the room. Reason: {reason}',
                sender_id='system',
            )

            # Remove user
            await self.remove_user(user_id, reason='banned')

        # Add to ban list
        self._settings['ban_list'].add(user_id)

        # Broadcast ban notification
        await self.broadcast_system_message(
            f'User {user_id} was banned from the room. Reason: {reason}',
            metadata={'moderator_id': moderator_id, 'reason': reason},
        )

        return True

    async def unban_user(self, user_id: str, moderator_id: str) -> bool:
        """Unban a user from the room."""
        moderator = self._users.get(moderator_id)
        if not moderator or not moderator.has_permission(UserRole.MODERATOR):
            return False

        if user_id in self._settings['ban_list']:
            self._settings['ban_list'].remove(user_id)

            await self.broadcast_system_message(
                f'User {user_id} was unbanned from the room.',
                metadata={'moderator_id': moderator_id},
            )
            return True

        return False

    async def mute_user(self, user_id: str, moderator_id: str) -> bool:
        """Mute a user in the room."""
        moderator = self._users.get(moderator_id)
        if not moderator or not moderator.has_permission(UserRole.MODERATOR):
            return False

        if user_id in self._users:
            target_user = self._users[user_id]
            if not moderator.has_permission(target_user.role):
                return False

        self._settings['mute_list'].add(user_id)

        await self.broadcast_system_message(
            f'User {user_id} was muted.',
            metadata={'moderator_id': moderator_id},
        )
        return True

    async def unmute_user(self, user_id: str, moderator_id: str) -> bool:
        """Unmute a user in the room."""
        moderator = self._users.get(moderator_id)
        if not moderator or not moderator.has_permission(UserRole.MODERATOR):
            return False

        if user_id in self._settings['mute_list']:
            self._settings['mute_list'].remove(user_id)

            await self.broadcast_system_message(
                f'User {user_id} was unmuted.',
                metadata={'moderator_id': moderator_id},
            )
            return True

        return False

    async def send_private_message(
        self,
        target_id: str,
        content: str,
        sender_id: str,
        message_type: str = 'private',
    ) -> bool:
        """Send a private message to a specific user."""
        target_user = self._users.get(target_id)
        if not target_user:
            return False

        message = {
            'id': self._generate_message_id(),
            'room_id': self.room_id,
            'sender_id': sender_id,
            'target_id': target_id,
            'content': content,
            'type': message_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        # Send to specific connection
        await self._channel.send_to_connection(
            target_user.connection_id,
            ChannelMessage(event='room.private_message', data=message),
        )

        return True

    def get_message_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get message history."""
        if limit:
            return self._message_history[-limit:]
        return self._message_history.copy()

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

    async def suspend(self) -> None:
        """Suspend the room."""
        if self.state == RoomState.ACTIVE:
            self.state = RoomState.SUSPENDED
            await self.broadcast_system_message('Room has been suspended.')
            logger.info(f"Room '{self.room_id}' suspended")

    async def resume(self) -> None:
        """Resume the room."""
        if self.state == RoomState.SUSPENDED:
            self.state = RoomState.ACTIVE
            await self.broadcast_system_message('Room has been resumed.')
            logger.info(f"Room '{self.room_id}' resumed")

    async def close(self) -> None:
        """Close the room and disconnect all users."""
        if self.state == RoomState.CLOSED:
            return

        self.state = RoomState.CLOSED

        # Notify all users
        await self.broadcast_system_message('Room is closing.')

        # Remove all users
        for user_id in list(self._users.keys()):
            await self.remove_user(user_id, reason='room_closed')

        # Close channel
        await self._channel.close()

        # Clear data
        self._users.clear()
        self._connections.clear()
        self._message_history.clear()
        self._event_handlers.clear()
        self._user_last_message.clear()

        logger.info(f"Room '{self.room_id}' closed")

    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        import uuid

        return str(uuid.uuid4())

    def _add_to_history(self, message: dict[str, Any]) -> None:
        """Add message to history with size limit."""
        self._message_history.append(message)
        history_limit = self._settings['message_history_limit']
        if len(self._message_history) > history_limit:
            self._message_history.pop(0)

    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit internal event."""
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


class RoomManager:
    """Manages multiple WebSocket rooms.

    Provides centralized room management with:
    - Room creation and deletion
    - User management across rooms
    - Cross-room messaging capabilities
    - Room discovery and listing
    - Global statistics and monitoring
    """

    def __init__(
        self,
        max_rooms: int = 1000,
        default_max_users: int = 100,
        auto_cleanup: bool = True,
        cleanup_interval: float = 300.0,  # 5 minutes
    ):
        """Initialize room manager.

        Args:
            max_rooms: Maximum number of concurrent rooms
            default_max_users: Default maximum users per room
            auto_cleanup: Whether to auto-cleanup empty rooms
            cleanup_interval: Interval for cleanup operations

        """
        self.max_rooms = max_rooms
        self.default_max_users = default_max_users
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval = cleanup_interval

        # Room tracking
        self._rooms: dict[str, Room] = {}
        self._user_rooms: dict[str, set[str]] = {}  # user_id -> set of room_ids

        # Manager state
        self._running = False
        self._cleanup_task: asyncio.Task | None = None

        # Statistics
        self._stats = {
            'total_rooms_created': 0,
            'total_rooms_deleted': 0,
            'total_users_joined': 0,
            'total_users_left': 0,
            'total_messages': 0,
        }

        # Event callbacks
        self._event_handlers: dict[str, list[Callable]] = {}

        logger.info('RoomManager initialized')

    @property
    def room_count(self) -> int:
        """Get current room count."""
        return len(self._rooms)

    @property
    def stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        active_rooms = len(
            [r for r in self._rooms.values() if r.state == RoomState.ACTIVE]
        )
        total_users = sum(room.user_count for room in self._rooms.values())

        return {
            **self._stats,
            'current_rooms': self.room_count,
            'active_rooms': active_rooms,
            'total_users': total_users,
        }

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

    async def start(self) -> None:
        """Start the room manager."""
        if self._running:
            logger.warning('RoomManager is already running')
            return

        self._running = True

        # Start cleanup task if auto-cleanup is enabled
        if self.auto_cleanup:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info('RoomManager started')

    async def stop(self) -> None:
        """Stop the room manager."""
        if not self._running:
            return

        self._running = False

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all rooms
        await self.close_all_rooms()

        logger.info('RoomManager stopped')

    async def create_room(
        self,
        room_id: str,
        name: str,
        max_users: int | None = None,
        require_auth: bool = False,
        default_role: UserRole = UserRole.MEMBER,
        metadata: dict[str, Any] | None = None,
    ) -> Room:
        """Create a new room.

        Args:
            room_id: Unique room identifier
            name: Human-readable room name
            max_users: Maximum users (uses default if None)
            require_auth: Whether authentication is required
            default_role: Default role for new users
            metadata: Additional room metadata

        Returns:
            Room instance

        Raises:
            ValueError: If room already exists or manager is full

        """
        if room_id in self._rooms:
            raise ValueError(f"Room '{room_id}' already exists")

        if len(self._rooms) >= self.max_rooms:
            raise ValueError(f'Room manager is full (max: {self.max_rooms})')

        # Create room
        room = Room(
            room_id=room_id,
            name=name,
            max_users=max_users or self.default_max_users,
            require_auth=require_auth,
            default_role=default_role,
            metadata=metadata,
        )

        # Set up room event handlers
        room.on('user.joined', self._handle_user_joined)
        room.on('user.left', self._handle_user_left)
        room.on('message.sent', self._handle_message_sent)

        # Add to tracking
        self._rooms[room_id] = room
        self._stats['total_rooms_created'] += 1

        # Emit event
        await self._emit_event(
            'room.created',
            {
                'room_id': room_id,
                'name': name,
                'metadata': metadata,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Room '{room_id}' ({name}) created")
        return room

    async def delete_room(self, room_id: str) -> bool:
        """Delete a room.

        Args:
            room_id: Room ID to delete

        Returns:
            True if room was deleted, False if not found

        """
        room = self._rooms.get(room_id)
        if not room:
            return False

        # Close room
        await room.close()

        # Remove from tracking
        del self._rooms[room_id]
        self._stats['total_rooms_deleted'] += 1

        # Clean up user room tracking
        for user_id, room_set in self._user_rooms.items():
            room_set.discard(room_id)

        # Remove empty user entries
        empty_users = [uid for uid, rooms in self._user_rooms.items() if not rooms]
        for uid in empty_users:
            del self._user_rooms[uid]

        # Emit event
        await self._emit_event(
            'room.deleted',
            {
                'room_id': room_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Room '{room_id}' deleted")
        return True

    def get_room(self, room_id: str) -> Room | None:
        """Get a room by ID."""
        return self._rooms.get(room_id)

    def list_rooms(self) -> list[Room]:
        """List all rooms."""
        return list(self._rooms.values())

    def get_rooms_by_state(self, state: RoomState) -> list[Room]:
        """Get rooms with specific state."""
        return [room for room in self._rooms.values() if room.state == state]

    def get_user_rooms(self, user_id: str) -> list[Room]:
        """Get rooms that a user is in."""
        room_ids = self._user_rooms.get(user_id, set())
        return [self._rooms[rid] for rid in room_ids if rid in self._rooms]

    async def join_room(
        self,
        room_id: str,
        user_id: str,
        websocket: WebSocket,
        connection_id: str,
        role: UserRole | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Join a user to a room.

        Args:
            room_id: Room ID to join
            user_id: User ID
            websocket: WebSocket connection
            connection_id: Connection ID
            role: User role (optional)
            metadata: User metadata (optional)

        Returns:
            True if joined successfully, False otherwise

        """
        room = self._rooms.get(room_id)
        if not room:
            return False

        try:
            await room.add_user(
                user_id=user_id,
                websocket=websocket,
                connection_id=connection_id,
                role=role,
                metadata=metadata,
            )

            # Update user room tracking
            if user_id not in self._user_rooms:
                self._user_rooms[user_id] = set()
            self._user_rooms[user_id].add(room_id)

            return True

        except ValueError as e:
            logger.warning(f"Failed to join room '{room_id}': {e}")
            return False

    async def leave_room(self, room_id: str, user_id: str) -> bool:
        """Remove a user from a room.

        Args:
            room_id: Room ID to leave
            user_id: User ID

        Returns:
            True if left successfully, False otherwise

        """
        room = self._rooms.get(room_id)
        if not room:
            return False

        success = await room.remove_user(user_id)

        if success:
            # Update user room tracking
            if user_id in self._user_rooms:
                self._user_rooms[user_id].discard(room_id)
                if not self._user_rooms[user_id]:
                    del self._user_rooms[user_id]

        return success

    async def leave_all_rooms(self, user_id: str) -> int:
        """Remove a user from all rooms they're in.

        Args:
            user_id: User ID

        Returns:
            Number of rooms left

        """
        room_ids = list(self._user_rooms.get(user_id, set()))
        count = 0

        for room_id in room_ids:
            if await self.leave_room(room_id, user_id):
                count += 1

        return count

    async def broadcast_to_all_rooms(
        self,
        content: str,
        message_type: str = 'system',
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Broadcast a message to all rooms.

        Args:
            content: Message content
            message_type: Message type
            metadata: Message metadata

        Returns:
            Number of rooms that received the message

        """
        count = 0
        for room in self._rooms.values():
            if room.state == RoomState.ACTIVE:
                await room.broadcast_system_message(
                    content=content,
                    message_type=message_type,
                    metadata=metadata,
                )
                count += 1

        return count

    async def close_all_rooms(self) -> int:
        """Close all rooms.

        Returns:
            Number of rooms closed

        """
        count = 0
        for room in list(self._rooms.values()):
            await room.close()
            count += 1

        self._rooms.clear()
        self._user_rooms.clear()

        return count

    async def cleanup_empty_rooms(self) -> list[str]:
        """Clean up empty rooms.

        Returns:
            List of room IDs that were cleaned up

        """
        empty_rooms = []

        for room_id, room in list(self._rooms.items()):
            if room.user_count == 0 and room.state == RoomState.ACTIVE:
                # Check if room has been empty for a while
                time_since_activity = (
                    datetime.now(timezone.utc) - room.last_activity
                ).total_seconds()
                if time_since_activity > 300:  # 5 minutes
                    empty_rooms.append(room_id)
                    await self.delete_room(room_id)

        if empty_rooms:
            logger.info(f'Cleaned up {len(empty_rooms)} empty rooms')

        return empty_rooms

    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit internal event."""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(self, event, data)
                else:
                    handler(self, event, data)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {e}")

    def _handle_user_joined(self, room: Room, event: str, data: Any) -> None:
        """Handle user joined event from room."""
        self._stats['total_users_joined'] += 1

    def _handle_user_left(self, room: Room, event: str, data: Any) -> None:
        """Handle user left event from room."""
        self._stats['total_users_left'] += 1

    def _handle_message_sent(self, room: Room, event: str, data: Any) -> None:
        """Handle message sent event from room."""
        self._stats['total_messages'] += 1

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        try:
            while self._running:
                await asyncio.sleep(self.cleanup_interval)

                if not self._running:
                    break

                await self.cleanup_empty_rooms()

        except asyncio.CancelledError:
            logger.debug('Cleanup loop cancelled')
        except Exception as e:
            logger.error(f'Error in cleanup loop: {e}')
