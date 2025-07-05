"""Auto-serialization example for Velithon framework.

This example demonstrates how Velithon automatically serializes various Python objects
to JSON responses without requiring explicit wrapping in JSONResponse objects.
"""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from velithon import Velithon


class User(BaseModel):
    """Pydantic model representing a user."""
    
    id: int
    name: str
    email: str
    active: bool = True
    tags: list[str] = []
    created_at: datetime = datetime.utcnow()


@dataclass
class Product:
    """Dataclass representing a product."""
    
    id: int
    name: str
    price: float
    in_stock: bool
    description: str | None = None


class CustomStats:
    """Custom serializable object with statistics."""
    
    def __init__(self, total_users: int, active_users: int):
        """Initialize custom stats with user counts."""
        self.total_users = total_users
        self.active_users = active_users
        self.computed_at = datetime.utcnow()
    
    def __json__(self):
        """Return JSON representation of the stats."""
        activity_rate = (
            self.active_users / self.total_users if self.total_users > 0 else 0
        )
        return {
            "total_users": self.total_users,
            "active_users": self.active_users,
            "activity_rate": activity_rate,
            "computed_at": self.computed_at.isoformat()
        }


# Create Velithon app
app = Velithon()


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Return a Pydantic model - automatically uses OptimizedJSONResponse."""
    return User(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com",
        tags=["customer", "verified"]
    )


@app.get("/products/{product_id}")
async def get_product(product_id: int):
    """Return a dataclass - automatically uses OptimizedJSONResponse."""
    return Product(
        id=product_id,
        name=f"Product {product_id}",
        price=29.99,
        in_stock=True,
        description="A great product"
    )


@app.get("/simple-data")
async def get_simple_data():
    """Return a small dict - automatically uses JSONResponse."""
    return {
        "message": "Hello from Velithon!",
        "status": "success",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/large-collection")
async def get_large_collection():
    """Return a large collection - automatically uses OptimizedJSONResponse."""
    return {
        "users": [
            {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(100)
        ],
        "total": 100,
        "page": 1
    }


@app.get("/mixed-objects")
async def get_mixed_objects():
    """Return a list of mixed objects - automatically serialized."""
    return [
        {"type": "dict", "data": {"key": "value"}},
        User(id=1, name="Alice", email="alice@example.com"),
        Product(id=1, name="Widget", price=19.99, in_stock=True),
        CustomStats(total_users=1000, active_users=750)
    ]


@app.get("/custom-stats")
async def get_custom_stats():
    """Return custom object with __json__ method."""
    return CustomStats(total_users=5000, active_users=3750)


@app.get("/basic-types")
async def get_basic_types():
    """Return basic types - automatically handled."""
    return [
        "string",
        42,
        3.14,
        True,
        None,
        {"nested": {"data": "value"}}
    ]


if __name__ == "__main__":
    print("🚀 Velithon Auto-Serialization Example")
    print("=" * 50)
    print()
    print("Available endpoints:")
    print("  GET /users/{user_id} - Pydantic model")
    print("  GET /products/{product_id} - Dataclass")
    print("  GET /simple-data - Small dictionary")
    print("  GET /large-collection - Large collection")
    print("  GET /mixed-objects - Mixed object types")
    print("  GET /custom-stats - Custom serializable object")
    print("  GET /basic-types - Basic Python types")
    print()
    print("Run with: velithon run auto_serialization_example.py")
    print("Or: python -m velithon run auto_serialization_example.py")
