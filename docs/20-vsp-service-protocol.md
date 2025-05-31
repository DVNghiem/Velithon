# VSP (Velithon Service Protocol) Documentation

## Overview

VSP (Velithon Service Protocol) is a high-performance, asynchronous service communication framework built into Velithon. It enables distributed microservice architectures with service discovery, load balancing, and message passing capabilities.

## Key Features

- **Service Discovery**: Support for static, mDNS, and Consul-based service discovery
- **Load Balancing**: Built-in round-robin load balancing with support for custom strategies
- **Async Communication**: Full async/await support for non-blocking service calls
- **Service Mesh**: Integrated service mesh for managing distributed services
- **Health Monitoring**: Automatic health checking and service status management
- **Multi-Worker Support**: Both asyncio and multicore worker types
- **Transport Layer**: Pluggable transport layer with TCP support

## Architecture

VSP consists of several key components:

- **VSPManager**: Main service manager handling workers and message processing
- **VSPClient**: Client for making calls to remote services
- **ServiceMesh**: Service discovery and load balancing coordination
- **VSPProtocol**: Network protocol implementation
- **VSPMessage**: Message format for service communication

## Quick Start

### Creating a VSP Service

```python
from velithon.vsp import VSPManager, WorkerType

# Create a VSP manager
manager = VSPManager(
    name="user-service",
    num_workers=4,
    worker_type=WorkerType.ASYNCIO
)

# Define service endpoints
@manager.vsp_service("get_user")
async def get_user(user_id: int) -> dict:
    return {"id": user_id, "name": "John Doe"}

@manager.vsp_service("create_user")
async def create_user(name: str, email: str) -> dict:
    return {"id": 123, "name": name, "email": email}

# Start the service
async def main():
    await manager.start_server("localhost", 8001)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Making Service Calls

```python
from velithon.vsp import VSPManager, ServiceMesh, ServiceInfo

# Setup service mesh with known services
mesh = ServiceMesh(discovery_type="static")
mesh.register(ServiceInfo("user-service", "localhost", 8001))

# Create client
client_manager = VSPManager("client", service_mesh=mesh)

# Make service calls
@client_manager.vsp_call("user-service", "get_user")
async def get_user_remote(**kwargs):
    pass

# Use the decorated function
async def main():
    user = await get_user_remote(user_id=123)
    print(user)  # {'id': 123, 'name': 'John Doe'}
```

## Configuration

### Worker Types

VSP supports two worker types:

- **ASYNCIO**: Single-process, multi-coroutine workers (default)
- **MULTICORE**: Multi-process workers for CPU-intensive tasks

```python
from velithon.vsp import WorkerType

# Asyncio workers (lightweight, good for I/O)
manager = VSPManager(
    name="io-service",
    worker_type=WorkerType.ASYNCIO,
    num_workers=10
)

# Multicore workers (CPU-intensive tasks)
manager = VSPManager(
    name="cpu-service", 
    worker_type=WorkerType.MULTICORE,
    num_workers=4
)
```

### Service Discovery

#### Static Discovery (Default)

```python
from velithon.vsp import ServiceMesh, ServiceInfo

mesh = ServiceMesh(discovery_type="static")
mesh.register(ServiceInfo("auth-service", "localhost", 8001))
mesh.register(ServiceInfo("user-service", "localhost", 8002))
```

#### mDNS Discovery

```python
mesh = ServiceMesh(discovery_type="mdns")
# Services are automatically discovered via mDNS
```

#### Consul Discovery

```python
mesh = ServiceMesh(
    discovery_type="consul",
    consul_host="localhost",
    consul_port=8500
)
```

## Advanced Usage

### Custom Load Balancing

```python
from velithon.vsp.load_balancer import LoadBalancer
from velithon.vsp import ServiceInfo
from typing import List
import random

class WeightedRandomBalancer(LoadBalancer):
    def select(self, instances: List[ServiceInfo]) -> ServiceInfo:
        weights = [instance.weight for instance in instances]
        return random.choices(instances, weights=weights)[0]

# Use custom load balancer
mesh = ServiceMesh(
    discovery_type="static",
    load_balancer=WeightedRandomBalancer()
)
```

### Health Monitoring

Services automatically perform health checks. You can manually manage service health:

```python
# Mark service as unhealthy
service_info = ServiceInfo("problematic-service", "localhost", 8003)
service_info.mark_unhealthy()

# Mark service as healthy
service_info.mark_healthy()
```

### Connection Management

```python
# Configure connection pool
manager = VSPManager(
    name="service",
    max_transports=10,  # Max connections per service
    max_queue_size=2000  # Message queue size
)
```

## Error Handling

VSP provides comprehensive error handling:

```python
from velithon.vsp.message import VSPError

try:
    result = await client.call("nonexistent-service", "endpoint", {})
except VSPError as e:
    print(f"Service call failed: {e}")
```

## Message Format

VSP uses a structured message format:

```python
{
    "header": {
        "request_id": "uuid-string",
        "service": "service-name", 
        "endpoint": "endpoint-name",
        "is_response": false,
        "timestamp": 1640995200.0
    },
    "payload": {
        "param1": "value1",
        "param2": "value2"
    }
}
```

## Performance Tuning

### Message Queue Optimization

```python
manager = VSPManager(
    name="high-throughput-service",
    num_workers=8,
    max_queue_size=5000,  # Larger queue for high load
    worker_type=WorkerType.ASYNCIO
)
```

### Transport Pool Tuning

```python
# Adjust connection pool size based on load
client = VSPClient(
    service_mesh=mesh,
    transport_factory=lambda m: TCPTransport(m),
    max_transports=20  # More connections for high load
)
```

## Best Practices

1. **Service Naming**: Use descriptive, consistent service names
2. **Error Handling**: Always wrap service calls in try-catch blocks
3. **Health Checks**: Implement custom health check logic for complex services
4. **Resource Management**: Properly close managers and clients
5. **Monitoring**: Log service calls and monitor performance metrics

## Integration with Velithon Web Framework

VSP can be integrated with Velithon's web framework for building microservice architectures:

```python
from velithon import Velithon
from velithon.vsp import VSPManager, ServiceMesh

app = Velithon()
vsp_manager = VSPManager("web-service")

@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: int):
    # Call VSP service
    user = await vsp_manager.client.call("user-service", "get_user", {"user_id": user_id})
    return user

# Start both web server and VSP service
async def startup():
    # Start VSP service
    await vsp_manager.start_server("localhost", 8001)
    
app.on_startup(startup)
```

## Troubleshooting

### Common Issues

1. **Service Not Found**: Check service registration and discovery configuration
2. **Connection Refused**: Verify service is running and ports are accessible
3. **Message Queue Full**: Increase `max_queue_size` or add more workers
4. **High Latency**: Check network connectivity and consider connection pooling

### Debugging

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("velithon.vsp")
```

## API Reference

See the full API documentation for detailed method signatures and parameters:

- [VSPManager API](../api/vsp/manager.md)
- [VSPClient API](../api/vsp/client.md) 
- [ServiceMesh API](../api/vsp/mesh.md)
- [VSPMessage API](../api/vsp/message.md)
