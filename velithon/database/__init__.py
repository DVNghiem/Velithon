"""Velithon Database Module.

This module provides database integration for Velithon applications,
including SQLAlchemy async support, connection pooling, transaction management,
and repository pattern implementation.
"""

from velithon.database.config import (
    DatabaseConfig,
    MySQLConfig,
    PostgreSQLConfig,
    SQLiteConfig,
)
from velithon.database.health import DatabaseHealthCheck, DatabaseHealthResponse
from velithon.database.manager import Database
from velithon.database.repository import BaseRepository
from velithon.database.session import (
    SessionManager,
    get_current_database,
    get_current_session,
    get_db,
    set_current_database,
    set_current_session,
)
from velithon.database.sqlalchemy_adapter import (
    Base,
    get_model_columns,
    get_model_primary_keys,
    get_model_relationships,
)
from velithon.database.transaction import (
    TransactionManager,
    transaction,
    transactional,
)

__all__ = [
    # Configuration
    "DatabaseConfig",
    "PostgreSQLConfig",
    "MySQLConfig",
    "SQLiteConfig",
    # Core
    "Database",
    # Session management
    "get_db",
    "get_current_session",
    "set_current_session",
    "get_current_database",
    "set_current_database",
    "SessionManager",
    # Transaction management
    "transaction",
    "transactional",
    "TransactionManager",
    # SQLAlchemy
    "Base",
    "get_model_columns",
    "get_model_primary_keys",
    "get_model_relationships",
    # Repository
    "BaseRepository",
    # Health check
    "DatabaseHealthCheck",
    "DatabaseHealthResponse",
]
