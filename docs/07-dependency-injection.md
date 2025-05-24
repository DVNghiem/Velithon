# Dependency Injection

Velithon provides a powerful dependency injection system.

## Setting Up a Container

```python
from velithon.di import ServiceContainer, SingletonProvider, FactoryProvider, AsyncFactoryProvider

class Database:
    async def query(self, sql: str):
        return {"result": f"Data for: {sql}"}

class UserRepository:
    def __init__(self, db: Database):
        self.db = db
    
    async def find_user(self, user_id: int):
        return await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

class UserService:
    def __init__(self, user_repository: UserRepository, api_key: str):
        self.user_repository = user_repository
        self.api_key = api_key
    
    async def get_user(self, user_id: int):
        return await self.user_repository.find_user(user_id)

async def create_user_service(user_repository: UserRepository, api_key: str = "default-key") -> UserService:
    return UserService(user_repository, api_key)

class Container(ServiceContainer):
    db = SingletonProvider(Database)
    user_repository = FactoryProvider(UserRepository, db=db)
    user_service = AsyncFactoryProvider(create_user_service, user_repository=user_repository, api_key="my-api-key")

container = Container()
app.register_container(container)
```

## Using Dependency Injection

```python
from velithon.di import inject, Provide

class UserEndpoint(HTTPEndpoint):
    @inject
    async def get(self, user_service: UserService = Provide[container.user_service]):
        user_data = await user_service.get_user(123)
        return JSONResponse(user_data)

# Function-based endpoint with DI
@inject
@app.get("/users/{user_id}")
async def get_user(user_id: int, user_service: UserService = Provide[container.user_service]):
    user_data = await user_service.get_user(user_id)
    return JSONResponse(user_data)
```

## Provider Types

1. **SingletonProvider**: Creates and reuses a single instance
2. **FactoryProvider**: Creates a new instance each time
3. **AsyncFactoryProvider**: Uses an async function to create instances

```python
class Container(ServiceContainer):
    # Singleton - one instance for the entire application
    db = SingletonProvider(Database)
    
    # Factory - new instance per request
    user_repo = FactoryProvider(UserRepository, db=db)
    
    # Async Factory - for complex async initialization
    user_service = AsyncFactoryProvider(create_user_service, user_repository=user_repo)
```
