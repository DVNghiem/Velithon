import logging
from typing import Annotated

from pydantic import BaseModel, Field

from velithon.datastructures import Headers
from velithon.endpoint import HTTPEndpoint
from velithon.params import Body, Path, Query
from velithon.requests import Request
from velithon.responses import PlainTextResponse

logger = logging.getLogger(__name__)

class User(BaseModel):
    name: str = Field(..., description="The name of the user")
    age: int = Field(..., description="The age of the user")

class InjectQueryEndpoint(HTTPEndpoint):
    
    async def get(self, query: Annotated[User, Query()]):
        return PlainTextResponse("Hello, World!")
    
class InjectQueryItemEndpoint(HTTPEndpoint):
    
    async def get(self, name: Annotated[str, Query()]):
        return PlainTextResponse("Hello, World!")
    
class InjectPathEndpoint(HTTPEndpoint):
    async def get(self, name: Annotated[str, Path()]):
        return PlainTextResponse("Hello, World!")
    
class InjectBodyEndpoint(HTTPEndpoint):
    async def post(self, body: Annotated[User, Body()]):
        return PlainTextResponse("Hello, World!")
    
class InjectHeadersEndpoint(HTTPEndpoint):
    async def get(self, headers: Headers):
        return PlainTextResponse("Hello, World!")
    
class InjectRequestEndpoint(HTTPEndpoint):
    async def get(self, request: Request):
        return PlainTextResponse("Hello, World!")
    
