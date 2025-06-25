# Velithon Proxy Feature

## Overview

The Velithon proxy feature provides high-performance HTTP proxying capabilities implemented in Rust and exposed to Python. It includes advanced features like circuit breaker pattern, load balancing, connection pooling, and health checking.

## Features

- **High Performance**: Built with Rust using hyper for maximum throughput
- **Circuit Breaker**: Prevents cascading failures with configurable thresholds
- **Load Balancing**: Multiple strategies (round-robin, random, weighted)
- **Connection Pooling**: Efficient connection reuse with hyper's connection pool
- **Health Checking**: Automatic monitoring of upstream service availability
- **Retry Logic**: Exponential backoff for failed requests
- **No OpenSSL Dependencies**: Uses native system TLS to avoid build issues

## Quick Start

### Basic Proxy Client

```python
import asyncio
from velithon.middleware.proxy import ProxyClient

async def main():
    # Create a proxy client
    proxy = ProxyClient(
        target_url="https://api.example.com",
        timeout_ms=30000,
        max_retries=3
    )
    
    # Forward a request
    status, headers, body = await proxy.forward_request(
        method="GET",
        path="/users/123",
        headers={"Authorization": "Bearer token"},
        query_params={"include": "profile"}
    )
    
    print(f"Status: {status}")
    print(f"Headers: {headers}")
    print(f"Body length: {len(body)}")

asyncio.run(main())
```

### Load Balancer

```python
import asyncio
from velithon.middleware.proxy import ProxyLoadBalancer

async def main():
    # Create load balancer with multiple targets
    lb = ProxyLoadBalancer(
        targets=[
            "https://api1.example.com",
            "https://api2.example.com", 
            "https://api3.example.com"
        ],
        strategy="round_robin",
        health_check_url="/health"
    )
    
    # Get next available target
    target = await lb.get_next_target()
    print(f"Selected target: {target}")
    
    # Check health status
    health = await lb.get_health_status()
    print(f"Health status: {health}")
    
    # Perform health check
    await lb.health_check()

asyncio.run(main())
```

### Weighted Load Balancing

```python
from velithon.middleware.proxy import ProxyLoadBalancer

lb = ProxyLoadBalancer(
    targets=["server1", "server2", "server3"],
    strategy="weighted",
    weights=[50, 30, 20]  # Server1 gets 50% of traffic
)
```

### Proxy Middleware Integration

```python
from velithon import Velithon
from velithon.middleware.proxy import ProxyMiddleware

app = Velithon()

# Add proxy middleware for API routes
proxy_middleware = ProxyMiddleware(
    target_urls=["https://api1.example.com", "https://api2.example.com"],
    path_prefix="/api",
    strategy="round_robin",
    timeout_ms=15000,
    max_retries=2,
    preserve_host=True,
    strip_prefix=True
)

app.add_middleware(proxy_middleware)

# All requests to /api/* will be proxied to the target servers
```

## Advanced Configuration

### Circuit Breaker Settings

```python
proxy = ProxyClient(
    target_url="https://api.example.com",
    max_failures=5,        # Open circuit after 5 failures
    recovery_timeout_ms=60000  # Try again after 60 seconds
)

# Check circuit breaker status
status, failures, last_failure = await proxy.get_circuit_breaker_status()
print(f"Circuit breaker: {status}, failures: {failures}")

# Manually reset circuit breaker
await proxy.reset_circuit_breaker()
```

### Custom Health Checks

```python
lb = ProxyLoadBalancer(
    targets=["https://service1.com", "https://service2.com"],
    health_check_url="/health/ready"  # Custom health endpoint
)

# Manual health check
await lb.health_check()

# Get detailed health status
health_status = await lb.get_health_status()
for target, is_healthy in health_status:
    print(f"{target}: {'healthy' if is_healthy else 'unhealthy'}")
```

### Request Transformation

```python
proxy_middleware = ProxyMiddleware(
    target_urls=["https://backend.example.com"],
    
    # Transform requests before forwarding
    def transform_request(request):
        # Add authentication header
        request.headers["X-API-Key"] = "secret-key"
        
        # Modify path
        request.path = f"/v2{request.path}"
        
        return request,
    
    # Transform responses before returning
    def transform_response(response):
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
)
```

## Performance Considerations

### Connection Pooling

The proxy automatically manages connection pools for optimal performance:

- Connections are reused when possible
- Automatic connection keepalive (60 seconds)
- TCP_NODELAY enabled for low latency
- Configurable pool size per host (default: 50)

### Memory Usage

- Streaming response handling for large payloads
- Efficient zero-copy operations where possible
- Automatic cleanup of idle connections

### Monitoring

```python
# Monitor circuit breaker status
status = await proxy.get_circuit_breaker_status()
print(f"Circuit: {status[0]}, Failures: {status[1]}")

# Monitor load balancer health
health = await lb.get_health_status()
healthy_count = sum(1 for _, is_healthy in health if is_healthy)
print(f"Healthy targets: {healthy_count}/{len(health)}")
```

## Error Handling

The proxy handles various error scenarios gracefully:

- **Connection timeouts**: Configurable timeout with automatic retries
- **Service failures**: Circuit breaker prevents cascading failures  
- **Network errors**: Exponential backoff for transient issues
- **Invalid responses**: Proper error propagation to client

```python
try:
    result = await proxy.forward_request("GET", "/api/data")
except Exception as e:
    print(f"Proxy error: {e}")
    # Handle error appropriately
```

## Best Practices

1. **Use appropriate timeouts**: Set realistic timeout values based on your use case
2. **Configure circuit breaker**: Adjust failure thresholds for your service SLA
3. **Health check frequency**: Balance between responsiveness and overhead
4. **Load balancing strategy**: Choose based on your backend characteristics
5. **Monitor metrics**: Track success rates, latencies, and circuit breaker status

## API Reference

### ProxyClient

```python
ProxyClient(
    target_url: str,
    timeout_ms: int = 30000,
    max_retries: int = 3,
    max_failures: int = 5,
    recovery_timeout_ms: int = 60000
)
```

**Methods:**
- `forward_request(method, path, headers=None, body=None, query_params=None)`
- `get_circuit_breaker_status()` → `(state, failures, last_failure_ms)`
- `reset_circuit_breaker()`

### ProxyLoadBalancer

```python
ProxyLoadBalancer(
    targets: List[str],
    strategy: str = "round_robin",  # "round_robin", "random", "weighted"
    weights: Optional[List[int]] = None,
    health_check_url: Optional[str] = None
)
```

**Methods:**
- `get_next_target()` → `str`
- `health_check()`
- `get_health_status()` → `List[Tuple[str, bool]]`

### ProxyMiddleware

```python
ProxyMiddleware(
    target_urls: Union[str, List[str]],
    path_prefix: str = "/",
    strategy: str = "round_robin",
    timeout_ms: int = 30000,
    max_retries: int = 3,
    preserve_host: bool = False,
    strip_prefix: bool = False,
    transform_request: Optional[Callable] = None,
    transform_response: Optional[Callable] = None
)
```

## Example

```python
from velithon import Velithon
from velithon.middleware.proxy import ProxyMiddleware
from velithon.responses import JSONResponse

app = Velithon()

# API Gateway Configuration
BACKEND_SERVICES = {
    "users": ["https://users-api-1.example.com", "https://users-api-2.example.com"],
    "orders": ["https://orders-api.example.com"],
    "payments": ["https://payments-api-1.example.com", "https://payments-api-2.example.com"],
}

# Add proxy middleware for each service
for service_name, service_urls in BACKEND_SERVICES.items():
    proxy_middleware = ProxyMiddleware(
        target_urls=service_urls,
        path_prefix=f"/api/{service_name}",
        strategy="round_robin" if len(service_urls) > 1 else "single",
        timeout_ms=15000,
        max_retries=2,
        preserve_host=False,
        strip_prefix=True,
        
        # Add service-specific headers
        transform_request=lambda req, svc=service_name: add_service_headers(req, svc),
        
        # Transform responses for consistency
        transform_response=lambda resp: add_api_gateway_headers(resp)
    )
    
    app.add_middleware(proxy_middleware)

def add_service_headers(request, service_name):
    """Add service-specific headers to outgoing requests."""
    request.headers["X-Service"] = service_name
    request.headers["X-Request-ID"] = f"req-{hash(request.path)}"
    request.headers["X-Gateway"] = "Velithon-Proxy"
    return request

def add_api_gateway_headers(response):
    """Add API gateway headers to responses."""
    response.headers["X-Gateway"] = "Velithon"
    response.headers["X-Response-Time"] = "fast"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check health of API gateway and backend services."""
    return JSONResponse({
        "status": "healthy",
        "gateway": "velithon-proxy",
        "timestamp": "2025-06-11T00:00:00Z"
    })

# Service discovery endpoint
@app.get("/services")
async def list_services():
    """List available backend services."""
    return JSONResponse({
        "services": list(BACKEND_SERVICES.keys()),
        "endpoints": {
            name: f"/api/{name}/*" 
            for name in BACKEND_SERVICES.keys()
        }
    })

# Metrics endpoint (would normally integrate with your monitoring system)
@app.get("/metrics")
async def get_metrics():
    """Get proxy metrics (placeholder for real implementation)."""
    return JSONResponse({
        "requests_total": 12345,
        "requests_per_second": 42.5,
        "average_response_time_ms": 156,
        "circuit_breaker_status": {
            "users": "closed",
            "orders": "closed", 
            "payments": "closed"
        },
        "backend_health": {
            service: "healthy" for service in BACKEND_SERVICES.keys()
        }
    })

if __name__ == "__main__":
    print("Starting Velithon API Gateway with Proxy Feature")
    print("Available endpoints:")
    print("  GET  /health         - Gateway health check")
    print("  GET  /services       - List available services")
    print("  GET  /metrics        - Proxy metrics")
    print("  ANY  /api/users/*    - User service proxy")
    print("  ANY  /api/orders/*   - Orders service proxy") 
    print("  ANY  /api/payments/* - Payments service proxy")
    print("\nExample requests:")
    print("  curl http://localhost:8000/api/users/profile")
    print("  curl http://localhost:8000/api/orders/123")
    print("  curl -X POST http://localhost:8000/api/payments/process")
    
    # In a real application, you would run this with:
    # app.run(host="0.0.0.0", port=8000)
    print("\nTo run: python -m velithon example_api_gateway.py")
```
