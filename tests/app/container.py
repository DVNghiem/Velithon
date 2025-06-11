from velithon.di import AsyncFactoryProvider, FactoryProvider, ServiceContainer, SingletonProvider


class MockDatabase:
    async def query(self, q: str):
        return {"result": f"Mock data: {q}"}

class MockUserRepository:
    def __init__(self, db: MockDatabase):
        self.db = db

    async def find_user(self, user_id: int):
        return await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

class MockUserService:
    def __init__(self, user_repository: MockUserRepository, api_key: str):
        self.user_repository = user_repository
        self.api_key = api_key

    async def get_user(self, user_id: int):
        return await self.user_repository.find_user(user_id)

async def create_user_service(user_repository: MockUserRepository, api_key: str = "xyz") -> MockUserService:
    return MockUserService(user_repository, api_key)

class Container(ServiceContainer):
    db = SingletonProvider(MockDatabase)
    user_repository = FactoryProvider(MockUserRepository, db=db)
    user_service = AsyncFactoryProvider(create_user_service, user_repository=user_repository, api_key="xyz")

container = Container()