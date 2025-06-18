"""
Comprehensive example demonstrating Router with path parameter functionality.

This example shows all the features we've implemented:
1. Router(path="/prefix", routes=[...]) - Router with path parameter
2. app.add_router() - Add router to application
3. app.include_router() - Include router with additional prefix
4. Nested routers with multiple levels of prefixes
"""

from velithon import Velithon
from velithon.routing import Router
from velithon.responses import JSONResponse

# =============================================================================
# Create handlers for different resource types
# =============================================================================

def get_orders():
    return JSONResponse({"orders": ["order1", "order2", "order3"]})

def get_order(order_id: int):
    return JSONResponse({"order_id": order_id, "status": "shipped"})

def create_order():
    return JSONResponse({"message": "Order created", "order_id": 123})

def get_users():
    return JSONResponse({"users": ["alice", "bob", "charlie"]})

def get_user(user_id: int):
    return JSONResponse({"user_id": user_id, "name": f"User {user_id}"})

def create_user():
    return JSONResponse({"message": "User created", "user_id": 456})

def get_products():
    return JSONResponse({"products": ["laptop", "phone", "tablet"]})

def get_product(product_id: int):
    return JSONResponse({"product_id": product_id, "name": f"Product {product_id}"})

# =============================================================================
# Example 1: Router with path parameter and manual route addition
# =============================================================================

orders_router = Router(path="/orders")
orders_router.add_api_route("/", get_orders, methods=["GET"])
orders_router.add_api_route("/{order_id}", get_order, methods=["GET"])
orders_router.add_api_route("/", create_order, methods=["POST"])

# =============================================================================
# Example 2: Router without path, will get prefix when added to app
# =============================================================================

users_router = Router()
users_router.add_api_route("/", get_users, methods=["GET"])
users_router.add_api_route("/{user_id}", get_user, methods=["GET"])
users_router.add_api_route("/", create_user, methods=["POST"])

# =============================================================================
# Example 3: Router with decorators and path parameter
# =============================================================================

api_router = Router(path="/api")

@api_router.get("/health")
def health_check():
    return JSONResponse({"status": "healthy", "timestamp": "2025-06-18"})

@api_router.get("/version")
def get_version():
    return JSONResponse({"version": "1.0.0", "framework": "Velithon"})

@api_router.post("/reset")
def reset_system():
    return JSONResponse({"message": "System reset initiated"})

# =============================================================================
# Example 4: Nested routers - Router containing other routers
# =============================================================================

# Create a products router
products_router = Router(path="/products")
products_router.add_api_route("/", get_products, methods=["GET"])
products_router.add_api_route("/{product_id}", get_product, methods=["GET"])

# Create a shop router that contains the products router
shop_router = Router(path="/shop")
shop_router.add_router(products_router)

# Add some direct routes to the shop router
@shop_router.get("/info")
def shop_info():
    return JSONResponse({"name": "Velithon Shop", "open": True})

# =============================================================================
# Example 5: API versioning with routers
# =============================================================================

# Create v1 API router
v1_router = Router(path="/v1")

@v1_router.get("/status") 
def v1_status():
    return JSONResponse({"version": "v1", "status": "deprecated"})

# Create v2 API router  
v2_router = Router(path="/v2")

@v2_router.get("/status")
def v2_status():
    return JSONResponse({"version": "v2", "status": "active"})

@v2_router.get("/features")
def v2_features():
    return JSONResponse({"features": ["auth", "caching", "rate-limiting"]})

# Combine v1 and v2 into main API router
main_api_router = Router(path="/api")
main_api_router.add_router(v1_router)
main_api_router.add_router(v2_router)

# =============================================================================
# Create the main application and add all routers
# =============================================================================

app = Velithon(
    title="Comprehensive Router Example",
    description="Demonstrating all Router path parameter features",
    version="1.0.0"
)

# Method 1: Add router that already has a path prefix
app.add_router(orders_router)

# Method 2: Add router with additional prefix (users_router has no path)
app.include_router(users_router, prefix="/users")

# Method 3: Add router with existing path prefix
app.add_router(api_router)

# Method 4: Add nested router
app.add_router(shop_router)

# Method 5: Add versioned API router
app.add_router(main_api_router)

# Add some root level routes
@app.get("/")
def root():
    return JSONResponse({
        "message": "Welcome to the Comprehensive Router Example",
        "available_routes": [
            "GET /orders/ - List orders",
            "GET /orders/{id} - Get order by ID", 
            "POST /orders/ - Create order",
            "GET /users/ - List users",
            "GET /users/{id} - Get user by ID",
            "POST /users/ - Create user", 
            "GET /api/health - Health check",
            "GET /api/version - Get version",
            "POST /api/reset - Reset system",
            "GET /shop/info - Shop information",
            "GET /shop/products/ - List products",
            "GET /shop/products/{id} - Get product by ID",
            "GET /api/v1/status - V1 API status",
            "GET /api/v2/status - V2 API status",
            "GET /api/v2/features - V2 features",
            "GET /docs - API documentation"
        ]
    })

@app.get("/routes")
def list_routes():
    """List all available routes in the application."""
    routes = []
    for route in app.router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in sorted(route.methods or []):
                if method != 'HEAD':  # Skip HEAD methods for cleaner output
                    routes.append(f"{method} {route.path}")
    
    return JSONResponse({"total_routes": len(routes), "routes": sorted(routes)})

if __name__ == "__main__":
    print("🚀 Comprehensive Router Example")
    print("=" * 50)
    print()
    print("This example demonstrates:")
    print("1. Router(path='/prefix') - Router with path parameter")  
    print("2. app.add_router() - Add router to application")
    print("3. app.include_router() - Include router with additional prefix")
    print("4. Nested routers with multiple levels")
    print("5. API versioning with routers")
    print()
    print("Available endpoints:")
    print("📋 GET  /routes              - List all routes")
    print("🏠 GET  /                    - Welcome message")
    print("📦 GET  /orders/             - List orders")
    print("📦 GET  /orders/{order_id}   - Get specific order")
    print("📦 POST /orders/             - Create new order")
    print("👥 GET  /users/              - List users") 
    print("👥 GET  /users/{user_id}     - Get specific user")
    print("👥 POST /users/              - Create new user")
    print("🔧 GET  /api/health          - Health check")
    print("🔧 GET  /api/version         - Get version")
    print("🔧 POST /api/reset           - Reset system")
    print("🛍️  GET  /shop/info           - Shop information")
    print("🛍️  GET  /shop/products/      - List products")
    print("🛍️  GET  /shop/products/{id}  - Get specific product")
    print("📡 GET  /api/v1/status       - V1 API status")
    print("📡 GET  /api/v2/status       - V2 API status")
    print("📡 GET  /api/v2/features     - V2 API features")
    print("📚 GET  /docs                - Swagger documentation")
    print()
    print("🌐 Server will start on http://localhost:8000")
    print("💡 Try: curl http://localhost:8000/routes")
