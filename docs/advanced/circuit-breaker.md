# Circuit Breaker

Velithon provides circuit breaker patterns to handle failures gracefully and prevent cascading failures in distributed systems.

## Overview

The circuit breaker pattern helps prevent cascading failures by monitoring for failures and temporarily blocking requests to failing services.

## Implementation

```python
from velithon import Velithon
from velithon.di import ServiceContainer, Provide, inject, SingletonProvider, FactoryProvider
import asyncio
from datetime import datetime, timedelta

app = Velithon()

class CircuitBreakerService:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.reset()
            return result
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def _should_attempt_reset(self):
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout)
        )
    
    def reset(self):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

class AppContainer(ServiceContainer):
    circuit_breaker_service = SingletonProvider(CircuitBreakerService)

container = AppContainer()
```

## Usage Example

```python
class ExternalAPIService:
    def __init__(self, circuit_breaker: CircuitBreakerService):
        self.circuit_breaker = circuit_breaker
    
    async def fetch_data(self, endpoint):
        return await self.circuit_breaker.call(self._make_request, endpoint)
    
    async def _make_request(self, endpoint):
        # Simulate external API call
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint)
            return response.json()

class AppContainer(ServiceContainer):
    circuit_breaker_service = SingletonProvider(CircuitBreakerService)
    external_api_service = FactoryProvider(
        ExternalAPIService,
        factory=lambda: ExternalAPIService(container.circuit_breaker_service)
    )

container = AppContainer()

@app.get("/external-data")
@inject
async def get_external_data(
    api_service: ExternalAPIService = Provide[container.external_api_service]
):
    try:
        data = await api_service.fetch_data("https://api.example.com/data")
        return {"data": data}
    except Exception as e:
        return {"error": "Service temporarily unavailable"}, 503
```

## Configuration

```python
# Circuit breaker with custom settings
circuit_breaker = CircuitBreakerService(
    failure_threshold=3,  # Open after 3 failures
    timeout=30           # Try again after 30 seconds
)
```

## States

- **Closed**: Normal operation, requests pass through
- **Open**: Failures exceeded threshold, requests are blocked
- **Half-Open**: Testing if service has recovered

## Benefits

- Prevents cascading failures
- Improves system resilience
- Reduces load on failing services
- Provides graceful degradation
