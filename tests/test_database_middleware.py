"""Tests for database middleware."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from velithon.database import Database, SQLiteConfig, Base
from velithon.database.session import get_current_session, set_current_session
from velithon.middleware.database_middleware import (
    DatabaseSessionMiddleware,
    TransactionMiddleware,
)


class TestDatabaseSessionMiddleware:
    """Tests for DatabaseSessionMiddleware."""

    @pytest_asyncio.fixture
    async def database(self):
        """Create test database."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()
        
        # Create tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield db
        
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_session_middleware(self, database):
        """Test session middleware creates and cleans up session."""
        # Create mock app
        app_called = False
        session_in_app = None

        async def mock_app(scope, protocol):
            nonlocal app_called, session_in_app
            app_called = True
            session_in_app = get_current_session()

        # Create middleware
        middleware = DatabaseSessionMiddleware(mock_app, database)

        # Create mock scope and protocol
        scope = MagicMock()
        scope.proto = "http"
        protocol = MagicMock()

        # Call middleware
        await middleware(scope, protocol)

        # Verify app was called
        assert app_called is True
        
        # Verify session was available in app
        assert session_in_app is not None
        
        # Verify session was cleaned up
        assert get_current_session() is None

    @pytest.mark.asyncio
    async def test_session_attached_to_scope(self, database):
        """Test that session is attached to scope."""
        async def mock_app(scope, protocol):
            assert hasattr(scope, "_db_session")
            assert scope._db_session is not None

        middleware = DatabaseSessionMiddleware(mock_app, database)
        
        scope = MagicMock()
        scope.proto = "http"
        protocol = MagicMock()

        await middleware(scope, protocol)


class TestTransactionMiddleware:
    """Tests for TransactionMiddleware."""

    @pytest_asyncio.fixture
    async def database(self):
        """Create test database."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()
        
        # Create tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield db
        
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_transaction_middleware_commit(self, database):
        """Test transaction middleware commits on success."""
        # Create session
        async with database.session() as session:
            set_current_session(session)
            
            async def mock_app(scope, protocol):
                # Do nothing, should commit
                pass

            middleware = TransactionMiddleware(mock_app, auto_commit=True)
            
            scope = MagicMock()
            scope.proto = "http"
            scope._db_session = session
            protocol = MagicMock()

            await middleware(scope, protocol)
            
            # Transaction should be committed
            assert not session.in_transaction()

    @pytest.mark.asyncio
    async def test_transaction_middleware_rollback(self, database):
        """Test transaction middleware rolls back on error."""
        # Create session
        async with database.session() as session:
            set_current_session(session)
            
            async def mock_app(scope, protocol):
                raise ValueError("Test error")

            middleware = TransactionMiddleware(
                mock_app,
                auto_commit=True,
                rollback_on_error=True,
            )
            
            scope = MagicMock()
            scope.proto = "http"
            scope._db_session = session
            protocol = MagicMock()

            with pytest.raises(ValueError):
                await middleware(scope, protocol)

    @pytest.mark.asyncio
    async def test_transaction_middleware_no_session(self):
        """Test transaction middleware handles missing session."""
        async def mock_app(scope, protocol):
            pass

        middleware = TransactionMiddleware(mock_app)
        
        scope = MagicMock()
        scope.proto = "http"
        # No _db_session attribute
        protocol = MagicMock()

        # Should not raise, just log warning
        await middleware(scope, protocol)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
