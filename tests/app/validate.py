import logging

from pydantic import BaseModel, Field

from velithon.endpoint import HTTPEndpoint
from velithon.responses import PlainTextResponse

logger = logging.getLogger(__name__)

class TestModel(BaseModel):
    id: int = Field(..., description="The ID of the item")
    name: str = Field(..., description="The name of the item")
    description: str = Field(None, description="The description of the item")


class TestValidate(HTTPEndpoint):
    async def get(self, query: TestModel):
        return PlainTextResponse("success")
    
    async def post(self, body: TestModel):
        return PlainTextResponse("success")
