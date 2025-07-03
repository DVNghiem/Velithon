# Load Balancing

Velithon supports load balancing configurations for distributing traffic across multiple application instances.

## Overview

Load balancing ensures high availability and optimal performance by distributing incoming requests across multiple server instances.

## Configuration

```python
from velithon import Velithon
from velithon.proxy import ProxySettings

app = Velithon()

# Configure load balancing
load_balancer_config = {
    "strategy": "round_robin",  # round_robin, least_connections, weighted
    "health_check": {
        "enabled": True,
        "interval": 30,
        "timeout": 5,
        "path": "/health"
    },
    "upstream_servers": [
        {"host": "server1.example.com", "port": 8000, "weight": 1},
        {"host": "server2.example.com", "port": 8000, "weight": 1},
        {"host": "server3.example.com", "port": 8000, "weight": 2}
    ]
}
```

## Strategies

### Round Robin
Distributes requests evenly across all available servers.

### Least Connections
Routes requests to the server with the fewest active connections.

### Weighted Round Robin
Distributes requests based on server weights.

## Health Checks

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

## Integration with Proxy Feature

```python
from velithon.proxy import create_proxy_handler

@app.route("/api/{path:path}")
async def proxy_api(request):
    return await create_proxy_handler(
        upstream_servers=load_balancer_config["upstream_servers"],
        strategy=load_balancer_config["strategy"]
    )(request)
```

## Monitoring

- Monitor server health and response times
- Track request distribution across servers
- Set up alerts for server failures
- Log load balancing decisions for debugging
