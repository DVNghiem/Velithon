# VSP Examples

This document provides practical examples of using VSP (Velithon Service Protocol) for building distributed applications.

## Example 1: Simple Microservice Architecture

### User Service

```python
# user_service.py
import asyncio
from velithon.vsp import VSPManager, WorkerType

# In-memory user storage for demo
users_db = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"}
}

manager = VSPManager(
    name="user-service",
    num_workers=4,
    worker_type=WorkerType.ASYNCIO
)

@manager.vsp_service("get_user")
async def get_user(user_id: int) -> dict:
    """Get user by ID"""
    user = users_db.get(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user

@manager.vsp_service("create_user")
async def create_user(name: str, email: str) -> dict:
    """Create a new user"""
    user_id = max(users_db.keys()) + 1 if users_db else 1
    user = {"id": user_id, "name": name, "email": email}
    users_db[user_id] = user
    return user

@manager.vsp_service("list_users")
async def list_users() -> dict:
    """List all users"""
    return {"users": list(users_db.values())}

async def main():
    print("Starting User Service on localhost:8001")
    await manager.start_server("localhost", 8001)

if __name__ == "__main__":
    asyncio.run(main())
```

### Order Service

```python
# order_service.py
import asyncio
from velithon.vsp import VSPManager, ServiceMesh, ServiceInfo

# Setup service mesh to find user service
mesh = ServiceMesh(discovery_type="static")
mesh.register(ServiceInfo("user-service", "localhost", 8001))

manager = VSPManager(
    name="order-service",
    service_mesh=mesh,
    num_workers=2
)

# In-memory order storage
orders_db = {}
order_counter = 0

@manager.vsp_call("user-service", "get_user")
async def get_user_remote(**kwargs):
    """Remote call to user service"""
    pass

@manager.vsp_service("create_order")
async def create_order(user_id: int, product: str, quantity: int) -> dict:
    """Create an order for a user"""
    global order_counter
    
    # Verify user exists
    try:
        user = await get_user_remote(user_id=user_id)
    except Exception as e:
        raise ValueError(f"Cannot create order: {str(e)}")
    
    # Create order
    order_counter += 1
    order = {
        "id": order_counter,
        "user_id": user_id,
        "user_name": user["name"],
        "product": product,
        "quantity": quantity,
        "total": quantity * 10.0  # Simple pricing
    }
    orders_db[order_counter] = order
    return order

@manager.vsp_service("get_orders")
async def get_orders(user_id: int) -> dict:
    """Get orders for a user"""
    user_orders = [order for order in orders_db.values() if order["user_id"] == user_id]
    return {"orders": user_orders}

async def main():
    print("Starting Order Service on localhost:8002")
    await manager.start_server("localhost", 8002)

if __name__ == "__main__":
    asyncio.run(main())
```

### API Gateway

```python
# api_gateway.py
import asyncio
from velithon import Velithon
from velithon.vsp import VSPManager, ServiceMesh, ServiceInfo

# Setup service mesh
mesh = ServiceMesh(discovery_type="static")
mesh.register(ServiceInfo("user-service", "localhost", 8001))
mesh.register(ServiceInfo("order-service", "localhost", 8002))

# VSP manager for the gateway
vsp_manager = VSPManager("api-gateway", service_mesh=mesh)

# Web application
app = Velithon()

# User endpoints
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    try:
        response = await vsp_manager.client.call("user-service", "get_user", {"user_id": user_id})
        return response
    except Exception as e:
        return {"error": str(e)}

@app.post("/users")
async def create_user(name: str, email: str):
    try:
        response = await vsp_manager.client.call("user-service", "create_user", {"name": name, "email": email})
        return response
    except Exception as e:
        return {"error": str(e)}

@app.get("/users")
async def list_users():
    try:
        response = await vsp_manager.client.call("user-service", "list_users", {})
        return response
    except Exception as e:
        return {"error": str(e)}

# Order endpoints
@app.post("/orders")
async def create_order(user_id: int, product: str, quantity: int):
    try:
        response = await vsp_manager.client.call("order-service", "create_order", {
            "user_id": user_id,
            "product": product,
            "quantity": quantity
        })
        return response
    except Exception as e:
        return {"error": str(e)}

@app.get("/users/{user_id}/orders")
async def get_user_orders(user_id: int):
    try:
        response = await vsp_manager.client.call("order-service", "get_orders", {"user_id": user_id})
        return response
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import granian
    granian.Granian("api_gateway:app", host="127.0.0.1", port=8000).serve()
```

## Example 2: CPU-Intensive Processing Service

```python
# calculation_service.py
import asyncio
import math
from velithon.vsp import VSPManager, WorkerType

manager = VSPManager(
    name="calculation-service",
    num_workers=4,
    worker_type=WorkerType.MULTICORE  # Use multicore for CPU tasks
)

@manager.vsp_service("factorial")
async def calculate_factorial(n: int) -> dict:
    """Calculate factorial using multicore processing"""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n > 1000:
        raise ValueError("Number too large")
    
    result = math.factorial(n)
    return {"input": n, "factorial": result}

@manager.vsp_service("prime_check")
async def check_prime(n: int) -> dict:
    """Check if a number is prime"""
    if n < 2:
        return {"input": n, "is_prime": False}
    
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return {"input": n, "is_prime": False}
    
    return {"input": n, "is_prime": True}

@manager.vsp_service("fibonacci")
async def calculate_fibonacci(n: int) -> dict:
    """Calculate nth Fibonacci number"""
    if n < 0:
        raise ValueError("Fibonacci not defined for negative numbers")
    if n > 100:
        raise ValueError("Number too large")
    
    if n <= 1:
        return {"input": n, "fibonacci": n}
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return {"input": n, "fibonacci": b}

async def main():
    print("Starting Calculation Service on localhost:8003")
    await manager.start_server("localhost", 8003)

if __name__ == "__main__":
    asyncio.run(main())
```

## Example 3: Service Discovery with Consul

```python
# consul_example.py
import asyncio
from velithon.vsp import VSPManager, ServiceMesh

# Service using Consul for discovery
mesh = ServiceMesh(
    discovery_type="consul",
    consul_host="localhost",
    consul_port=8500
)

manager = VSPManager(
    name="analytics-service",
    service_mesh=mesh
)

@manager.vsp_service("process_data")
async def process_data(data: list) -> dict:
    """Process analytics data"""
    if not data:
        return {"error": "No data provided"}
    
    total = sum(data)
    average = total / len(data)
    maximum = max(data)
    minimum = min(data)
    
    return {
        "count": len(data),
        "sum": total,
        "average": average,
        "max": maximum,
        "min": minimum
    }

@manager.vsp_service("health")
async def health_check() -> dict:
    """Custom health check"""
    return {"status": "healthy", "service": "analytics-service"}

async def main():
    print("Starting Analytics Service with Consul discovery")
    await manager.start_server("localhost", 8004)

if __name__ == "__main__":
    asyncio.run(main())
```

## Example 4: Load Testing Client

```python
# load_test_client.py
import asyncio
import time
from velithon.vsp import VSPManager, ServiceMesh, ServiceInfo

# Setup service mesh
mesh = ServiceMesh(discovery_type="static")
mesh.register(ServiceInfo("user-service", "localhost", 8001))

client_manager = VSPManager("load-test-client", service_mesh=mesh)

async def test_service_performance():
    """Test service performance with concurrent requests"""
    print("Starting load test...")
    
    start_time = time.time()
    tasks = []
    
    # Create 100 concurrent requests
    for i in range(100):
        task = client_manager.client.call("user-service", "get_user", {"user_id": 1})
        tasks.append(task)
    
    # Wait for all requests to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Analyze results
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful
    
    print(f"Load test completed in {duration:.2f} seconds")
    print(f"Successful requests: {successful}")
    print(f"Failed requests: {failed}")
    print(f"Requests per second: {len(results) / duration:.2f}")

async def main():
    await test_service_performance()

if __name__ == "__main__":
    asyncio.run(main())
```

## Example 5: Error Handling and Resilience

```python
# resilient_service.py
import asyncio
import random
from velithon.vsp import VSPManager, ServiceMesh, ServiceInfo
from velithon.vsp.message import VSPError

mesh = ServiceMesh(discovery_type="static")
mesh.register(ServiceInfo("unreliable-service", "localhost", 8005))

manager = VSPManager("resilient-client", service_mesh=mesh)

async def call_with_retry(service: str, endpoint: str, payload: dict, max_retries: int = 3):
    """Call service with retry logic"""
    for attempt in range(max_retries):
        try:
            result = await manager.client.call(service, endpoint, payload)
            return result
        except VSPError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff

@manager.vsp_service("unreliable_operation")
async def unreliable_operation(data: str) -> dict:
    """Simulates an unreliable service operation"""
    # 30% chance of failure
    if random.random() < 0.3:
        raise Exception("Random service failure")
    
    return {"processed": data.upper(), "timestamp": time.time()}

async def main():
    # Start the unreliable service
    server_task = asyncio.create_task(manager.start_server("localhost", 8005))
    
    # Wait a bit for server to start
    await asyncio.sleep(1)
    
    # Test resilient calls
    for i in range(10):
        try:
            result = await call_with_retry(
                "unreliable-service", 
                "unreliable_operation", 
                {"data": f"test-{i}"}
            )
            print(f"Success {i}: {result}")
        except Exception as e:
            print(f"Final failure {i}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Running the Examples

### Prerequisites

1. Start the individual services in separate terminals:
```bash
# Terminal 1
python user_service.py

# Terminal 2  
python order_service.py

# Terminal 3
python api_gateway.py
```

2. Test the API gateway:
```bash
# Create a user
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie", "email": "charlie@example.com"}'

# Get users
curl "http://localhost:8000/users"

# Create an order
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product": "laptop", "quantity": 2}'

# Get user orders
curl "http://localhost:8000/users/1/orders"
```

### Running with Docker

You can also containerize the services:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "user_service.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  user-service:
    build: .
    command: python user_service.py
    ports:
      - "8001:8001"
  
  order-service:
    build: .
    command: python order_service.py
    ports:
      - "8002:8002"
    depends_on:
      - user-service
  
  api-gateway:
    build: .
    command: python api_gateway.py
    ports:
      - "8000:8000"
    depends_on:
      - user-service
      - order-service
```

These examples demonstrate the key features of VSP and how to build scalable microservice architectures with Velithon.
