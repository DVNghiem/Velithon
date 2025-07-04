# Connection Pooling

Velithon provides efficient connection pooling capabilities for optimal performance in high-traffic applications.

## Overview

Connection pooling helps manage database and external service connections efficiently by reusing existing connections rather than creating new ones for each request.

## Configuration

```python
from velithon import Velithon
from velithon.di import ServiceContainer, Provide, SingletonProvider, FactoryProvider

app = Velithon()

# Configure connection pool settings
class DatabaseConfig:
    def __init__(self):
        self.pool_size = 20
        self.max_overflow = 10
        self.pool_timeout = 30

class AppContainer(ServiceContainer):
    database_config = SingletonProvider(DatabaseConfig)
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

class AppContainer(ServiceContainer):
    database_config = SingletonProvider(DatabaseConfig)
    database_service = FactoryProvider(DatabaseService, factory=lambda: DatabaseService(container.database_config))

container = AppContainer()

@app.get("/users")
@inject
async def get_users(db_service: DatabaseService = Provide[container.database_service]):
    # Use pooled connection
    return await db_service.get_all_users()
```

## Best Practices

- Configure appropriate pool sizes based on your application's needs
- Monitor connection usage and adjust pool settings accordingly
- Use connection pooling for database connections and external HTTP clients
- Implement proper connection lifecycle management
