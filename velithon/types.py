import typing
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    from velithon.requests import Request
    from velithon.responses import Response

AppType = typing.TypeVar("AppType")


@dataclass
class Scope:
    proto: typing.Literal["http", "websocket"]
    rsgi_version: str
    http_version: str
    server: str
    client: str
    scheme: str
    method: str
    path: str
    query_string: str
    headers: typing.MutableMapping[str, str]
    authority: typing.Optional[str]


@dataclass
class Protocol:
    async def __call__(self, *args, **kwds) -> bytes: ...
    async def __aiter__(self) -> typing.AsyncIterator[bytes]: ...
    async def client_disconnect(self) -> None: ...
    def response_empty(self, status: int, headers: typing.Tuple[str, str]) -> None: ...
    def response_str(
        self, status: int, headers: typing.Tuple[str, str], body: str
    ) -> None: ...
    def response_bytes(
        self, status: int, headers: typing.Tuple[str, str], body: bytes
    ) -> None: ...
    def response_file(
        self, status: int, headers: typing.Tuple[str, str], file: typing.Any
    ) -> None: ...
    def response_stream(
        self, status: int, headers: typing.Tuple[str, str]
    ) -> typing.Any: ...


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

HTTP_METHODS = (
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "OPTIONS",
    "PATCH",
    "TRACE",
    "CONNECT",
)
