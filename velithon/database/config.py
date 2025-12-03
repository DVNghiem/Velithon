"""Database configuration module for Velithon.

This module provides configuration classes for database connections,
connection pooling, and other database-related settings.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatabaseConfig(BaseModel):
    """Database configuration model.

    This class defines all configuration options for database connections,
    including connection URL, pool settings, and other database-specific options.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
    )

    url: str = Field(
        ...,
        description="Database connection URL (e.g., 'postgresql+asyncpg://user:pass@localhost/db')",
    )
    echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging for debugging",
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        description="Number of connections to maintain in the pool",
    )
    max_overflow: int = Field(
        default=10,
        ge=0,
        description="Maximum number of connections that can be created beyond pool_size",
    )
    pool_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Timeout in seconds for getting a connection from the pool",
    )
    pool_recycle: int = Field(
        default=3600,
        ge=-1,
        description="Recycle connections after this many seconds (-1 to disable)",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Test connections for liveness before using them",
    )
    connect_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional arguments to pass to the database driver",
    )
    execution_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution options for the engine",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("Database URL cannot be empty")
        
        # Check for async driver support
        async_drivers = [
            "postgresql+asyncpg",
            "mysql+aiomysql",
            "sqlite+aiosqlite",
        ]
        
        if not any(driver in v for driver in async_drivers):
            raise ValueError(
                f"Database URL must use an async driver. "
                f"Supported drivers: {', '.join(async_drivers)}"
            )
        
        return v

    @field_validator("pool_size")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Validate pool size is reasonable."""
        if v > 100:
            raise ValueError("pool_size should not exceed 100 for most applications")
        return v

    @field_validator("max_overflow")
    @classmethod
    def validate_max_overflow(cls, v: int) -> int:
        """Validate max overflow is reasonable."""
        if v > 100:
            raise ValueError("max_overflow should not exceed 100 for most applications")
        return v


class PostgreSQLConfig(DatabaseConfig):
    """PostgreSQL-specific configuration."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: str = "",
        **kwargs: Any,
    ):
        """Initialize PostgreSQL configuration.

        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            **kwargs: Additional configuration options
        """
        url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
        super().__init__(url=url, **kwargs)


class MySQLConfig(DatabaseConfig):
    """MySQL-specific configuration."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        database: str = "mysql",
        username: str = "root",
        password: str = "",
        **kwargs: Any,
    ):
        """Initialize MySQL configuration.

        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: Database password
            **kwargs: Additional configuration options
        """
        url = f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}"
        super().__init__(url=url, **kwargs)


class SQLiteConfig(DatabaseConfig):
    """SQLite-specific configuration."""

    def __init__(
        self,
        database: str = ":memory:",
        **kwargs: Any,
    ):
        """Initialize SQLite configuration.

        Args:
            database: Database file path or ':memory:' for in-memory database
            **kwargs: Additional configuration options
        """
        url = f"sqlite+aiosqlite:///{database}"
        super().__init__(url=url, **kwargs)
