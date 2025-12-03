"""Database session management utilities for Velithon.

This module provides utilities for managing database sessions,
including dependency injection helpers and request-scoped session management.
"""

from contextvars import ContextVar
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from velithon.database.manager import Database

# Context variable for storing the current database session
_current_session: ContextVar[Optional[AsyncSession]] = ContextVar(
    "current_session", default=None
)

# Context variable for storing the database instance
_current_database: ContextVar[Optional[Database]] = ContextVar(
    "current_database", default=None
)


async def get_db(database: Database) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for dependency injection.

    This is an async generator that yields a database session and
    automatically handles cleanup.

    Args:
        database: Database instance

    Yields:
        AsyncSession instance

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with database.session() as session:
        # Store session in context for potential access
        token = _current_session.set(session)
        try:
            yield session
        finally:
            _current_session.reset(token)


def get_current_session() -> Optional[AsyncSession]:
    """Get the current database session from context.

    Returns:
        Current AsyncSession if available, None otherwise

    Example:
        session = get_current_session()
        if session:
            result = await session.execute(select(User))
    """
    return _current_session.get()


def set_current_session(session: Optional[AsyncSession]) -> None:
    """Set the current database session in context.

    Args:
        session: AsyncSession to set as current

    Example:
        async with db.session() as session:
            set_current_session(session)
            # Now session is available via get_current_session()
    """
    _current_session.set(session)


def get_current_database() -> Optional[Database]:
    """Get the current database instance from context.

    Returns:
        Current Database instance if available, None otherwise
    """
    return _current_database.get()


def set_current_database(database: Optional[Database]) -> None:
    """Set the current database instance in context.

    Args:
        database: Database instance to set as current
    """
    _current_database.set(database)


class SessionManager:
    """Manager for database sessions with context support.

    This class provides a convenient way to manage database sessions
    with automatic context variable handling.
    """

    def __init__(self, database: Database):
        """Initialize the session manager.

        Args:
            database: Database instance
        """
        self.database = database
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        """Async context manager entry.

        Returns:
            AsyncSession instance
        """
        session_cm = self.database.session()
        self._session = await session_cm.__aenter__()
        set_current_session(self._session)
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        set_current_session(None)
        if self._session is not None:
            session_cm = self.database.session()
            await session_cm.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None
