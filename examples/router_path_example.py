"""
Example demonstrating Router with path parameter and adding routers to application.

This example shows how to:
1. Create a router with a path prefix: Router(path="/orders", routes=[...])
2. Add routers to the application using app.add_router() or app.include_router()
3. Use nested path prefixes when adding routers
"""

from velithon import Velithon
from velithon.routing import Router
from velithon.responses import JSONResponse

# Create handlers for orders
def get_orders():
    """Get all orders"""
    return JSONResponse({"orders": ["order1", "order2", "order3"]})

def get_order(order_id: int):
    """Get a specific order by ID"""
    return JSONResponse({"order_id": order_id, "status": "shipped"})

def create_order():
    """Create a new order"""
    return JSONResponse({"message": "Order created", "order_id": 123})

# Create handlers for users  
def get_users():
    """Get all users"""
    return JSONResponse({"users": ["user1", "user2", "user3"]})

def get_user(user_id: int):
    """Get a specific user by ID"""
    return JSONResponse({"user_id": user_id, "name": "John Doe"})

# Example 1: Router with path parameter and routes
order_router = Router(
    path="/orders",
    routes=[
        # These routes will be prefixed with /orders
    ]
)

# Add routes to the order router (will be prefixed with /orders)
order_router.add_api_route("/", get_orders, methods=["GET"])
order_router.add_api_route("/{order_id}", get_order, methods=["GET"])  
order_router.add_api_route("/", create_order, methods=["POST"])

# Example 2: Router without path parameter, will add prefix when including
user_router = Router()
user_router.add_api_route("/", get_users, methods=["GET"])
user_router.add_api_route("/{user_id}", get_user, methods=["GET"])

# Example 3: Using decorators on router with path
api_router = Router(path="/api/v1")

@api_router.get("/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse({"status": "healthy"})

@api_router.get("/info")  
def app_info():
    """Application info endpoint"""
    return JSONResponse({"name": "Velithon App", "version": "1.0.0"})

# Create the main application
app = Velithon(
    title="Router Example API",
    description="Example demonstrating Router with path parameter",
    version="1.0.0"
)

# Add the order router (already has /orders prefix)
app.add_router(order_router)

# Add the user router with a prefix
app.include_router(user_router, prefix="/users")

# Add the API router (already has /api/v1 prefix)
app.add_router(api_router)

# Add some direct routes to the main app
@app.get("/")
def root():
    return JSONResponse({"message": "Welcome to the Router Example API"})

if __name__ == "__main__":
    # Available endpoints:
    # GET  /                    - Root endpoint
    # GET  /orders/             - Get all orders  
    # GET  /orders/{order_id}   - Get specific order
    # POST /orders/             - Create new order
    # GET  /users/              - Get all users
    # GET  /users/{user_id}     - Get specific user
    # GET  /api/v1/health       - Health check
    # GET  /api/v1/info         - App info
    # GET  /docs                - Swagger documentation
    
    print("Starting server...")
    print("Available endpoints:")
    print("  GET  /                    - Root endpoint")
    print("  GET  /orders/             - Get all orders")
    print("  GET  /orders/{order_id}   - Get specific order") 
    print("  POST /orders/             - Create new order")
    print("  GET  /users/              - Get all users")
    print("  GET  /users/{user_id}     - Get specific user")
    print("  GET  /api/v1/health       - Health check")
    print("  GET  /api/v1/info         - App info")
    print("  GET  /docs                - Swagger documentation")
    print()
    print("Server will start on http://localhost:8000")
    
    # The app can be run with: python examples/router_path_example.py
    # Or using uvicorn: uvicorn examples.router_path_example:app --reload
