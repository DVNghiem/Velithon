import typing
from enum import Enum

from velithon.middleware import Middleware
from velithon.types import ASGIApp, Lifespan, Receive, Scope, Send

from .requests import Request
from .responses import PlainTextResponse, Response
from velithon.exceptions import HTTPException


class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class BaseRoute:
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        raise NotImplementedError()  # pragma: no cover

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        A route may be used in isolation as a stand-alone ASGI app.
        This is a somewhat contrived case, as they'll almost always be used
        within a Router, but could be useful for some tooling and minimal apps.
        """
        match, child_scope = self.matches(scope)
        if match == Match.NONE:
            if scope["type"] == "http":
                response = PlainTextResponse("Not Found", status_code=404)
                await response(scope, receive, send)
            elif scope["type"] == "websocket":  # pragma: no branch
                # websocket_close = WebSocketClose()
                # await websocket_close(scope, receive, send)
                pass  # pragma: no cover
            return

        scope.update(child_scope)
        await self.handle(scope, receive, send)


class Router:
    def __init__(
        self,
        routes: typing.Sequence[BaseRoute] | None = None,
        default: ASGIApp | None = None,
        on_startup: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        on_shutdown: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        # the generic to Lifespan[AppType] is the type of the top level application
        # which the router cannot know statically, so we use typing.Any
        lifespan: Lifespan[typing.Any] | None = None,
        *,
        middleware: typing.Sequence[Middleware] | None = None,
    ):
        self.routes = [] if routes is None else list(routes)
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)

    async def not_found(self, scope: Scope, receive: Receive, send: Send) -> None:
        # if scope["type"] == "websocket":
        #     websocket_close = WebSocketClose()
        #     await websocket_close(scope, receive, send)
        #     return

        # If we're running inside a starlette application then raise an
        # exception, so that the configurable exception handler can deal with
        # returning the response. For plain ASGI apps, just return the response.
        if "app" in scope:
            raise HTTPException(status_code=404)
        else:
            response = PlainTextResponse("Not Found", status_code=404)
        await response(scope, receive, send)

    async def handle(self, request: Request) -> Response:
        key = (request.path, request.method)
        handler = self.routes.get(key)
        if handler:
            return await handler(request)
        return Response("Not Found", status=404)
