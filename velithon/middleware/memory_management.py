"""Memory management middleware for Velithon framework.

This middleware provides automatic memory management for web requests,
including garbage collection management and memory monitoring.
"""

import time
from typing import Any, Callable

from velithon.datastructures import Protocol, Scope
from velithon.memory_management import RequestMemoryContext, get_memory_optimizer
from velithon.middleware import Middleware


class MemoryManagementMiddleware(Middleware):
    """Middleware that applies memory management to web requests."""

    def __init__(
        self,
        app: Callable[[Scope, Protocol], Any],
        enable_monitoring: bool = True,
        cleanup_threshold: int = 1000,
        cleanup_interval: float = 300.0,  # 5 minutes
    ):
        """Initialize memory management middleware.

        Args:
            app: The RSGI application
            enable_monitoring: Whether to enable memory monitoring
            cleanup_threshold: Object count threshold for triggering cleanup
            cleanup_interval: Interval between periodic cleanups (seconds)

        """
        super().__init__(app)
        self.enable_monitoring = enable_monitoring
        self.cleanup_threshold = cleanup_threshold
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = 0.0
        self._request_count = 0
        self.memory_optimizer = get_memory_optimizer()

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Process request with memory management."""
        self._request_count += 1

        # Use lightweight memory monitoring to reduce overhead
        enable_monitoring = self.enable_monitoring and (self._request_count % 10 == 0)

        # Use memory-optimized request context
        with RequestMemoryContext(enable_monitoring=enable_monitoring):
            # Check if periodic cleanup is needed
            current_time = time.time()
            if (current_time - self._last_cleanup) > self.cleanup_interval:
                await self._periodic_cleanup()
                self._last_cleanup = current_time

            # Process the request
            await self.app(scope, protocol)

            # Trigger cleanup based on request count (less frequently)
            if self._request_count % (self.cleanup_threshold * 2) == 0:
                self.memory_optimizer.gc_optimizer.manual_collection(0)

    async def _periodic_cleanup(self) -> None:
        """Perform periodic memory cleanup."""
        # Check memory usage and trigger cleanup if needed
        self.memory_optimizer.memory_monitor.check_memory_usage()

        # Perform light garbage collection
        self.memory_optimizer.gc_optimizer.manual_collection(1)


class GCTuningMiddleware(Middleware):
    """Middleware for fine-tuning garbage collection during request processing."""

    def __init__(
        self,
        app: Callable[[Scope, Protocol], Any],
        disable_gc_during_request: bool = True,
        generation_0_interval: int = 100,  # Clean gen 0 every N requests
        generation_2_interval: int = 1000,  # Clean gen 2 every N requests
    ):
        """Initialize GC tuning middleware.

        Args:
            app: The RSGI application
            disable_gc_during_request: Whether to disable GC during request processing
            generation_0_interval: Requests between generation 0 collections
            generation_2_interval: Requests between generation 2 collections

        """
        super().__init__(app)
        self.disable_gc_during_request = disable_gc_during_request
        self.generation_0_interval = generation_0_interval
        self.generation_2_interval = generation_2_interval
        self._request_count = 0
        self.memory_optimizer = get_memory_optimizer()

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Process request with GC tuning."""
        import gc

        self._request_count += 1

        # Disable GC during request processing if configured
        gc_was_enabled = gc.isenabled()
        if self.disable_gc_during_request and gc_was_enabled:
            gc.disable()

        try:
            # Process the request
            await self.app(scope, protocol)
        finally:
            # Re-enable GC if it was disabled
            if self.disable_gc_during_request and gc_was_enabled:
                gc.enable()

            # Perform scheduled garbage collection
            await self._scheduled_gc()

    async def _scheduled_gc(self) -> None:
        """Perform scheduled garbage collection based on request count."""
        # Generation 0 cleanup (frequent, lightweight)
        if self._request_count % self.generation_0_interval == 0:
            self.memory_optimizer.gc_optimizer.manual_collection(0)

        # Generation 2 cleanup (infrequent, comprehensive)
        if self._request_count % self.generation_2_interval == 0:
            self.memory_optimizer.gc_optimizer.manual_collection(2)

