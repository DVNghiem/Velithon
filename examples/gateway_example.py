"""Gateway Example for Velithon Framework.

This example demonstrates how to use Velithon's gateway features to forward
requests to backend services, enabling gradual migration from monolithic
to microservice architecture.
"""

from velithon import Gateway, Velithon, forward_to, gateway_route
from velithon.requests import Request
from velithon.responses import JSONResponse


# Initialize the gateway
gateway = Gateway()

# Create Velithon application
app = Velithon(
    title="API Gateway Example",
    description="Demonstrates Velithon's gateway functionality for service forwarding",
    version="1.0.0"
)


# Example 1: Simple single-target forwarding
@app.route("/api/v1/users/{user_id}", methods=["GET", "POST", "PUT", "DELETE"])
async def users_gateway(request: Request):
    """Forward all user-related requests to the user service."""
    # Use the convenience forward_to function
    forward_func = forward_to(
        path="/api/v1/users/{user_id}",
        target="http://user-service:8080",
        strip_path=False,  # Keep the full path
        preserve_host=False,  # Don't preserve the original host header
        timeout_ms=15000,  # 15 second timeout
        max_retries=2
    )
    return await forward_func(request)


# Example 2: Load-balanced forwarding to multiple backends
product_service_route = gateway_route(
    path="/api/v1/products/{path:path}",  # Catch all product paths
    targets=[
        "http://product-service-1:8080",
        "http://product-service-2:8080",
        "http://product-service-3:8080"
    ],
    methods=["GET", "POST", "PUT", "DELETE"],
    load_balancing_strategy="round_robin",
    health_check_path="/health",
    strip_path=False,
    headers_to_add={
        "X-Gateway": "Velithon",
        "X-Service": "product"
    },
    headers_to_remove=["X-Internal-Token"],
    timeout_ms=10000,
    max_retries=3
)

# Example 3: Weighted load balancing for gradual migration
legacy_migration_route = gateway_route(
    path="/api/v1/orders/{path:path}",
    targets=[
        "http://legacy-order-service:8080",  # Old monolithic service
        "http://new-order-service:8080"      # New microservice
    ],
    methods=["GET", "POST", "PUT", "DELETE"],
    load_balancing_strategy="weighted",
    weights=[70, 30],  # 70% to legacy, 30% to new service
    health_check_path="/health",
    strip_path=False,
    timeout_ms=20000
)

# Example 4: Path rewriting for API versioning
@app.route("/v2/inventory/{path:path}", methods=["GET", "POST"])
async def inventory_v2_gateway(request: Request):
    """Rewrite v2 API calls to v1 backend while transitioning."""
    forward_func = forward_to(
        path="/v2/inventory/{path:path}",
        target="http://inventory-service:8080",
        strip_path=True,  # Remove the matched path
        timeout_ms=8000
    )
    return await forward_func(request)


# Example 5: Service-specific middleware and headers
payment_route = gateway_route(
    path="/api/v1/payments/{path:path}",
    targets="http://payment-service:8443",  # HTTPS backend
    methods=["POST", "GET"],
    headers_to_add={
        "X-Gateway": "Velithon",
        "X-Service": "payment",
        "Content-Security-Policy": "default-src 'self'"
    },
    headers_to_remove=["X-Debug", "X-Internal"],
    timeout_ms=30000,  # Longer timeout for payment processing
    max_retries=1  # Don't retry payment operations
)

# Add gateway routes to the application
app.router.routes.extend([
    product_service_route,
    legacy_migration_route,
    payment_route
])

# Example 6: Using the Gateway class decorator pattern
@gateway.forward_to(
    targets=[
        "http://notification-service-1:8080",
        "http://notification-service-2:8080"
    ],
    path="/api/v1/notifications/{path:path}",
    load_balancing_strategy="random",
    timeout_ms=5000
)
def notifications():
    """Forward notification requests to available services."""
    pass

# Add the gateway routes
app.router.routes.extend(gateway.get_routes())


# Health check endpoint for the gateway itself
@app.route("/health")
async def health_check(request: Request):
    """Health check for the gateway."""
    try:
        # Check health of all backend services
        health_status = await gateway.health_check_all()
        
        # Determine overall health
        all_healthy = all(
            isinstance(status, list) and
            any(service[1] for service in status) if isinstance(status, list)
            else False
            for status in health_status.values()
        )
        
        status_code = 200 if all_healthy else 503
        
        return JSONResponse(
            content={
                "status": "healthy" if all_healthy else "degraded",
                "gateway": "operational",
                "backends": health_status,
                "timestamp": "2024-01-01T00:00:00Z"  # In real app, use actual timestamp
            },
            status_code=status_code
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            },
            status_code=503
        )


# Gateway status and configuration endpoint
@app.route("/gateway/status")
async def gateway_status(request: Request):
    """Get gateway configuration and status."""
    routes_info = []
    
    for route in gateway.get_routes():
        route_info = {
            "path": route.path,
            "name": route.name,
            "methods": route.methods,
            "targets": (
                [route.proxy_client.target_url] if route.proxy_client
                else route.load_balancer.targets if route.load_balancer
                else []
            ),
            "timeout_ms": route.timeout_ms,
            "max_retries": route.max_retries
        }
        routes_info.append(route_info)
    
    return JSONResponse(
        content={
            "gateway": {
                "total_routes": len(gateway.get_routes()),
                "routes": routes_info
            },
            "load_balancers": list(gateway.load_balancers.keys())
        }
    )


# Example middleware for request logging
async def request_logging_middleware(scope, protocol, call_next):
    """Log all gateway requests."""
    request = Request(scope, protocol)
    print(f"Gateway request: {request.method} {request.url.path}")
    
    response = await call_next(scope, protocol)
    return response


# Add the logging middleware
# app.middleware.append(request_logging_middleware)  # Uncomment to enable


if __name__ == "__main__":
    # Run the gateway
    print("Starting Velithon API Gateway...")
    print("Available endpoints:")
    print("  GET /health - Gateway health check")
    print("  GET /gateway/status - Gateway configuration")
    print("  * /api/v1/users/* - Forward to user service")
    print("  * /api/v1/products/* - Load balanced product services")
    print("  * /api/v1/orders/* - Weighted migration orders")
    print("  * /v2/inventory/* - Path rewriting inventory")
    print("  * /api/v1/payments/* - Payment service gateway")
    print("  * /api/v1/notifications/* - Random load balanced notifications")
    
    # In a real application, you would run this with:
    # uvicorn gateway_example:app --host 0.0.0.0 --port 8000
    # or use the Velithon CLI
