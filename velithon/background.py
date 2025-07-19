"""Background task management for Velithon framework.

This module provides BackgroundTask and BackgroundTasks classes for handling
asynchronous tasks that should run independently from request handling.
"""

from __future__ import annotations

from velithon._velithon import BackgroundTask, BackgroundTasks

__all__ = [
    'BackgroundTask',
    'BackgroundTasks',
]
