# Connection Pooling

Velithon provides efficient connection pooling capabilities for optimal performance in high-traffic applications.

## Overview

Connection pooling helps manage database and external service connections efficiently by reusing existing connections rather than creating new ones for each request.

## Configuration

```python
from velithon import Velithon
from velithon.di import ServiceContainer, Provide

app = Velithon()
container = ServiceContainer()

# Configure connection pool settings
class DatabaseConfig:
    def __init__(self):
        self.pool_size = 20
        self.max_overflow = 10
        self.pool_timeout = 30

container.register(DatabaseConfig, lambda: DatabaseConfig())
```

## Usage with Dependency Injection

```python
from velithon.di import inject

class DatabaseService:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = self._create_pool()
    
    def _create_pool(self):
        # Initialize connection pool
        pass

container.register(DatabaseService, lambda: DatabaseService(container.get(DatabaseConfig)))

@app.get("/users")
@inject
async def get_users(db_service: DatabaseService = Provide(DatabaseService)):
    # Use pooled connection
    return await db_service.get_all_users()
```

## Best Practices

- Configure appropriate pool sizes based on your application's needs
- Monitor connection usage and adjust pool settings accordingly
- Use connection pooling for database connections and external HTTP clients
- Implement proper connection lifecycle management
