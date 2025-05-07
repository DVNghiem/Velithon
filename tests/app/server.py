
from velithon.application import Velithon
from velithon.endpoint import HTTPEndpoint
from velithon.routing import Route, Router
from velithon.responses import PlainTextResponse
from velithon.requests import Request
from velithon.params import Query, Path, Form, File, Body
from velithon.datastructures import UploadFile, FormData, Headers
from velithon.di import Provide, inject, FactoryProvider, ServiceContainer
from pydantic import BaseModel
import logging
from typing import Annotated

logger = logging.getLogger(__name__)

class User(BaseModel):
    id: int
    name: str
    age: int

class UserService:
    def get_user(self):
        return "Name: John Doe, Age: 30"
    
class Container(ServiceContainer):
    user_service_provider = FactoryProvider(UserService)

container = Container()

@inject
async def print_user(user: UserService = Provide(container.user_service_provider)):
    print(user.get_user())

class HelloWorld(HTTPEndpoint):
    
    @inject
    async def get(self, query: Annotated[User, Query()], name: Annotated[str, Path()], user: UserService = Provide[container.user_service_provider]):
        await print_user()
        print(query, name, user)
        return PlainTextResponse("Hello, World!")
    
    async def post(self, data: Annotated[User, Body()], request: Request, headers: Headers):
        print(data, headers, request)
        return PlainTextResponse("File uploaded successfully!")
    
router = Router()

@router.get("/test")
@inject
async def hello_world(request: Request, user: UserService = Provide[container.user_service_provider]):
    print(user.get_user())
    return PlainTextResponse("Hello, !")

router.add_route("/hello/{name}", HelloWorld)

app = Velithon(routes=router.routes)
app.register_container(container)
