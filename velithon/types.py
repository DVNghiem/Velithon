import typing

if typing.TYPE_CHECKING:
    from velithon.requests import Request
    from velithon.responses import Response
    
from velithon.datastructures import Protocol, Scope

AppType = typing.TypeVar("AppType")

RSGIApp = typing.Callable[[Scope, Protocol], typing.Awaitable[None]]

StatelessLifespan = typing.Callable[[AppType], typing.AsyncContextManager[None]]
StatefulLifespan = typing.Callable[
    [AppType], typing.AsyncContextManager[typing.Mapping[str, typing.Any]]
]
Lifespan = typing.Union[StatelessLifespan[AppType], StatefulLifespan[AppType]]

HTTPExceptionHandler = typing.Callable[
    ["Request", Exception], "Response | typing.Awaitable[Response]"
]
ExceptionHandler = typing.Union[HTTPExceptionHandler]

