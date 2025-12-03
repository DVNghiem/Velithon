"""Tests for database core functionality."""

import pytest
import pytest_asyncio
from sqlalchemy import String
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
            assert not session.is_active

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
