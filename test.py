from velithon.application import Velithon
from velithon.endpoint import HTTPEndpoint
from velithon.routing import Route
from velithon.responses import PlainTextResponse

class TestMiddleware:
    def __init__(self, app, *args, **kwargs):
        self.app = app
        self.args = args
        self.kwargs = kwargs

    async def __call__(self, scope, protocol):
        # Middleware logic here
        print(scope.path)
        response = PlainTextResponse("Middleware response", status_code=200)
        await response(scope, protocol)
        return
        await self.app(scope, protocol)

class HelloWorld(HTTPEndpoint):
    async def get(self, request):
        return PlainTextResponse("Hello, World!")
    
route = Route("/hello", HelloWorld, methods=["GET"])
app = Velithon(routes=[route])
