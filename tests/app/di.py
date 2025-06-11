import logging

from velithon.di import Provide, inject
from velithon.endpoint import HTTPEndpoint
from velithon.responses import PlainTextResponse

from .container import MockDatabase, MockUserRepository, MockUserService, container

logger = logging.getLogger(__name__)

class TestSingletonProvider(HTTPEndpoint):
    @inject
    async def get(self, db: MockDatabase = Provide[container.db]):
        assert isinstance(db, MockDatabase)
        return PlainTextResponse("success")
    
class TestFactoryProvider(HTTPEndpoint):
    @inject
    async def get(self, user_repository: MockUserRepository = Provide[container.user_repository]):
        assert isinstance(user_repository, MockUserRepository)
        return PlainTextResponse("success")
    
class TestAsyncFactoryProvider(HTTPEndpoint):
    @inject
    async def get(self, user_service: MockUserService = Provide[container.user_service]):
        assert isinstance(user_service, MockUserService)
        return PlainTextResponse("success")