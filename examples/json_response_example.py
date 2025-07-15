"""Simple example demonstrating the unified JSONResponse.

This example shows how the new JSONResponse handles all JSON serialization
needs with optimal performance and simplicity.
"""

import time
from dataclasses import dataclass

from velithon import Velithon
from velithon.responses import JSONResponse

# Create app instance
app = Velithon()


@dataclass
class User:
    """Example user dataclass."""

    id: int
    name: str
    email: str
    active: bool = True


@app.get("/")
async def root():
    """Return simple JSON response."""
    return JSONResponse({
        "message": "Welcome to Velithon with unified JSONResponse!",
        "timestamp": time.time(),
        "framework": "Velithon"
    })


@app.get("/user/{user_id}")
async def get_user(user_id: int):
    """Return a single user - demonstrates dataclass serialization."""
    user = User(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com"
    )
    return JSONResponse(user.__dict__)


@app.get("/users")
async def list_users():
    """Return multiple users - demonstrates collection handling."""
    users = [
        User(id=i, name=f"User {i}", email=f"user{i}@example.com")
        for i in range(100)
    ]

    return JSONResponse({
        "users": [user.__dict__ for user in users],
        "total": len(users),
        "page": 1,
        "per_page": 100
    })


@app.get("/large-dataset")
async def large_dataset():
    """Return a large dataset - demonstrates performance with big data."""
    data = {
        "metadata": {
            "generated_at": time.time(),
            "version": "1.0",
            "total_records": 1000
        },
        "items": [
            {
                "id": i,
                "name": f"Item {i}",
                "category": f"Category {i % 10}",
                "properties": {
                    "tags": [f"tag_{j}" for j in range(5)],
                    "values": [i * j for j in range(10)],
                    "active": i % 2 == 0
                }
            }
            for i in range(1000)
        ],
        "summary": {
            "active_items": sum(1 for i in range(1000) if i % 2 == 0),
            "categories": 10,
            "total_tags": 5000
        }
    }

    return JSONResponse(data)


@app.post("/users")
async def create_user(request):
    """Create a new user - demonstrates POST with JSON response."""
    user_data = await request.json()

    # Simulate user creation
    new_user = User(
        id=123,
        name=user_data.get("name", "Unknown"),
        email=user_data.get("email", "unknown@example.com")
    )

    return JSONResponse(
        {
            "message": "User created successfully",
            "user": new_user.__dict__
        },
        status_code=201
    )


@app.get("/error-example")
async def error_example():
    """Return example error response."""
    return JSONResponse(
        {
            "error": "Something went wrong",
            "code": "EXAMPLE_ERROR",
            "details": {
                "message": "This is just an example error",
                "timestamp": time.time()
            }
        },
        status_code=400
    )


if __name__ == "__main__":
    print("🚀 Velithon JSONResponse Example")
    print("===============================")
    print("Run this with: uvicorn json_response_example:app --reload")
    print()
    print("Try these endpoints:")
    print("  GET  /                  - Simple JSON response")
    print("  GET  /user/1            - Single user")
    print("  GET  /users             - Multiple users")
    print("  GET  /large-dataset     - Large dataset (1000 items)")
    print("  POST /users             - Create user")
    print("  GET  /error-example     - Error response")
    print()
    print("All responses use the unified JSONResponse for optimal performance!")
