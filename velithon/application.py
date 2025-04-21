import typing
from .routing import Router
from .requests import Request
from velithon.types import ASGIApp, Lifespan, Send, Scope, Receive
from velithon.middleware import Middleware
from velithon.routing import BaseRoute

AppType = typing.TypeVar("AppType", bound="Velithon")
class Velithon:
    def __init__(self, debug: bool = False,
        routes: typing.Sequence[BaseRoute] | None = None,
        middleware: typing.Sequence[Middleware] | None = None,
        # exception_handlers: typing.Mapping[typing.Any, ExceptionHandler] | None = None,
        on_startup: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        on_shutdown: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        lifespan: Lifespan[AppType] | None = None,):
        self.router = Router(routes, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan)
        # self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: ASGIApp | None = None


    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        request = Request(scope)
        response = await self.router.handle(request)
        
        await send({
            "type": "http.response.start",
            "status": response.status,
            "headers": [(k.encode(), v.encode()) for k, v in response.headers.items()]
        })
        await send({
            "type": "http.response.body",
            "body": response.body
        })