"""Database middleware for Velithon.

This module provides middleware components for managing database sessions
and transactions in Velithon applications.
"""

import logging
from collections.abc import Callable

from velithon.database.manager import Database
from velithon.database.session import set_current_database, set_current_session
from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """Middleware for managing request-scoped database sessions.

    This middleware creates a database session for each request and
    makes it available via context variables. The session is automatically
    cleaned up after the request completes.
    """

    def __init__(
        self,
        app: Callable[[Scope, Protocol], None],
        database: Database,
    ):
        """Initialize the middleware.

        Args:
            app: RSGI application
            database: Database instance

        """
        super().__init__(app)
        self.database = database

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request with database session.

        Args:
            scope: Request scope
            protocol: Protocol instance

        """
        # Set database in context
        set_current_database(self.database)

        # Create session for this request
        async with self.database.session() as session:
            # Set session in context
            set_current_session(session)

            # Attach session to scope for easy access
            scope._db_session = session

            try:
                # Call next middleware/handler
                await self.app(scope, protocol)
            finally:
                # Clean up context
                set_current_session(None)
                set_current_database(None)


class TransactionMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic transaction management.

    This middleware wraps each request in a database transaction,
    automatically committing on success and rolling back on exceptions.
    """

    def __init__(
        self,
        app: Callable[[Scope, Protocol], None],
        *,
        auto_commit: bool = True,
        rollback_on_error: bool = True,
    ):
        """Initialize the middleware.

        Args:
            app: RSGI application
            auto_commit: Whether to auto-commit transactions on success
            rollback_on_error: Whether to rollback on exceptions

        """
        super().__init__(app)
        self.auto_commit = auto_commit
        self.rollback_on_error = rollback_on_error

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request with transaction management.

        Args:
            scope: Request scope
            protocol: Protocol instance

        """
        # Get session from scope (set by DatabaseSessionMiddleware)
        session = getattr(scope, '_db_session', None)

        if session is None:
            logger.warning(
                'No database session found in scope. '
                'Ensure DatabaseSessionMiddleware is added' 
                'before TransactionMiddleware.'
            )
            await self.app(scope, protocol)
            return

        # Start transaction
        async with session.begin():
            try:
                # Call next middleware/handler
                await self.app(scope, protocol)

                # Auto-commit if enabled
                if self.auto_commit:
                    await session.commit()

            except Exception as e:
                # Rollback on error if enabled
                if self.rollback_on_error:
                    logger.error(f'Rolling back transaction due to error: {e}')
                    await session.rollback()
                raise
