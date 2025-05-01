import typing
from velithon.routing import Router
from velithon.types import RSGIApp, Scope, Protocol
from velithon.middleware import Middleware
from velithon.routing import BaseRoute

AppType = typing.TypeVar("AppType", bound="Velithon")

class Velithon:
    def __init__(self, debug: bool = False,
        routes: typing.Sequence[BaseRoute] | None = None,
        middleware: typing.Sequence[Middleware] | None = None,
        on_startup: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        on_shutdown: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
    ):
        self.router = Router(routes, on_startup=on_startup, on_shutdown=on_shutdown)
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: RSGIApp | None = None

    def build_middleware_stack(self) -> RSGIApp:
        middleware = self.user_middleware
        app = self.router
        for cls, args, kwargs in reversed(middleware):
            app = cls(app, *args, **kwargs)
        return app

    async def __call__(self, scope: Scope, protocol: Protocol):
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, protocol)

    