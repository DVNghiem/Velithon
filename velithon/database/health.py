"""Database health check implementation for Velithon.

This module provides health check functionality for database connections
and connection pool monitoring.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from velithon.database.manager import Database

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DatabaseHealthResponse(BaseModel):
    """Database health check response model."""

    status: HealthStatus = Field(
        ...,
        description="Overall health status",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the health check",
    )
    database_connected: bool = Field(
        ...,
        description="Whether database is connected",
    )
    database_reachable: bool = Field(
        ...,
        description="Whether database is reachable (ping successful)",
    )
    pool_status: dict[str, Any] | None = Field(
        default=None,
        description="Connection pool status",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Database ping response time in milliseconds",
    )
    error: str | None = Field(
        default=None,
        description="Error message if unhealthy",
    )


class DatabaseHealthCheck:
    """Database health check implementation.

    This class provides methods for checking database health,
    including connectivity and connection pool status.
    """

    def __init__(self, database: Database):
        """Initialize the health check.

        Args:
            database: Database instance

        """
        self.database = database

    async def check_health(self) -> DatabaseHealthResponse:
        """Perform a comprehensive health check.

        Returns:
            DatabaseHealthResponse with health status

        """
        import time

        connected = self.database.is_connected
        reachable = False
        response_time_ms = None
        error = None
        pool_status = None

        # Check if database is reachable
        if connected:
            try:
                start_time = time.perf_counter()
                reachable = await self.database.ping()
                end_time = time.perf_counter()
                response_time_ms = (end_time - start_time) * 1000

                # Get pool status
                pool_status = await self.database.get_pool_status()

            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                error = str(e)
                reachable = False

        # Determine overall status
        if not connected:
            status = HealthStatus.UNHEALTHY
            error = "Database is not connected"
        elif not reachable:
            status = HealthStatus.UNHEALTHY
            error = error or "Database is not reachable"
        elif pool_status and self._is_pool_degraded(pool_status):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return DatabaseHealthResponse(
            status=status,
            database_connected=connected,
            database_reachable=reachable,
            pool_status=pool_status,
            response_time_ms=response_time_ms,
            error=error,
        )

    def _is_pool_degraded(self, pool_status: dict[str, Any]) -> bool:
        """Check if connection pool is in a degraded state.

        Args:
            pool_status: Pool status dictionary

        Returns:
            True if pool is degraded, False otherwise

        """
        # Skip check for NullPool (SQLite)
        if pool_status.get("pool_type") == "NullPool":
            return False

        pool_size = pool_status.get("pool_size", 0)
        checked_out = pool_status.get("checked_out", 0)
        overflow = pool_status.get("overflow", 0)

        # Pool is degraded if:
        # 1. More than 80% of connections are checked out
        # 2. Overflow is being used
        if pool_size > 0:
            utilization = checked_out / pool_size
            if utilization > 0.8 or overflow > 0:
                return True

        return False

    async def get_metrics(self) -> dict[str, Any]:
        """Get database metrics.

        Returns:
            Dictionary with database metrics

        """
        health = await self.check_health()

        metrics = {
            "status": health.status.value,
            "connected": health.database_connected,
            "reachable": health.database_reachable,
            "response_time_ms": health.response_time_ms,
        }

        if health.pool_status:
            metrics["pool"] = health.pool_status

        if health.error:
            metrics["error"] = health.error

        return metrics
