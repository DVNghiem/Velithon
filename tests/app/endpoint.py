
import logging

from velithon.endpoint import HTTPEndpoint
from velithon.requests import Request
from velithon.responses import PlainTextResponse

logger = logging.getLogger(__name__)

class TestEndpoint(HTTPEndpoint):
    async def get(self, request: Request):
        return PlainTextResponse("success")
    async def post(self, request: Request):
        return PlainTextResponse("success")
    async def put(self, request: Request):
        return PlainTextResponse("success")
    async def delete(self, request: Request):
        return PlainTextResponse("success")

