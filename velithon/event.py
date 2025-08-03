
"""
Event handling system for Velithon.

This module provides the EventChannel class, which enables registering listeners
and emitting events across the application using a Rust-powered backend for high
performance.
"""

import asyncio
import typing

from velithon._velithon import RustEventChannel


class EventChannel(RustEventChannel):
    """EventChannel is a global event handling system for Velithon.

    It allows for registering listeners and emitting events across the application.
    """

    def __init__(self, buffer_size: int = 1000):
        """Initialize the EventChannel with an optional buffer size for event handling.""" # noqa: E501
        self.buffer_size = buffer_size
        self.events: list[tuple[str, typing.Callable, bool]] = []

    def on_event(self, event_name: str):
        """Register a listener for a specific event.

        Args:
            event_name: The name of the event to listen for.

        """
        def decorator(func):
            is_async = asyncio.iscoroutinefunction(func)
            self.events.append((event_name, func, is_async))
            return func
        return decorator
