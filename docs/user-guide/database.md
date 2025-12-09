# Database Integration

Velithon provides comprehensive database integration built on top of SQLAlchemy with async support. The database module offers a high-performance, production-ready solution for database operations including ORM support, connection pooling, transaction management, and migration tools.

## Features

- **Async SQLAlchemy Support**: Full async/await support for database operations
- **Multiple Database Backends**: PostgreSQL, MySQL, and SQLite support
- **Repository Pattern**: Clean separation of data access logic
- **Transaction Management**: Automatic and manual transaction handling
- **Connection Pooling**: Efficient connection management with configurable pools
- **Migration Support**: Alembic integration for schema migrations
- **Health Checks**: Built-in database health monitoring
- **Middleware Integration**: Seamless integration with Velithon's middleware system

## Quick Start

### Basic Setup

```python
from velithon import Velithon
from velithon.database import Database, SQLiteConfig

# Create database configuration
db_config = SQLiteConfig(database="app.db")
database = Database(db_config)

# Create Velithon app
app = Velithon()

# Attach database to app (for CLI commands)
app.database = database

# Startup event to initialize database
@app.router.on_event("startup")
async def startup():
    await database.connect()

    # Create tables
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Shutdown event to cleanup
@app.router.on_event("shutdown")
async def shutdown():
    await database.disconnect()
```

### Model Definition

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from velithon.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

### Repository Pattern

```python
from velithon.database import BaseRepository
from velithon.database.session import get_current_session

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.get_by(email=email)

# Usage in endpoint
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    session = get_current_session()
    repo = UserRepository(User, session)
    user = await repo.get(user_id)

    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)

    return JSONResponse(user.to_dict())
```

## Database Configuration

### PostgreSQL

```python
from velithon.database import PostgreSQLConfig

db_config = PostgreSQLConfig(
    host="localhost",
    port=5432,
    database="myapp",
    username="myuser",
    password="mypassword",
    pool_size=10,
    max_overflow=20,
    echo=True  # Enable SQL logging
)
```

### MySQL

```python
from velithon.database import MySQLConfig

db_config = MySQLConfig(
    host="localhost",
    port=3306,
    database="myapp",
    username="myuser",
    password="mypassword"
)
```

### SQLite

```python
from velithon.database import SQLiteConfig

# File-based database
db_config = SQLiteConfig(database="app.db")

# In-memory database
db_config = SQLiteConfig(database=":memory:")
```

### Custom Configuration

```python
from velithon.database import DatabaseConfig

db_config = DatabaseConfig(
    url="postgresql+asyncpg://user:pass@localhost/db",
    pool_size=5,
    max_overflow=10,
    pool_timeout=30.0,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)
```

## Repository Operations

The `BaseRepository` class provides common CRUD operations:

### Create

```python
# Create single record
user = await repo.create(name="John Doe", email="john@example.com")

# Create multiple records
users = await repo.create_many([
    {"name": "John", "email": "john@example.com"},
    {"name": "Jane", "email": "jane@example.com"}
])
```

### Read

```python
# Get by ID
user = await repo.get(1)

# Get by filters
user = await repo.get_by(email="john@example.com")

# Get all with filters
users = await repo.get_all(limit=10, offset=0, active=True)

# Count records
total_users = await repo.count(active=True)

# Check existence
exists = await repo.exists(email="john@example.com")
```

### Update

```python
# Update single record
user = await repo.update(1, name="John Smith")

# Update multiple records
updated_count = await repo.update_many(
    filters={"status": "active"},
    values={"status": "inactive"}
)
```

### Delete

```python
# Delete single record
deleted = await repo.delete(1)

# Delete multiple records
deleted_count = await repo.delete_many(status="inactive")
```

### Pagination

```python
result = await repo.paginate(page=1, page_size=20)

# Result contains:
# {
#     'items': [...],      # List of records
#     'total': 100,        # Total count
#     'page': 1,           # Current page
#     'page_size': 20,     # Items per page
#     'total_pages': 5,    # Total pages
#     'has_next': True,    # Has next page
#     'has_prev': False    # Has previous page
# }
```

## Transaction Management

### Automatic Transactions

```python
from velithon.middleware import Middleware, TransactionMiddleware

# Add transaction middleware
app.user_middleware = [
    Middleware(TransactionMiddleware, auto_commit=True),
]
```

### Manual Transactions

```python
from velithon.database.transaction import transaction

@app.post("/users")
async def create_user():
    session = get_current_session()

    async with transaction(session):
        # All operations in this block are transactional
        user = await repo.create(name="John", email="john@example.com")
        profile = await profile_repo.create(user_id=user.id, bio="Hello!")

        return JSONResponse(user.to_dict())
```

### Transaction Decorator

```python
from velithon.database.transaction import transactional

@transactional
async def create_user_with_profile(name: str, email: str, bio: str):
    user = await user_repo.create(name=name, email=email)
    profile = await profile_repo.create(user_id=user.id, bio=bio)
    return user
```

## Session Management

### Current Session

```python
from velithon.database.session import get_current_session

@app.get("/users")
async def get_users():
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)

    repo = UserRepository(User, session)
    users = await repo.get_all()
    return JSONResponse({"users": [u.to_dict() for u in users]})
```

### Session Middleware

```python
from velithon.middleware import Middleware, DatabaseSessionMiddleware

app.user_middleware = [
    Middleware(DatabaseSessionMiddleware, database),
]
```

## Database Migrations

Velithon integrates with Alembic for database schema migrations.

### Initialize Migrations

```python
from velithon.database.migrations import MigrationManager

# Initialize migration directory
migration_manager = MigrationManager(
    database_url="postgresql+asyncpg://user:pass@localhost/db",
    migrations_dir="migrations"
)

migration_manager.init()
```

### Create Migration

```python
# Auto-generate migration from model changes
migration_manager.create_migration("add user table")

# Create empty migration
migration_manager.create_migration("custom changes", autogenerate=False)
```

### Run Migrations

```python
# Upgrade to latest
migration_manager.upgrade()

# Upgrade to specific revision
migration_manager.upgrade("abc123")

# Downgrade
migration_manager.downgrade("-1")  # One step back
migration_manager.downgrade("base")  # To beginning
```

### Migration Commands

```python
# Show current revision
migration_manager.current()

# Show migration history
migration_manager.history(verbose=True)

# Show specific migration details
migration_manager.show("abc123")

# Stamp database with revision (without running migrations)
migration_manager.stamp("abc123")
```

## Health Checks

```python
from velithon.database.health import DatabaseHealthCheck

@app.get("/health/db")
async def health_check():
    health_checker = DatabaseHealthCheck(database)
    health = await health_checker.check_health()
    return JSONResponse(health.model_dump())
```

The health check returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "response_time": 0.001,
  "database": {
    "connection": "healthy",
    "version": "PostgreSQL 15.0"
  }
}
```

## CLI Integration

When you attach a database to your app, you get CLI commands:

```bash
# Create tables
velithon db create-tables

# Drop tables
velithon db drop-tables

# Show current migration
velithon db migration current

# Create new migration
velithon db migration create "add user table"

# Run migrations
velithon db migration upgrade
```

## Best Practices

### Connection Pooling

- Use appropriate pool sizes for your workload
- Enable `pool_pre_ping` for production environments
- Set reasonable `pool_recycle` times

### Transactions

- Use transactions for related operations
- Keep transactions short to avoid locks
- Use automatic transaction middleware for simple cases

### Repository Pattern

- Create specific repository classes for complex queries
- Keep repositories focused on data access
- Use dependency injection for repository instances

### Migrations

- Always test migrations on staging before production
- Create descriptive migration messages
- Don't modify existing migrations - create new ones

### Performance

- Use `select` with specific columns when you don't need all data
- Implement proper indexing on frequently queried columns
- Use pagination for large result sets
- Consider read replicas for heavy read workloads

## Advanced Usage

### Custom Repository Methods

```python
class UserRepository(BaseRepository[User]):
    async def get_active_users_with_posts(self):
        stmt = (
            select(User)
            .join(Post)
            .where(User.active == True)
            .options(selectinload(User.posts))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_users(self, query: str, limit: int = 10):
        stmt = (
            select(User)
            .where(User.name.ilike(f"%{query}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Raw SQL Queries

```python
from sqlalchemy import text

async def get_user_stats():
    session = get_current_session()

    # Raw SQL query
    stmt = text("""
        SELECT
            COUNT(*) as total_users,
            COUNT(CASE WHEN active = true THEN 1 END) as active_users
        FROM users
    """)

    result = await session.execute(stmt)
    return result.mappings().first()
```

### Custom Model Methods

```python
class User(Base):
    # ... columns ...

    async def get_posts(self, session: AsyncSession):
        """Get user's posts."""
        stmt = select(Post).where(Post.user_id == self.id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"
```

## Error Handling

```python
from sqlalchemy.exc import IntegrityError, NoResultFound

@app.post("/users")
async def create_user(data: dict):
    session = get_current_session()
    repo = UserRepository(User, session)

    try:
        async with transaction(session):
            user = await repo.create(**data)
            return JSONResponse(user.to_dict(), status_code=201)

    except IntegrityError:
        return JSONResponse(
            {"error": "Email already exists"},
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500
        )
```

## Testing

```python
import pytest
from velithon.database import SQLiteConfig

@pytest.fixture
async def test_db():
    config = SQLiteConfig(database=":memory:")
    db = Database(config)
    await db.connect()

    # Create tables
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield db

    await db.disconnect()

@pytest.fixture
async def test_session(test_db):
    async with test_db.session() as session:
        yield session
```

## Production Considerations

### Environment Variables

```python
import os

db_config = PostgreSQLConfig(
    host=os.getenv("DB_HOST", "localhost"),
    database=os.getenv("DB_NAME", "myapp"),
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)
```

### Monitoring

- Monitor connection pool usage
- Track query performance
- Set up alerts for database issues
- Log slow queries

### Security

- Use strong passwords
- Limit database user permissions
- Use SSL/TLS connections
- Regularly update database software
- Implement proper input validation

For more examples, see the [database example](../examples/database_example.py) in the examples directory.</content>
<parameter name="filePath">/home/nghiem/project/Velithon/docs/user-guide/database.md