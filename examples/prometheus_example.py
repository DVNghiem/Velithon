"""Example demonstrating Prometheus metrics collection in Velithon.

This example shows how to integrate Prometheus monitoring into a Velithon
application for collecting HTTP request metrics and performance monitoring.
"""

from velithon import Velithon
from velithon.middleware import Middleware, PrometheusMiddleware
from velithon.responses import JSONResponse


def create_prometheus_app() -> Velithon:
    """Create a Velithon application with Prometheus metrics collection.
    
    Returns:
        Configured Velithon application with Prometheus middleware
    """
    app = Velithon(
        middleware=[
            # Add Prometheus middleware for metrics collection
            Middleware(
                PrometheusMiddleware,
                metrics_path="/metrics",  # Endpoint for Prometheus scraping
                collect_request_size=True,  # Collect request size metrics
                collect_response_size=True,  # Collect response size metrics
                exclude_paths=["/health", "/ping"],  # Exclude health checks
            ),
        ]
    )
    
    # Sample endpoints for demonstration
    @app.get("/")
    async def root():
        """Root endpoint returning a simple message."""
        return JSONResponse({"message": "Hello from Velithon with Prometheus!"})
    
    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        """Get user by ID - demonstrates path normalization in metrics."""
        return JSONResponse({
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        })
    
    @app.post("/users")
    async def create_user(data: dict):
        """Create a new user - demonstrates POST request metrics."""
        return JSONResponse(
            {"message": "User created", "data": data},
            status_code=201
        )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint - excluded from metrics."""
        return JSONResponse({"status": "healthy"})
    
    @app.get("/error")
    async def trigger_error():
        """Endpoint that triggers an error for error metrics testing."""
        raise Exception("Test error for metrics")
    
    return app


def create_optimized_prometheus_app() -> Velithon:
    """Create a Velithon application with optimized Prometheus metrics.
    
    Uses FastPrometheusMiddleware for high-throughput applications.
    
    Returns:
        Configured Velithon application with optimized Prometheus middleware
    """
    from velithon.middleware import FastPrometheusMiddleware
    
    app = Velithon(
        middleware=[
            # Use optimized Prometheus middleware
            Middleware(
                FastPrometheusMiddleware,
                metrics_path="/metrics",
                collect_request_size=True,
                collect_response_size=True,
                exclude_paths=["/health", "/ping", "/ready"],
                # Custom path normalizer for better grouping
                path_normalizer=lambda path: normalize_api_path(path),
            ),
        ]
    )
    
    @app.get("/api/v1/users/{user_id}")
    async def get_user_v1(user_id: int):
        """API v1 endpoint for user retrieval."""
        return JSONResponse({
            "version": "v1",
            "user_id": user_id,
            "name": f"User {user_id}"
        })
    
    @app.get("/api/v2/users/{user_id}")
    async def get_user_v2(user_id: int):
        """API v2 endpoint for user retrieval."""
        return JSONResponse({
            "version": "v2",
            "user_id": user_id,
            "name": f"User {user_id}",
            "created_at": "2025-01-01T00:00:00Z"
        })
    
    return app


def normalize_api_path(path: str) -> str:
    """Custom path normalizer for API endpoints.
    
    Groups API paths by version and resource type for better metrics.
    
    Args:
        path: Original request path
        
    Returns:
        Normalized path for metrics grouping
    """
    import re
    
    # Normalize API versioned paths
    path = re.sub(r"/api/v\d+/", "/api/v{version}/", path)
    # Replace numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    # Replace UUIDs
    path = re.sub(
        r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "/{uuid}",
        path
    )
    
    return path


if __name__ == "__main__":
    # Create and run the application
    app = create_prometheus_app()
    
    print("Starting Velithon application with Prometheus metrics...")
    print("Metrics available at: http://localhost:8000/metrics")
    print("Test endpoints:")
    print("  - GET  http://localhost:8000/")
    print("  - GET  http://localhost:8000/users/123")
    print("  - POST http://localhost:8000/users")
    print("  - GET  http://localhost:8000/health")
    print("  - GET  http://localhost:8000/error")
    
    # Note: In a real application, you would run this with:
    # velithon run --app prometheus_example:app --host 0.0.0.0 --port 8000
