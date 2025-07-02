# Dependency Injection

Velithon provides a powerful and high-performance dependency injection (DI) system that uses Rust optimizations for enhanced speed and efficiency. The DI system helps manage dependencies between components, making your code more modular, testable, and maintainable.

## Core Concepts

### Service Container

The `ServiceContainer` is the central registry that manages all your application's dependencies:

```python
from velithon.di import ServiceContainer, SingletonProvider, FactoryProvider, AsyncFactoryProvider

class AppContainer(ServiceContainer):
    # Define providers as class attributes
    database = SingletonProvider(Database)
    user_repository = FactoryProvider(UserRepository, database=database)
    user_service = AsyncFactoryProvider(create_user_service, user_repository=user_repository)

# Create and register with the application
container = AppContainer()
app.register_container(container)
```

### Providers

Providers define how services are created and managed:

- **SingletonProvider**: Creates one instance for the entire application lifecycle
- **FactoryProvider**: Creates a new instance every time it's requested
- **AsyncFactoryProvider**: Uses async functions for complex initialization

### Dependency Injection

Use the `@inject` decorator and `Provide` annotation to inject dependencies:

```python
from velithon.di import inject, Provide

@inject
async def get_user(user_id: int, user_service: UserService = Provide[container.user_service]):
    return await user_service.get_user(user_id)
```

## Setting Up Dependencies

### Basic Service Classes

First, define your service classes:

```python
class Database:
    def __init__(self, connection_string: str = "sqlite:///app.db"):
        self.connection_string = connection_string
    
    async def query(self, sql: str) -> dict:
        # Simulate database query
        return {"result": f"Data for: {sql}"}
    
    async def execute(self, sql: str) -> bool:
        # Simulate database execution
        return True

class UserRepository:
    def __init__(self, database: Database):
        self.database = database
    
    async def find_user(self, user_id: int) -> dict:
        return await self.database.query(f"SELECT * FROM users WHERE id = {user_id}")
    
    async def create_user(self, user_data: dict) -> dict:
        await self.database.execute(f"INSERT INTO users ...")
        return {"id": 123, **user_data}
    
    async def update_user(self, user_id: int, user_data: dict) -> dict:
        await self.database.execute(f"UPDATE users SET ... WHERE id = {user_id}")
        return {"id": user_id, **user_data}

class UserService:
    def __init__(self, user_repository: UserRepository, cache_ttl: int = 300):
        self.user_repository = user_repository
        self.cache_ttl = cache_ttl
        self._cache = {}
    
    async def get_user(self, user_id: int) -> dict:
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id]
        
        # Fetch from repository
        user = await self.user_repository.find_user(user_id)
        self._cache[user_id] = user
        return user
    
    async def create_user(self, user_data: dict) -> dict:
        return await self.user_repository.create_user(user_data)
    
    async def update_user(self, user_id: int, user_data: dict) -> dict:
        user = await self.user_repository.update_user(user_id, user_data)
        # Update cache
        self._cache[user_id] = user
        return user
```

### Async Factory Functions

For complex initialization, use async factory functions:

```python
async def create_user_service(
    user_repository: UserRepository, 
    cache_ttl: int = 300,
    enable_notifications: bool = True
) -> UserService:
    """Factory function for creating UserService with complex initialization."""
    service = UserService(user_repository, cache_ttl)
    
    if enable_notifications:
        # Initialize notification system
        await service.setup_notifications()
    
    return service

async def create_email_service(
    smtp_host: str = "localhost",
    smtp_port: int = 587,
    username: str = "",
    password: str = ""
) -> EmailService:
    """Factory function for EmailService with async initialization."""
    service = EmailService(smtp_host, smtp_port)
    
    if username and password:
        await service.authenticate(username, password)
    
    return service
```

### Container Definition

Define your container with all providers:

```python
class AppContainer(ServiceContainer):
    # Singleton providers (one instance per application)
    database = SingletonProvider(
        Database, 
        connection_string="postgresql://user:pass@localhost/db"
    )
    
    # Factory providers (new instance per request)
    user_repository = FactoryProvider(
        UserRepository, 
        database=database
    )
    
    # Async factory providers (for complex async initialization)
    user_service = AsyncFactoryProvider(
        create_user_service,
        user_repository=user_repository,
        cache_ttl=600,
        enable_notifications=True
    )
    
    email_service = AsyncFactoryProvider(
        create_email_service,
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="app@example.com",
        password="secret"
    )

# Create container instance
container = AppContainer()
```

## Using Dependency Injection

### In HTTP Endpoints

#### Class-based Endpoints

```python
from velithon.endpoint import HTTPEndpoint
from velithon.di import inject, Provide
from velithon.responses import JSONResponse

class UserEndpoint(HTTPEndpoint):
    @inject
    async def get(self, user_id: int, user_service: UserService = Provide[container.user_service]):
        """Get a user by ID."""
        try:
            user = await user_service.get_user(user_id)
            return JSONResponse(user)
        except UserNotFoundError:
            return JSONResponse({"error": "User not found"}, status_code=404)
    
    @inject
    async def post(self, request: Request, user_service: UserService = Provide[container.user_service]):
        """Create a new user."""
        user_data = await request.json()
        user = await user_service.create_user(user_data)
        return JSONResponse(user, status_code=201)
    
    @inject
    async def put(
        self, 
        user_id: int, 
        request: Request,
        user_service: UserService = Provide[container.user_service]
    ):
        """Update a user."""
        user_data = await request.json()
        user = await user_service.update_user(user_id, user_data)
        return JSONResponse(user)

# Register the endpoint
app.add_route("/users/{user_id}", UserEndpoint)
```

#### Function-based Endpoints

```python
@app.get("/users/{user_id}")
@inject
async def get_user(user_id: int, user_service: UserService = Provide[container.user_service]):
    user = await user_service.get_user(user_id)
    return JSONResponse(user)

@app.post("/users")
@inject
async def create_user(
    request: Request,
    user_service: UserService = Provide[container.user_service],
    email_service: EmailService = Provide[container.email_service]
):
    user_data = await request.json()
    user = await user_service.create_user(user_data)
    
    # Send welcome email
    await email_service.send_welcome_email(user["email"], user["name"])
    
    return JSONResponse(user, status_code=201)

@app.get("/health")
@inject
async def health_check(database: Database = Provide[container.database]):
    try:
        # Test database connection
        await database.query("SELECT 1")
        return JSONResponse({"status": "healthy", "database": "connected"})
    except Exception as e:
        return JSONResponse(
            {"status": "unhealthy", "database": "disconnected", "error": str(e)},
            status_code=503
        )
```

### Multiple Dependencies

Inject multiple dependencies in a single function:

```python
@app.post("/users/{user_id}/send-email")
@inject
async def send_user_email(
    user_id: int,
    request: Request,
    user_service: UserService = Provide[container.user_service],
    email_service: EmailService = Provide[container.email_service]
):
    # Get user data
    user = await user_service.get_user(user_id)
    
    # Get email content from request
    email_data = await request.json()
    
    # Send email
    await email_service.send_email(
        to=user["email"],
        subject=email_data["subject"],
        body=email_data["body"]
    )
    
    return JSONResponse({"message": "Email sent successfully"})
```

### Accessing Scope

You can also inject the current request scope:

```python
from velithon.datastructures import Scope

@app.get("/request-info")
@inject
async def request_info(
    scope: Scope,
    user_service: UserService = Provide[container.user_service]
):
    return JSONResponse({
        "method": scope.method,
        "path": scope.path,
        "headers": dict(scope.headers),
        "user_service_type": type(user_service).__name__
    })
```

## Provider Types in Detail

### SingletonProvider

Creates and caches a single instance for the entire application:

```python
class AppContainer(ServiceContainer):
    # Database connection should be singleton
    database = SingletonProvider(Database, connection_string="...")
    
    # Configuration service
    config = SingletonProvider(ConfigService)
    
    # Logger
    logger = SingletonProvider(LoggerService, level="INFO")
```

Use singletons for:
- Database connections
- Configuration services
- Logging services
- Cache managers
- Shared resources

### FactoryProvider

Creates a new instance every time it's requested:

```python
class AppContainer(ServiceContainer):
    database = SingletonProvider(Database)
    
    # New repository instance per request
    user_repository = FactoryProvider(UserRepository, database=database)
    order_repository = FactoryProvider(OrderRepository, database=database)
```

Use factories for:
- Repository classes
- Request-scoped services
- Stateful services that shouldn't be shared

### AsyncFactoryProvider

Uses async functions for complex initialization:

```python
async def create_redis_service(host: str = "localhost", port: int = 6379):
    service = RedisService(host, port)
    await service.connect()  # Async initialization
    return service

async def create_notification_service(
    email_service: EmailService,
    sms_service: SMSService,
    push_service: PushService
):
    service = NotificationService()
    await service.register_providers(email_service, sms_service, push_service)
    return service

class AppContainer(ServiceContainer):
    email_service = AsyncFactoryProvider(create_email_service)
    sms_service = AsyncFactoryProvider(create_sms_service)
    push_service = AsyncFactoryProvider(create_push_service)
    
    # Complex service with multiple dependencies
    notification_service = AsyncFactoryProvider(
        create_notification_service,
        email_service=email_service,
        sms_service=sms_service,
        push_service=push_service
    )
    
    # Redis with async initialization
    redis = AsyncFactoryProvider(create_redis_service, host="redis.example.com")
```

## Advanced Features

### Conditional Dependencies

Use different implementations based on configuration:

```python
class DevelopmentDatabase(Database):
    def __init__(self):
        super().__init__("sqlite:///dev.db")

class ProductionDatabase(Database):
    def __init__(self):
        super().__init__("postgresql://prod-server/db")

def create_database(environment: str = "development"):
    if environment == "production":
        return ProductionDatabase()
    else:
        return DevelopmentDatabase()

class AppContainer(ServiceContainer):
    database = AsyncFactoryProvider(create_database, environment="development")
```

### Circular Dependency Detection

Velithon automatically detects and prevents circular dependencies:

```python
# This would raise a CircularDependencyError
class BadContainer(ServiceContainer):
    service_a = FactoryProvider(ServiceA, service_b=service_b)
    service_b = FactoryProvider(ServiceB, service_a=service_a)  # Circular!
```

### Performance Optimizations

The DI system includes several performance optimizations:

- **Rust-accelerated resolution**: Core resolution logic implemented in Rust
- **Signature caching**: Function signatures are cached for faster introspection
- **Precomputed mappings**: Dependency mappings are computed at decoration time
- **Singleton caching**: Singleton instances are cached efficiently

### Testing with DI

Override dependencies for testing:

```python
class TestContainer(ServiceContainer):
    # Use mock database for testing
    database = SingletonProvider(MockDatabase)
    user_repository = FactoryProvider(UserRepository, database=database)
    user_service = FactoryProvider(UserService, user_repository=user_repository)

# In your tests
def test_user_endpoint():
    test_container = TestContainer()
    app.register_container(test_container)
    
    # Now all endpoints will use mock dependencies
    # ... test code ...
```

## Best Practices

### 1. Keep Dependencies Focused

Each service should have a single responsibility:

```python
# Good: Focused responsibilities
class UserRepository:
    def find_user(self, user_id): ...
    def create_user(self, user_data): ...

class EmailService:
    def send_email(self, to, subject, body): ...

# Better than: Mixed responsibilities
class UserManager:  # Too broad
    def find_user(self, user_id): ...
    def send_welcome_email(self, user): ...
    def validate_user_data(self, data): ...
```

### 2. Use Appropriate Provider Types

- Singletons for shared, stateless resources
- Factories for request-scoped or stateful services
- Async factories for services requiring async initialization

### 3. Define Clear Interfaces

Use abstract base classes or protocols for better testing:

```python
from abc import ABC, abstractmethod

class UserRepositoryInterface(ABC):
    @abstractmethod
    async def find_user(self, user_id: int) -> dict: ...

class DatabaseUserRepository(UserRepositoryInterface):
    def __init__(self, database: Database):
        self.database = database
    
    async def find_user(self, user_id: int) -> dict:
        return await self.database.query(f"SELECT * FROM users WHERE id = {user_id}")
```

### 4. Avoid Deep Dependency Chains

Keep dependency graphs shallow and manageable:

```python
# Prefer: Shallow dependencies
class UserService:
    def __init__(self, user_repository: UserRepository): ...

# Over: Deep chains
class UserService:
    def __init__(self, user_manager: UserManager): ...

class UserManager:
    def __init__(self, user_repository: UserRepository): ...

class UserRepository:
    def __init__(self, database_manager: DatabaseManager): ...
```

This dependency injection system provides a robust foundation for building scalable, maintainable applications with clear separation of concerns and excellent testability.
