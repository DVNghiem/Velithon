"""Transaction management utilities for Velithon.

This module provides utilities for managing database transactions,
including context managers and decorators.
"""

import functools
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from velithon.database.session import get_current_session

logger = logging.getLogger(__name__)

T = TypeVar("T")


@asynccontextmanager
async def transaction(
    session: Optional[AsyncSession] = None,
    *,
    nested: bool = False,
) -> AsyncGenerator[AsyncSession, None]:
    """Create a transaction context manager.

    This context manager automatically commits the transaction on success
    and rolls back on exceptions.

    Args:
        session: Database session (uses current session if None)
        nested: Whether to create a nested transaction (savepoint)

    Yields:
        AsyncSession instance

    Example:
        async with transaction() as session:
            user = User(name="John")
            session.add(user)
            # Automatically commits on success

        # Or with explicit session
        async with db.session() as session:
            async with transaction(session):
                user = User(name="John")
                session.add(user)
    """
    if session is None:
        session = get_current_session()
        if session is None:
            raise RuntimeError(
                "No active database session. "
                "Either pass a session or ensure one is set in context."
            )

    if nested:
        async with session.begin_nested():
            yield session
    else:
        async with session.begin():
            yield session


def transactional(
    *,
    nested: bool = False,
    commit: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to wrap a function in a transaction.

    Args:
        nested: Whether to create a nested transaction (savepoint)
        commit: Whether to auto-commit on success (default: True)

    Returns:
        Decorator function

    Example:
        @transactional()
        async def create_user(name: str) -> User:
            session = get_current_session()
            user = User(name=name)
            session.add(user)
            return user

        # With nested transaction
        @transactional(nested=True)
        async def create_user_with_profile(name: str) -> User:
            session = get_current_session()
            user = User(name=name)
            session.add(user)
            await session.flush()
            
            profile = Profile(user_id=user.id)
            session.add(profile)
            return user
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            session = get_current_session()
            if session is None:
                raise RuntimeError(
                    "No active database session. "
                    "Ensure a session is set in context before using @transactional."
                )

            if nested:
                async with session.begin_nested():
                    result = await func(*args, **kwargs)
                    if commit:
                        await session.commit()
                    return result
            else:
                # Check if we're already in a transaction
                if session.in_transaction():
                    # Just execute the function without starting a new transaction
                    return await func(*args, **kwargs)
                
                async with session.begin():
                    result = await func(*args, **kwargs)
                    if commit:
                        await session.commit()
                    return result

        return wrapper

    return decorator


class TransactionManager:
    """Manager for database transactions.

    This class provides methods for managing transactions programmatically.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the transaction manager.

        Args:
            session: Database session
        """
        self.session = session

    async def begin(self) -> None:
        """Begin a new transaction."""
        await self.session.begin()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

    async def savepoint(self, name: Optional[str] = None) -> Any:
        """Create a savepoint.

        Args:
            name: Optional savepoint name

        Returns:
            Savepoint object
        """
        return await self.session.begin_nested()

    def in_transaction(self) -> bool:
        """Check if currently in a transaction.

        Returns:
            True if in transaction, False otherwise
        """
        return self.session.in_transaction()

    @asynccontextmanager
    async def atomic(
        self, *, nested: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        """Create an atomic transaction context.

        Args:
            nested: Whether to create a nested transaction

        Yields:
            AsyncSession instance

        Example:
            tx_manager = TransactionManager(session)
            async with tx_manager.atomic():
                user = User(name="John")
                session.add(user)
        """
        async with transaction(self.session, nested=nested):
            yield self.session
