# Health Checks

Velithon provides health check endpoints for monitoring application and service status.

## Overview

Health checks are essential for monitoring application health, load balancer configuration, and orchestration platforms like Kubernetes.

## Basic Health Check

```python
from velithon import Velithon
from velithon.di import ServiceContainer, Provide, inject, SingletonProvider
from datetime import datetime

app = Velithon()

class HealthService:
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.checks = {}
    
    def add_check(self, name: str, check_func):
        self.checks[name] = check_func
    
    async def get_health_status(self):
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": str(datetime.utcnow() - self.start_time),
            "checks": {}
        }
        
        overall_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                status["checks"][name] = {
                    "status": "healthy" if check_result else "unhealthy",
                    "details": check_result
                }
                if not check_result:
                    overall_healthy = False
            except Exception as e:
                status["checks"][name] = {
                    "status": "error",
                    "error": str(e)
                }
                overall_healthy = False
        
        status["status"] = "healthy" if overall_healthy else "unhealthy"
        return status

class AppContainer(ServiceContainer):
    health_service = SingletonProvider(HealthService)

container = AppContainer()
```

## Health Check Endpoints

```python
@app.get("/health")
@inject
async def health_check(
    health_service: HealthService = Provide[container.health_service]
):
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/detailed")
@inject
async def detailed_health_check(
    health_service: HealthService = Provide[container.health_service]
):
    """Detailed health check with all registered checks"""
    status = await health_service.get_health_status()
    status_code = 200 if status["status"] == "healthy" else 503
    return status, status_code

@app.get("/health/ready")
@inject
async def readiness_check(
    health_service: HealthService = Provide[container.health_service]
):
    """Readiness probe for Kubernetes"""
    # Check if application is ready to serve traffic
    return {"status": "ready"}

@app.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    # Check if application is still running
    return {"status": "alive"}
```

## Custom Health Checks

```python
class DatabaseHealthCheck:
    def __init__(self, db_service):
        self.db_service = db_service
    
    async def __call__(self):
        try:
            # Check database connectivity
            await self.db_service.execute("SELECT 1")
            return True
        except Exception:
            return False

class ExternalServiceHealthCheck:
    def __init__(self, service_url):
        self.service_url = service_url
    
    async def __call__(self):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.service_url}/health", 
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False

# Register health checks
health_service = container.get(HealthService)
health_service.add_check("database", DatabaseHealthCheck(db_service))
health_service.add_check("external_api", ExternalServiceHealthCheck("https://api.example.com"))
```

## Kubernetes Integration

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: velithon-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: velithon-app:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Monitoring Integration

```python
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {
        "http_requests_total": 1234,
        "http_request_duration_seconds": 0.123,
        "active_connections": 42
    }
```

## Best Practices

- Keep health checks lightweight and fast
- Include dependencies in detailed health checks
- Use different endpoints for different purposes (liveness vs readiness)
- Monitor health check response times
- Implement graceful shutdown procedures
