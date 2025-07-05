# Load Balancing

Velithon provides built-in load balancing capabilities through its proxy system for distributing traffic across multiple backend services.

## Overview

Load balancing ensures high availability and optimal performance by distributing incoming requests across multiple server instances. Velithon supports load balancing through both the Gateway system and Proxy Middleware.

## Configuration

### Using Gateway Routes

```python
from velithon import Velithon
from velithon.gateway import GatewayRoute

app = Velithon()

# Configure load balancing with Gateway Route
route = GatewayRoute(
    path="/api/{path:path}",
    targets=[
        "http://server1.example.com:8000",
        "http://server2.example.com:8000",
        "http://server3.example.com:8000"
    ],
    load_balancing_strategy="round_robin",  # round_robin, random, weighted
    weights=[1, 1, 2],  # Optional: for weighted strategy
    health_check_path="/health",
    timeout_ms=30000,
    max_retries=3
)

app.routes.append(route)
```

### Using Proxy Middleware

```python
from velithon import Velithon
from velithon.middleware.proxy import ProxyMiddleware

app = Velithon()

# Configure load balancing with Proxy Middleware
proxy_middleware = ProxyMiddleware(
    targets=[
        "http://server1.example.com:8000",
        "http://server2.example.com:8000", 
        "http://server3.example.com:8000"
    ],
    load_balancing_strategy="round_robin",
    weights=[1, 1, 2],  # Optional: for weighted strategy
    health_check_path="/health",
    health_check_interval=30,
    timeout_ms=30000,
    max_retries=3,
    path_prefix="/api"
)

app.add_middleware(proxy_middleware)
```

## Strategies

### Round Robin
Distributes requests evenly across all available servers (default strategy).

```python
from velithon.gateway import GatewayRoute

route = GatewayRoute(
    path="/service/{path:path}",
    targets=["http://server1:8080", "http://server2:8080", "http://server3:8080"],
    load_balancing_strategy="round_robin"
)
```

### Random
Randomly selects a server for each request.

```python
route = GatewayRoute(
    path="/service/{path:path}",
    targets=["http://server1:8080", "http://server2:8080"],
    load_balancing_strategy="random"
)
```

### Weighted Round Robin
Distributes requests based on server weights, allowing you to send more traffic to higher-capacity servers.

```python
route = GatewayRoute(
    path="/service/{path:path}",
    targets=["http://high-capacity:8080", "http://standard:8080", "http://backup:8080"],
    load_balancing_strategy="weighted",
    weights=[3, 2, 1]  # 50%, 33%, 17% of traffic respectively
)
```

## Health Checks

Health checks ensure that traffic is only sent to healthy backend servers.

### Automatic Health Checks

```python
from velithon.gateway import GatewayRoute

# Health checks are automatic when configured
route = GatewayRoute(
    path="/api/{path:path}",
    targets=["http://server1:8080", "http://server2:8080"],
    health_check_path="/health"  # Custom health check endpoint
)

# Your backend services should implement a health endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
```

### Manual Health Checks

```python
from velithon._velithon import ProxyLoadBalancer

# Create load balancer for direct health checking
lb = ProxyLoadBalancer(
    targets=["http://service1:8080", "http://service2:8080"],
    health_check_url="/health"
)

# Perform manual health check
await lb.health_check()

# Get health status
health_status = await lb.get_health_status()
for target, is_healthy in health_status:
    print(f"{target}: {'healthy' if is_healthy else 'unhealthy'}")
```

## Integration Examples

### Gateway Integration

```python
from velithon import Velithon
from velithon.gateway import Gateway, GatewayRoute

app = Velithon()
gateway = Gateway()

# Create load-balanced routes
api_route = GatewayRoute(
    path="/api/{path:path}",
    targets=[
        "http://api-server1:8080",
        "http://api-server2:8080",
        "http://api-server3:8080"
    ],
    load_balancing_strategy="round_robin",
    health_check_path="/health"
)

# Add to gateway and application
gateway.routes.append(api_route)
app.routes.extend(gateway.routes)
```

### Proxy Middleware Integration

```python
from velithon import Velithon
from velithon.middleware.proxy import ProxyMiddleware

app = Velithon()

# Add proxy middleware with load balancing
proxy = ProxyMiddleware(
    targets=[
        "http://backend1:8080",
        "http://backend2:8080"
    ],
    load_balancing_strategy="weighted",
    weights=[70, 30],  # 70% to backend1, 30% to backend2
    path_prefix="/api",
    health_check_path="/health"
)

app.add_middleware(proxy)
```

## Monitoring

### Load Balancer Status

```python
from velithon._velithon import ProxyLoadBalancer

@app.get("/load-balancer/status")
async def lb_status():
    lb = ProxyLoadBalancer(
        targets=["http://server1:8080", "http://server2:8080"]
    )
    
    health_status = await lb.get_health_status()
    
    return {
        "targets": [target for target, _ in health_status],
        "healthy": [target for target, healthy in health_status if healthy],
        "unhealthy": [target for target, healthy in health_status if not healthy]
    }
```

### Gateway Health Monitoring

```python
from velithon.gateway import Gateway

gateway = Gateway()

@app.get("/gateway/health")
async def gateway_health():
    health_status = await gateway.health_check_all()
    return {
        "status": "healthy" if health_status else "degraded",
        "backends": health_status
    }
```

### Proxy Middleware Status

```python
from velithon.middleware.proxy import ProxyMiddleware

# Access proxy status
proxy_middleware = ProxyMiddleware(targets=["http://server:8080"])

@app.get("/proxy/status")
async def proxy_status():
    return await proxy_middleware.get_proxy_status()
```

## Best Practices

- **Monitor server health**: Implement comprehensive health check endpoints
- **Set appropriate weights**: Use weighted load balancing for gradual migrations
- **Track response times**: Monitor latency across all backend servers
- **Set up alerts**: Configure alerts for server failures and degraded performance
- **Use circuit breakers**: Built-in circuit breaker prevents cascading failures
- **Test failover**: Regularly test server failure scenarios
