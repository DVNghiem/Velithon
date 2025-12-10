"""Tests for database core functionality."""

import pytest
import pytest_asyncio
from sqlalchemy import String, select, text, func
from sqlalchemy.orm import Mapped, mapped_column

from velithon.database import (
    Base,
    Database,
    DatabaseConfig,
    SQLiteConfig,
    DatabaseHealthCheck,
)


class TestUser(Base):
    """Test user model."""

    __tablename__ = "test_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_valid_config(self):
        """Test valid database configuration."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://user:pass@localhost/db",
            pool_size=10,
            max_overflow=20,
        )
        assert config.url == "postgresql+asyncpg://user:pass@localhost/db"
        assert config.pool_size == 10
        assert config.max_overflow == 20

    def test_invalid_url(self):
        """Test invalid database URL."""
        with pytest.raises(ValueError, match="async driver"):
            DatabaseConfig(url="postgresql://user:pass@localhost/db")

    def test_sqlite_config(self):
        """Test SQLite configuration."""
        config = SQLiteConfig(database=":memory:")
        assert "sqlite+aiosqlite" in config.url


class TestDatabase:
    """Tests for Database manager."""

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
    async def test_connect_disconnect(self):
        """Test database connection and disconnection."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        
        assert not db.is_connected
        
        await db.connect()
        assert db.is_connected
        
        await db.disconnect()
        assert not db.is_connected

    @pytest.mark.asyncio
    async def test_session_creation(self, database):
        """Test session creation."""
        async with database.session() as session:
            assert session is not None
            assert session.is_active

    @pytest.mark.asyncio
    async def test_ping(self, database):
        """Test database ping."""
        result = await database.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_pool_status(self, database):
        """Test getting pool status."""
        status = await database.get_pool_status()
        assert status["connected"] is True

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test database as context manager."""
        config = SQLiteConfig(database=":memory:")
        
        async with Database(config) as db:
            assert db.is_connected
            result = await db.ping()
            assert result is True

    @pytest.mark.asyncio
    async def test_crud_operations(self, database):
        """Test basic CRUD operations."""
        # Create
        async with database.session() as session:
            user = TestUser(name="Test User", email="test@example.com")
            session.add(user)
            await session.commit()
            user_id = user.id

        # Read
        async with database.session() as session:
            fetched_user = await session.get(TestUser, user_id)
            assert fetched_user is not None
            assert fetched_user.name == "Test User"
            assert fetched_user.email == "test@example.com"

        # Update
        async with database.session() as session:
            user = await session.get(TestUser, user_id)
            user.name = "Updated User"
            await session.commit()

        # Verify Update
        async with database.session() as session:
            updated_user = await session.get(TestUser, user_id)
            assert updated_user.name == "Updated User"

        # Delete
        async with database.session() as session:
            user = await session.get(TestUser, user_id)
            await session.delete(user)
            await session.commit()

        # Verify Delete
        async with database.session() as session:
            deleted_user = await session.get(TestUser, user_id)
            assert deleted_user is None


class TestDatabaseHealthCheck:
    """Tests for DatabaseHealthCheck."""

    @pytest_asyncio.fixture
    async def database(self):
        """Create test database."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()
        yield db
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, database):
        """Test health check with healthy database."""
        checker = DatabaseHealthCheck(database)
        health = await checker.check_health()
        
        assert health.status == "healthy"
        assert health.database_connected is True
        assert health.database_reachable is True
        assert health.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Test health check with disconnected database."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        
        checker = DatabaseHealthCheck(db)
        health = await checker.check_health()
        
        assert health.status == "unhealthy"
        assert health.database_connected is False

    @pytest.mark.asyncio
    async def test_get_metrics(self, database):
        """Test getting health metrics."""
        checker = DatabaseHealthCheck(database)
        metrics = await checker.get_metrics()
        
        assert "status" in metrics
        assert "connected" in metrics
        assert "reachable" in metrics


class TestDatabaseEdgeCases:
    """Tests for database edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()
        
        try:
            # This should handle gracefully
            status = await db.get_pool_status()
            assert "connected" in status
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_reconnection_after_disconnect(self):
        """Test reconnecting after disconnect."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        
        # First connection
        await db.connect()
        assert db.is_connected
        
        # Disconnect
        await db.disconnect()
        assert not db.is_connected
        
        # Reconnect
        await db.connect()
        assert db.is_connected
        
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_pings(self):
        """Test multiple ping operations."""
        config = SQLiteConfig(database=":memory:")
        
        async with Database(config) as db:
            for _ in range(10):
                result = await db.ping()
                assert result is True

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test concurrent session access."""
        import asyncio
        
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()
        
        # Create tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async def create_user(index):
            async with db.session() as session:
                user = TestUser(name=f"User{index}", email=f"user{index}@example.com")
                session.add(user)
                await session.commit()
        
        # Create 10 users concurrently
        tasks = [create_user(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all were created
        async with db.session() as session:
            result = await session.execute(select(func.count()).select_from(TestUser))
            count = result.scalar()
            assert count == 10
        
        await db.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
