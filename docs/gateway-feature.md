# Gateway Feature

The Velithon Gateway provides powerful request forwarding capabilities that enable gradual migration from monolithic to microservice architectures. It offers high-performance proxying with advanced features like load balancing, circuit breakers, and health checking.

## Overview

The gateway feature allows you to:

- Forward requests to single or multiple backend services
- Implement load balancing with different strategies
- Handle service failures gracefully with circuit breakers
- Perform health checks on backend services
- Manipulate headers and paths during forwarding
- Support gradual service migration with weighted routing

## Basic Usage

### Single Target Forwarding

```python
from velithon import Velithon, forward_to
from velithon.requests import Request

app = Velithon()

@app.route("/api/v1/users/{user_id}", methods=["GET", "POST", "PUT", "DELETE"])
async def users_gateway(request: Request):
    """Forward all user-related requests to the user service."""
    forward_func = forward_to(
        path="/api/v1/users/{user_id}",
        target="http://user-service:8080",
        timeout_ms=15000,
        max_retries=2
    )
    return await forward_func(request)
```

### Gateway Routes

```python
from velithon import gateway_route

# Create a gateway route with multiple targets
products_route = gateway_route(
    path="/api/v1/products/{path:path}",
    targets=[
        "http://product-service-1:8080",
        "http://product-service-2:8080", 
        "http://product-service-3:8080"
    ],
    methods=["GET", "POST", "PUT", "DELETE"],
    load_balancing_strategy="round_robin",
    health_check_path="/health",
    timeout_ms=10000,
    max_retries=3
)

# Add to your application
app.router.routes.append(products_route)
```

## Load Balancing

Velithon Gateway supports three load balancing strategies:

### Round Robin (Default)

```python
route = gateway_route(
    path="/api/service/{path:path}",
    targets=["http://service-1:8080", "http://service-2:8080"],
    load_balancing_strategy="round_robin"
)
```

### Random

```python
route = gateway_route(
    path="/api/service/{path:path}",
    targets=["http://service-1:8080", "http://service-2:8080"],
    load_balancing_strategy="random"
)
```

### Weighted (for gradual migration)

```python
# 70% traffic to legacy service, 30% to new service
route = gateway_route(
    path="/api/orders/{path:path}",
    targets=[
        "http://legacy-order-service:8080",
        "http://new-order-service:8080"
    ],
    load_balancing_strategy="weighted",
    weights=[70, 30]
)
```

## Header Manipulation

### Adding Headers

```python
route = gateway_route(
    path="/api/service/{path:path}",
    targets="http://backend-service:8080",
    headers_to_add={
        "X-Gateway": "Velithon",
        "X-Service": "backend",
        "X-Request-ID": "generated-id"
    }
)
```

### Removing Headers

```python
route = gateway_route(
    path="/api/service/{path:path}",
    targets="http://backend-service:8080",
    headers_to_remove=["X-Internal-Token", "X-Debug-Info"],
    preserve_host=False  # Remove Host header
)
```

## Path Manipulation

### Path Stripping

```python
# Request to /api/v1/service/users/123
# Forwarded as /users/123
route = gateway_route(
    path="/api/v1/service/{path:path}",
    targets="http://backend:8080",
    strip_path=True
)
```

### Path Rewriting

```python
# Request to /v2/api/users/123
# Forwarded as /v1/api/users/123
route = gateway_route(
    path="/v2/api/{path:path}",
    targets="http://backend:8080",
    path_rewrite="/v1/api/{path}"
)
```

## Gateway Class

The `Gateway` class provides a higher-level interface for managing multiple routes:

```python
from velithon import Gateway

gateway = Gateway()

# Add routes
gateway.add_route(
    path="/api/users/{path:path}",
    targets="http://user-service:8080"
)

# Use decorator pattern
@gateway.forward_to(
    targets=["http://notification-1:8080", "http://notification-2:8080"],
    path="/api/notifications/{path:path}",
    load_balancing_strategy="random"
)
def notifications():
    """Forward notification requests."""
    pass

# Add all gateway routes to your app
app.router.routes.extend(gateway.get_routes())
```

## Health Checking

Gateway routes automatically perform health checks on backend services:

```python
route = gateway_route(
    path="/api/service/{path:path}",
    targets=["http://service-1:8080", "http://service-2:8080"],
    health_check_path="/health",  # Custom health check endpoint
    load_balancing_strategy="round_robin"
)

# Manual health check
@app.route("/gateway/health")
async def gateway_health(request):
    health_status = await gateway.health_check_all()
    return JSONResponse(health_status)
```

## Circuit Breaker

The gateway includes automatic circuit breaker functionality:

```python
route = gateway_route(
    path="/api/service/{path:path}",
    targets="http://unreliable-service:8080",
    max_retries=3,
    timeout_ms=5000
)
```

The circuit breaker will:
- Track failures and successes
- Open the circuit after multiple failures
- Implement exponential backoff
- Automatically recover when service is healthy

## Configuration Options

### GatewayRoute Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str` | Required | Path pattern to match |
| `targets` | `str \| list[str]` | Required | Target URL(s) |
| `methods` | `list[str] \| None` | `None` | HTTP methods to match |
| `name` | `str \| None` | `None` | Route name |
| `strip_path` | `bool` | `False` | Strip matched path from forwarded request |
| `preserve_host` | `bool` | `False` | Preserve original Host header |
| `timeout_ms` | `int` | `30000` | Request timeout in milliseconds |
| `max_retries` | `int` | `3` | Maximum retry attempts |
| `load_balancing_strategy` | `str` | `"round_robin"` | Load balancing strategy |
| `weights` | `list[int] \| None` | `None` | Weights for weighted strategy |
| `health_check_path` | `str \| None` | `None` | Health check endpoint path |
| `headers_to_add` | `dict[str, str] \| None` | `None` | Headers to add |
| `headers_to_remove` | `list[str] \| None` | `None` | Headers to remove |
| `path_rewrite` | `str \| None` | `None` | Path rewrite pattern |

## Performance Considerations

### Connection Pooling

The gateway uses Hyper's connection pooling for optimal performance:

```python
# Connections are automatically pooled and reused
route = gateway_route(
    path="/api/high-traffic/{path:path}",
    targets=["http://service-1:8080", "http://service-2:8080"],
    timeout_ms=5000  # Lower timeout for high-traffic scenarios
)
```

### Async Operation

All gateway operations are fully asynchronous:

```python
# Multiple concurrent requests are handled efficiently
@app.route("/api/batch/{path:path}")
async def batch_requests(request: Request):
    # Gateway automatically handles concurrent forwarding
    forward_func = forward_to("/api/batch/{path:path}", "http://batch-service:8080")
    return await forward_func(request)
```

## Migration Strategies

### Blue-Green Deployment

```python
# Switch between blue and green deployments
current_environment = "blue"  # or "green"

route = gateway_route(
    path="/api/service/{path:path}",
    targets=f"http://service-{current_environment}:8080"
)
```

### Canary Deployment

```python
# Gradually increase traffic to new version
route = gateway_route(
    path="/api/service/{path:path}",
    targets=[
        "http://service-v1:8080",  # Stable version
        "http://service-v2:8080"   # Canary version
    ],
    load_balancing_strategy="weighted",
    weights=[95, 5]  # 5% canary traffic
)
```

### Service Decomposition

```python
# Gradually move endpoints from monolith to microservices
@app.route("/api/legacy/{path:path}")
async def legacy_service(request: Request):
    path = request.url.path
    
    # Route specific endpoints to new services
    if path.startswith("/api/legacy/users"):
        target = "http://user-service:8080"
        new_path = path.replace("/api/legacy", "/api/v1")
    elif path.startswith("/api/legacy/orders"):
        target = "http://order-service:8080"
        new_path = path.replace("/api/legacy", "/api/v1")
    else:
        # Fallback to monolith
        target = "http://monolith:8080"
        new_path = path
    
    forward_func = forward_to(path, target)
    return await forward_func(request)
```

## Error Handling

The gateway provides comprehensive error handling:

```python
@app.route("/api/service/{path:path}")
async def service_gateway(request: Request):
    try:
        forward_func = forward_to("/api/service/{path:path}", "http://service:8080")
        return await forward_func(request)
    except Exception as e:
        # Gateway automatically returns 502 Bad Gateway
        # You can customize error handling here
        return JSONResponse(
            content={"error": "Service unavailable", "detail": str(e)},
            status_code=503
        )
```

## Monitoring and Observability

### Gateway Status

```python
@app.route("/gateway/status")
async def gateway_status(request: Request):
    routes_info = []
    for route in gateway.get_routes():
        route_info = {
            "path": route.path,
            "targets": route.targets,
            "health": "healthy"  # Check actual health
        }
        routes_info.append(route_info)
    
    return JSONResponse({"routes": routes_info})
```

### Request Logging

```python
# Log all gateway requests
async def gateway_logging_middleware(scope, protocol, call_next):
    request = Request(scope, protocol)
    
    if request.url.path.startswith("/api/"):
        print(f"Gateway: {request.method} {request.url.path}")
    
    response = await call_next(scope, protocol)
    return response

app.middleware.append(gateway_logging_middleware)
```

## Best Practices

1. **Use Health Checks**: Always configure health check endpoints for your backend services.

2. **Set Appropriate Timeouts**: Configure timeouts based on your service characteristics.

3. **Monitor Circuit Breakers**: Track circuit breaker states to identify problematic services.

4. **Gradual Migration**: Use weighted load balancing for gradual traffic migration.

5. **Header Security**: Remove internal headers before forwarding to external services.

6. **Path Design**: Use consistent path patterns for easier maintenance.

7. **Error Handling**: Implement comprehensive error handling and fallback strategies.

8. **Performance Testing**: Test gateway performance under load to ensure it meets your requirements.

The Velithon Gateway provides a robust foundation for building resilient, scalable API gateways that can evolve with your architecture needs.
