"""Database manager module for Velithon.

This module provides the main Database class for managing SQLAlchemy
async engine and session factory.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from velithon.database.config import DatabaseConfig

logger = logging.getLogger(__name__)


class Database:
    """Database manager for Velithon applications.

    This class manages the SQLAlchemy async engine and session factory,
    providing methods for connection lifecycle management and health checks.
    """

    def __init__(self, config: DatabaseConfig):
        """Initialize the Database manager.

        Args:
            config: Database configuration
        """
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._is_connected = False

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine.

        Returns:
            AsyncEngine instance

        Raises:
            RuntimeError: If database is not connected
        """
        if self._engine is None:
            raise RuntimeError(
                "Database is not connected. Call connect() first."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory.

        Returns:
            Session factory instance

        Raises:
            RuntimeError: If database is not connected
        """
        if self._session_factory is None:
            raise RuntimeError(
                "Database is not connected. Call connect() first."
            )
        return self._session_factory

    @property
    def is_connected(self) -> bool:
        """Check if database is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._is_connected

    async def connect(self) -> None:
        """Connect to the database.

        Creates the async engine and session factory.
        """
        if self._is_connected:
            logger.warning("Database is already connected")
            return

        logger.info(f"Connecting to database: {self._mask_url(self.config.url)}")

        # Determine pool class and engine args based on database type
        is_sqlite = "sqlite" in self.config.url
        
        engine_args = {
            "echo": self.config.echo,
            "connect_args": self.config.connect_args,
            "execution_options": self.config.execution_options,
        }
        
        if is_sqlite:
            # SQLite doesn't support connection pooling well in async mode
            engine_args["poolclass"] = NullPool
        else:
            # Use QueuePool for other databases
            engine_args.update({
                "poolclass": QueuePool,
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping,
            })

        # Create async engine
        self._engine = create_async_engine(
            self.config.url,
            **engine_args,
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self._is_connected = True
        logger.info("Database connected successfully")

    async def disconnect(self) -> None:
        """Disconnect from the database.

        Disposes the engine and cleans up resources.
        """
        if not self._is_connected:
            logger.warning("Database is not connected")
            return

        logger.info("Disconnecting from database")

        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

        self._session_factory = None
        self._is_connected = False
        logger.info("Database disconnected successfully")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a new database session.

        This is a context manager that automatically handles session cleanup.

        Yields:
            AsyncSession instance

        Example:
            async with db.session() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
        """
        if not self._is_connected:
            raise RuntimeError(
                "Database is not connected. Call connect() first."
            )

        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def ping(self) -> bool:
        """Ping the database to check connectivity.

        Returns:
            True if database is reachable, False otherwise
        """
        if not self._is_connected:
            return False

        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False

    async def get_pool_status(self) -> dict[str, Any]:
        """Get connection pool status.

        Returns:
            Dictionary with pool statistics
        """
        if not self._is_connected or self._engine is None:
            return {
                "connected": False,
                "pool_size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
            }

        pool = self._engine.pool
        
        # Handle NullPool (SQLite)
        if isinstance(pool, NullPool):
            return {
                "connected": True,
                "pool_type": "NullPool",
                "note": "SQLite uses NullPool (no connection pooling)",
            }

        return {
            "connected": True,
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "timeout": self.config.pool_timeout,
        }

    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL.

        Args:
            url: Database URL

        Returns:
            Masked URL with password hidden
        """
        if "://" not in url:
            return url

        scheme, rest = url.split("://", 1)
        
        if "@" not in rest:
            return url

        credentials, host_part = rest.split("@", 1)
        
        if ":" in credentials:
            username, _ = credentials.split(":", 1)
            return f"{scheme}://{username}:***@{host_part}"
        
        return url

    async def __aenter__(self) -> "Database":
        """Async context manager entry.

        Returns:
            Database instance
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        await self.disconnect()
