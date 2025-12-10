"""Database integration example for Velithon.

This example demonstrates how to use the database ORM integration layer
with SQLAlchemy, including:
- Database configuration and setup
- Model definition
- CRUD operations using repositories
- Transaction management
- Middleware integration
- Health check endpoints
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from velithon import Velithon, JSONResponse
from velithon.database import (
    Base,
    Database,
    DatabaseConfig,
    SQLiteConfig,
    BaseRepository,
    DatabaseHealthCheck,
    transaction,
)
from velithon.database.session import get_current_session
from velithon.middleware import (
    Middleware,
    DatabaseSessionMiddleware,
    TransactionMiddleware,
)
from velithon.requests import Request


# Define a User model
class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# User repository
class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User instance or None
        """
        return await self.get_by(email=email)


# Create database configuration
db_config = SQLiteConfig(database="example.db")
database = Database(db_config)

# Create Velithon app
app = Velithon(
    title="Database Example API",
    description="Example API demonstrating database integration",
    version="1.0.0",
)

# Attach database to app for CLI commands
app.database = database


# Startup event to create tables
@app.router.on_event("startup")
async def startup():
    """Startup event handler."""
    await database.connect()
    
    # Create tables
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database connected and tables created")


# Shutdown event to close database
@app.router.on_event("shutdown")
async def shutdown():
    """Shutdown event handler."""
    await database.disconnect()
    print("Database disconnected")


# Health check endpoint
@app.get("/health/db", tags=["health"])
async def health_check(request: Request):
    """Database health check endpoint."""
    health_checker = DatabaseHealthCheck(database)
    health = await health_checker.check_health()
    return JSONResponse(health.model_dump())


# Get all users
@app.get("/users", tags=["users"])
async def get_users(request: Request):
    """Get all users."""
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)
    
    repo = UserRepository(User, session)
    users = await repo.get_all()
    
    return JSONResponse({
        "users": [user.to_dict() for user in users],
        "count": len(users),
    })


# Get user by ID
@app.get("/users/{user_id}", tags=["users"])
async def get_user(request: Request, user_id: int):
    """Get user by ID."""
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)
    
    repo = UserRepository(User, session)
    user = await repo.get(user_id)
    
    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)
    
    return JSONResponse(user.to_dict())


# Create user
@app.post("/users", tags=["users"])
async def create_user(request: Request):
    """Create a new user."""
    data = await request.json()
    
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)
    
    repo = UserRepository(User, session)
    
    # Check if email already exists
    existing_user = await repo.get_by_email(data["email"])
    if existing_user:
        return JSONResponse(
            {"error": "Email already exists"},
            status_code=400,
        )
    
    # Create user with transaction
    async with transaction(session):
        user = await repo.create(
            name=data["name"],
            email=data["email"],
        )
    
    return JSONResponse(user.to_dict(), status_code=201)


# Update user
@app.put("/users/{user_id}", tags=["users"])
async def update_user(request: Request, user_id: int):
    """Update a user."""
    data = await request.json()
    
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)
    
    repo = UserRepository(User, session)
    
    async with transaction(session):
        user = await repo.update(user_id, **data)
    
    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)
    
    return JSONResponse(user.to_dict())


# Delete user
@app.delete("/users/{user_id}", tags=["users"])
async def delete_user(request: Request, user_id: int):
    """Delete a user."""
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)
    
    repo = UserRepository(User, session)
    
    async with transaction(session):
        deleted = await repo.delete(user_id)
    
    if not deleted:
        return JSONResponse({"error": "User not found"}, status_code=404)
    
    return JSONResponse({"message": "User deleted successfully"})


# Paginated users
@app.get("/users/paginated", tags=["users"])
async def get_users_paginated(
    request: Request,
    page: int = 1,
    page_size: int = 10,
):
    """Get paginated users."""
    session = get_current_session()
    if session is None:
        return JSONResponse({"error": "No database session"}, status_code=500)
    
    repo = UserRepository(User, session)
    result = await repo.paginate(page=page, page_size=page_size)
    
    # Convert users to dict
    result["items"] = [user.to_dict() for user in result["items"]]
    
    return JSONResponse(result)


# Add middleware
app.user_middleware = [
    Middleware(DatabaseSessionMiddleware, database),
    Middleware(TransactionMiddleware, auto_commit=True),
]


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Velithon Database Example")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health/db")
    print("\nExample requests:")
    print("  Create user: POST http://localhost:8000/users")
    print('    Body: {"name": "John Doe", "email": "john@example.com"}')
    print("  Get users: GET http://localhost:8000/users")
    print("  Get user: GET http://localhost:8000/users/1")
    
    # Run with uvicorn (or use velithon CLI)
    # uvicorn database_example:app --reload
