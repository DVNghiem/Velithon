"""WebSocket Heartbeat implementation for Velithon.

Provides heartbeat functionality to detect disconnected WebSocket connections
and maintain connection health monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from velithon.websocket.connection import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class HeartbeatState(Enum):
    """Heartbeat state enumeration."""

    INACTIVE = 'inactive'
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    FAILED = 'failed'


class Heartbeat:
    """WebSocket heartbeat manager for individual connections.

    Manages ping/pong cycles for a single WebSocket connection to detect
    connection health and handle disconnections gracefully.
    """

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        interval: float = 30.0,
        timeout: float = 10.0,
        max_failures: int = 3,
    ):
        """Initialize heartbeat for a WebSocket connection.

        Args:
            websocket: WebSocket connection
            connection_id: Unique connection identifier
            interval: Ping interval in seconds
            timeout: Ping timeout in seconds
            max_failures: Maximum consecutive failures before marking as dead

        """
        self.websocket = websocket
        self.connection_id = connection_id
        self.interval = interval
        self.timeout = timeout
        self.max_failures = max_failures

        self.state = HeartbeatState.INACTIVE
        self.started_at: datetime | None = None
        self.last_ping_at: datetime | None = None
        self.last_pong_at: datetime | None = None

        # Statistics
        self.ping_count = 0
        self.pong_count = 0
        self.failure_count = 0
        self.consecutive_failures = 0

        # Internal state
        self._task: asyncio.Task | None = None
        self._ping_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._last_ping_data: str | None = None

        # Callbacks
        self._failure_callback: Callable | None = None
        self._success_callback: Callable | None = None
        self._disconnect_callback: Callable | None = None

    @property
    def is_active(self) -> bool:
        """Check if heartbeat is active."""
        return self.state == HeartbeatState.ACTIVE

    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy based on heartbeat status."""
        return (
            self.state == HeartbeatState.ACTIVE
            and self.consecutive_failures < self.max_failures
        )

    @property
    def stats(self) -> dict[str, Any]:
        """Get heartbeat statistics."""
        return {
            'connection_id': self.connection_id,
            'state': self.state.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_ping_at': self.last_ping_at.isoformat()
            if self.last_ping_at
            else None,
            'last_pong_at': self.last_pong_at.isoformat()
            if self.last_pong_at
            else None,
            'ping_count': self.ping_count,
            'pong_count': self.pong_count,
            'failure_count': self.failure_count,
            'consecutive_failures': self.consecutive_failures,
            'is_healthy': self.is_healthy,
            'interval': self.interval,
            'timeout': self.timeout,
            'max_failures': self.max_failures,
        }

    def on_failure(self, callback: Callable[[Heartbeat], None]) -> None:
        """Set callback for heartbeat failures."""
        self._failure_callback = callback

    def on_success(self, callback: Callable[[Heartbeat], None]) -> None:
        """Set callback for successful heartbeats."""
        self._success_callback = callback

    def on_disconnect(self, callback: Callable[[Heartbeat], None]) -> None:
        """Set callback for connection disconnections."""
        self._disconnect_callback = callback

    async def start(self) -> None:
        """Start the heartbeat monitoring."""
        if self.state == HeartbeatState.ACTIVE:
            logger.warning(f'Heartbeat for {self.connection_id} is already active')
            return

        self.state = HeartbeatState.ACTIVE
        self.started_at = datetime.now(timezone.utc)
        self._stop_event.clear()

        # Start the heartbeat task
        self._task = asyncio.create_task(self._heartbeat_loop())

        logger.debug(f'Heartbeat started for connection {self.connection_id}')

    async def stop(self) -> None:
        """Stop the heartbeat monitoring."""
        if self.state == HeartbeatState.INACTIVE:
            return

        self.state = HeartbeatState.INACTIVE
        self._stop_event.set()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.debug(f'Heartbeat stopped for connection {self.connection_id}')

    async def suspend(self) -> None:
        """Temporarily suspend heartbeat monitoring."""
        if self.state == HeartbeatState.ACTIVE:
            self.state = HeartbeatState.SUSPENDED
            logger.debug(f'Heartbeat suspended for connection {self.connection_id}')

    async def resume(self) -> None:
        """Resume heartbeat monitoring from suspended state."""
        if self.state == HeartbeatState.SUSPENDED:
            self.state = HeartbeatState.ACTIVE
            logger.debug(f'Heartbeat resumed for connection {self.connection_id}')

    async def ping(self) -> bool:
        """Send a ping to the WebSocket connection."""
        if not self.is_active:
            return False

        try:
            # Generate unique ping data
            ping_data = f'ping_{int(time.time() * 1000)}'
            self._last_ping_data = ping_data

            # Send ping (using text message since WebSocket ping might not be available)
            await self.websocket.send_json(
                {
                    'type': 'ping',
                    'data': ping_data,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                }
            )

            self.last_ping_at = datetime.now(timezone.utc)
            self.ping_count += 1

            logger.debug(f'Ping sent to connection {self.connection_id}')
            return True

        except (WebSocketDisconnect, ConnectionError, Exception) as e:
            logger.warning(f'Failed to send ping to {self.connection_id}: {e}')
            await self._handle_failure()
            return False

    async def handle_pong(self, data: str | None = None) -> bool:
        """Handle pong response from WebSocket connection."""
        if not self.is_active:
            return False

        # Verify pong data matches last ping
        if data and data != self._last_ping_data:
            logger.warning(
                f'Pong data mismatch for {self.connection_id}: '
                f'expected {self._last_ping_data}, got {data}'
            )
            return False

        self.last_pong_at = datetime.now(timezone.utc)
        self.pong_count += 1
        self.consecutive_failures = 0  # Reset failure counter

        # Calculate latency if we have ping time
        latency = None
        if self.last_ping_at:
            latency = (self.last_pong_at - self.last_ping_at).total_seconds() * 1000

        logger.debug(
            f'Pong received from connection {self.connection_id}'
            f'{f" (latency: {latency:.2f}ms)" if latency else ""}'
        )

        # Call success callback
        if self._success_callback:
            try:
                self._success_callback(self)
            except Exception as e:
                logger.error(f'Error in success callback: {e}')

        return True

    async def _heartbeat_loop(self) -> None:
        """Run main heartbeat loop."""
        try:
            while not self._stop_event.is_set():
                if self.state == HeartbeatState.ACTIVE:
                    # Send ping
                    ping_sent = await self.ping()

                    if ping_sent:
                        # Wait for pong with timeout
                        try:
                            await asyncio.wait_for(
                                self._wait_for_pong(), timeout=self.timeout
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                f'Ping timeout for connection {self.connection_id}'
                            )
                            await self._handle_failure()

                # Wait for next interval or stop signal
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self.interval
                    )
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    continue  # Time for next ping

        except asyncio.CancelledError:
            logger.debug(f'Heartbeat loop cancelled for {self.connection_id}')
        except Exception as e:
            logger.error(f'Error in heartbeat loop for {self.connection_id}: {e}')
            self.state = HeartbeatState.FAILED

    async def _wait_for_pong(self) -> None:
        """Wait for pong response."""
        # This is a simplified implementation
        # In practice, this would wait for an actual pong message
        # For now, we'll simulate a short wait
        await asyncio.sleep(0.1)

    async def _handle_failure(self) -> None:
        """Handle heartbeat failure."""
        self.failure_count += 1
        self.consecutive_failures += 1

        logger.warning(
            f'Heartbeat failure for {self.connection_id} '
            f'({self.consecutive_failures}/{self.max_failures})'
        )

        if self.consecutive_failures >= self.max_failures:
            self.state = HeartbeatState.FAILED
            logger.error(f'Connection {self.connection_id} marked as failed')

            # Call disconnect callback
            if self._disconnect_callback:
                try:
                    self._disconnect_callback(self)
                except Exception as e:
                    logger.error(f'Error in disconnect callback: {e}')

        # Call failure callback
        if self._failure_callback:
            try:
                self._failure_callback(self)
            except Exception as e:
                logger.error(f'Error in failure callback: {e}')


class HeartbeatManager:
    """Manages heartbeats for multiple WebSocket connections.

    Provides centralized heartbeat management with:
    - Automatic heartbeat creation and cleanup
    - Connection health monitoring
    - Bulk operations and statistics
    - Event handling for connection lifecycle
    """

    def __init__(
        self,
        default_interval: float = 30.0,
        default_timeout: float = 10.0,
        default_max_failures: int = 3,
        cleanup_interval: float = 60.0,
    ):
        """Initialize heartbeat manager.

        Args:
            default_interval: Default ping interval in seconds
            default_timeout: Default ping timeout in seconds
            default_max_failures: Default maximum consecutive failures
            cleanup_interval: Interval for cleanup of dead connections

        """
        self.default_interval = default_interval
        self.default_timeout = default_timeout
        self.default_max_failures = default_max_failures
        self.cleanup_interval = cleanup_interval

        # Heartbeat tracking
        self._heartbeats: dict[str, Heartbeat] = {}
        self._connection_websockets: dict[str, WebSocket] = {}

        # Manager state
        self._running = False
        self._cleanup_task: asyncio.Task | None = None

        # Statistics
        self._stats = {
            'total_connections': 0,
            'active_heartbeats': 0,
            'failed_connections': 0,
            'cleanup_runs': 0,
        }

        # Event callbacks
        self._connection_failed_callbacks: list[Callable] = []
        self._connection_recovered_callbacks: list[Callable] = []
        self._cleanup_callbacks: list[Callable] = []

    @property
    def stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        healthy_count = sum(1 for hb in self._heartbeats.values() if hb.is_healthy)
        return {
            **self._stats,
            'current_connections': len(self._heartbeats),
            'healthy_connections': healthy_count,
            'unhealthy_connections': len(self._heartbeats) - healthy_count,
        }

    def on_connection_failed(self, callback: Callable[[str, Heartbeat], None]) -> None:
        """Register callback for failed connections."""
        self._connection_failed_callbacks.append(callback)

    def on_connection_recovered(
        self, callback: Callable[[str, Heartbeat], None]
    ) -> None:
        """Register callback for recovered connections."""
        self._connection_recovered_callbacks.append(callback)

    def on_cleanup(self, callback: Callable[[list[str]], None]) -> None:
        """Register callback for cleanup operations."""
        self._cleanup_callbacks.append(callback)

    async def start(self) -> None:
        """Start the heartbeat manager."""
        if self._running:
            logger.warning('HeartbeatManager is already running')
            return

        self._running = True

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info('HeartbeatManager started')

    async def stop(self) -> None:
        """Stop the heartbeat manager."""
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

        # Stop all heartbeats
        await self.stop_all()

        logger.info('HeartbeatManager stopped')

    async def add_connection(
        self,
        websocket: WebSocket,
        connection_id: str,
        interval: float | None = None,
        timeout: float | None = None,
        max_failures: int | None = None,
        auto_start: bool = True,
    ) -> Heartbeat:
        """Add a WebSocket connection for heartbeat monitoring.

        Args:
            websocket: WebSocket connection
            connection_id: Unique connection identifier
            interval: Ping interval (uses default if None)
            timeout: Ping timeout (uses default if None)
            max_failures: Max failures (uses default if None)
            auto_start: Whether to start heartbeat immediately

        Returns:
            Heartbeat instance

        Raises:
            ValueError: If connection already exists

        """
        if connection_id in self._heartbeats:
            raise ValueError(f'Connection {connection_id} already exists')

        # Create heartbeat
        heartbeat = Heartbeat(
            websocket=websocket,
            connection_id=connection_id,
            interval=interval or self.default_interval,
            timeout=timeout or self.default_timeout,
            max_failures=max_failures or self.default_max_failures,
        )

        # Set up callbacks
        heartbeat.on_failure(self._handle_heartbeat_failure)
        heartbeat.on_success(self._handle_heartbeat_success)
        heartbeat.on_disconnect(self._handle_heartbeat_disconnect)

        # Store references
        self._heartbeats[connection_id] = heartbeat
        self._connection_websockets[connection_id] = websocket
        self._stats['total_connections'] += 1

        # Start if requested
        if auto_start:
            await heartbeat.start()
            self._stats['active_heartbeats'] += 1

        logger.debug(f'Added heartbeat for connection {connection_id}')
        return heartbeat

    async def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection from heartbeat monitoring.

        Args:
            connection_id: Connection ID to remove

        Returns:
            True if removed, False if not found

        """
        heartbeat = self._heartbeats.get(connection_id)
        if not heartbeat:
            return False

        # Stop heartbeat
        if heartbeat.is_active:
            await heartbeat.stop()
            self._stats['active_heartbeats'] = max(
                0, self._stats['active_heartbeats'] - 1
            )

        # Remove from tracking
        del self._heartbeats[connection_id]
        self._connection_websockets.pop(connection_id, None)

        logger.debug(f'Removed heartbeat for connection {connection_id}')
        return True

    def get_heartbeat(self, connection_id: str) -> Heartbeat | None:
        """Get heartbeat for a connection."""
        return self._heartbeats.get(connection_id)

    def list_connections(self) -> list[str]:
        """List all connection IDs."""
        return list(self._heartbeats.keys())

    def get_healthy_connections(self) -> list[str]:
        """Get list of healthy connection IDs."""
        return [conn_id for conn_id, hb in self._heartbeats.items() if hb.is_healthy]

    def get_unhealthy_connections(self) -> list[str]:
        """Get list of unhealthy connection IDs."""
        return [
            conn_id for conn_id, hb in self._heartbeats.items() if not hb.is_healthy
        ]

    async def suspend_connection(self, connection_id: str) -> bool:
        """Suspend heartbeat for a connection."""
        heartbeat = self._heartbeats.get(connection_id)
        if heartbeat:
            await heartbeat.suspend()
            return True
        return False

    async def resume_connection(self, connection_id: str) -> bool:
        """Resume heartbeat for a connection."""
        heartbeat = self._heartbeats.get(connection_id)
        if heartbeat:
            await heartbeat.resume()
            return True
        return False

    async def suspend_all(self) -> int:
        """Suspend all heartbeats."""
        count = 0
        for heartbeat in self._heartbeats.values():
            if heartbeat.is_active:
                await heartbeat.suspend()
                count += 1
        return count

    async def resume_all(self) -> int:
        """Resume all suspended heartbeats."""
        count = 0
        for heartbeat in self._heartbeats.values():
            if heartbeat.state == HeartbeatState.SUSPENDED:
                await heartbeat.resume()
                count += 1
        return count

    async def stop_all(self) -> int:
        """Stop all heartbeats."""
        count = 0
        for heartbeat in list(self._heartbeats.values()):
            if heartbeat.is_active:
                await heartbeat.stop()
                count += 1
        return count

    async def handle_pong(self, connection_id: str, data: str | None = None) -> bool:
        """Handle pong message for a connection."""
        heartbeat = self._heartbeats.get(connection_id)
        if heartbeat:
            return await heartbeat.handle_pong(data)
        return False

    async def cleanup_failed_connections(self) -> list[str]:
        """Clean up failed connections."""
        failed_connections = []

        for conn_id, heartbeat in list(self._heartbeats.items()):
            if heartbeat.state == HeartbeatState.FAILED:
                failed_connections.append(conn_id)
                await self.remove_connection(conn_id)

        if failed_connections:
            self._stats['failed_connections'] += len(failed_connections)
            logger.info(f'Cleaned up {len(failed_connections)} failed connections')

            # Call cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    callback(failed_connections)
                except Exception as e:
                    logger.error(f'Error in cleanup callback: {e}')

        return failed_connections

    def _handle_heartbeat_failure(self, heartbeat: Heartbeat) -> None:
        """Handle heartbeat failure."""
        logger.debug(f'Heartbeat failure for {heartbeat.connection_id}')

        # Call failure callbacks
        for callback in self._connection_failed_callbacks:
            try:
                callback(heartbeat.connection_id, heartbeat)
            except Exception as e:
                logger.error(f'Error in connection failed callback: {e}')

    def _handle_heartbeat_success(self, heartbeat: Heartbeat) -> None:
        """Handle heartbeat success."""
        logger.debug(f'Heartbeat success for {heartbeat.connection_id}')

        # Call recovery callbacks if this was a recovery
        if heartbeat.consecutive_failures > 0:
            for callback in self._connection_recovered_callbacks:
                try:
                    callback(heartbeat.connection_id, heartbeat)
                except Exception as e:
                    logger.error(f'Error in connection recovered callback: {e}')

    def _handle_heartbeat_disconnect(self, heartbeat: Heartbeat) -> None:
        """Handle heartbeat disconnect."""
        logger.info(f'Connection {heartbeat.connection_id} disconnected')

        # Schedule removal
        asyncio.create_task(self.remove_connection(heartbeat.connection_id))

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        try:
            while self._running:
                await asyncio.sleep(self.cleanup_interval)

                if not self._running:
                    break

                await self.cleanup_failed_connections()
                self._stats['cleanup_runs'] += 1

        except asyncio.CancelledError:
            logger.debug('Cleanup loop cancelled')
        except Exception as e:
            logger.error(f'Error in cleanup loop: {e}')
