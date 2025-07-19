"""WebSocket support for Velithon framework.

This package provides comprehensive WebSocket functionality including:
- Basic WebSocket connections and endpoints
- Channel-based messaging system
- Heartbeat monitoring for connection health
- Room management for group communications
- User roles and permissions
"""

from .channel import Channel, ChannelMessage, ChannelState
from .connection import WebSocket, WebSocketDisconnect, WebSocketState
from .endpoint import WebSocketEndpoint, websocket_response
from .heartbeat import Heartbeat, HeartbeatManager, HeartbeatState
from .room import Room, RoomManager, RoomState, RoomUser, UserRole
from .websocket import WebSocketRoute, websocket_route

__all__ = [
    # Channel system
    'Channel',
    'ChannelMessage',
    'ChannelState',
    # Heartbeat system
    'Heartbeat',
    'HeartbeatManager',
    'HeartbeatState',
    # Room system
    'Room',
    'RoomManager',
    'RoomState',
    'RoomUser',
    'UserRole',
    # Core WebSocket
    'WebSocket',
    'WebSocketDisconnect',
    'WebSocketEndpoint',
    'WebSocketRoute',
    'WebSocketState',
    'websocket_response',
    'websocket_route',
]
