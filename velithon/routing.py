import re
import typing
from enum import Enum

from velithon.middleware import Middleware
from velithon.responses import PlainTextResponse
from velithon.types import Protocol, RSGIApp, Scope
from velithon.convertors import CONVERTOR_TYPES, Convertor


T = typing.TypeVar("T")
# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")

class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class BaseRoute:
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        raise NotImplementedError()  # pragma: no cover

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """
        A route may be used in isolation as a stand-alone ASGI app.
        This is a somewhat contrived case, as they'll almost always be used
        within a Router, but could be useful for some tooling and minimal apps.
        """
        match, child_scope = self.matches(scope)
        if match == Match.NONE:
            if scope["type"] == "http":
                response = PlainTextResponse("Not Found", status_code=404)
                await response(scope, protocol)
            elif scope["type"] == "websocket":  # pragma: no branch
                # websocket_close = WebSocketClose()
                # await websocket_close(scope, protocol)
                pass  # pragma: no cover
            return

        scope.update(child_scope)
        await self.handle(scope, protocol)

def get_name(endpoint: typing.Callable[..., typing.Any]) -> str:
    return getattr(endpoint, "__name__", endpoint.__class__.__name__)

    
def compile_path(
    path: str,
) -> tuple[typing.Pattern[str], str, dict[str, Convertor[typing.Any]]]:
    """
    Given a path string, like: "/{username:str}",
    or a host string, like: "{subdomain}.mydomain.org", return a three-tuple
    of (regex, format, {param_name:convertor}).

    regex:      "/(?P<username>[^/]+)"
    format:     "/{username}"
    convertors: {"username": StringConvertor()}
    """
    is_host = not path.startswith("/")

    path_regex = "^"
    path_format = ""
    duplicated_params = set()

    idx = 0
    param_convertors = {}
    for match in PARAM_REGEX.finditer(path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")
        assert convertor_type in CONVERTOR_TYPES, f"Unknown path convertor '{convertor_type}'"
        convertor = CONVERTOR_TYPES[convertor_type]

        path_regex += re.escape(path[idx : match.start()])
        path_regex += f"(?P<{param_name}>{convertor.regex})"

        path_format += path[idx : match.start()]
        path_format += "{%s}" % param_name

        if param_name in param_convertors:
            duplicated_params.add(param_name)

        param_convertors[param_name] = convertor

        idx = match.end()

    if duplicated_params:
        names = ", ".join(sorted(duplicated_params))
        ending = "s" if len(duplicated_params) > 1 else ""
        raise ValueError(f"Duplicated param name{ending} {names} at path {path}")

    if is_host:
        # Align with `Host.matches()` behavior, which ignores port.
        hostname = path[idx:].split(":")[0]
        path_regex += re.escape(hostname) + "$"
    else:
        path_regex += re.escape(path[idx:]) + "$"

    path_format += path[idx:]

    return re.compile(path_regex), path_format, param_convertors

def request_response():
    pass

class Route(BaseRoute):
    def __init__(
        self,
        path: str,
        endpoint: typing.Callable[..., typing.Any],
        *,
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
        middleware: typing.Sequence[Middleware] | None = None,
    ) -> None:
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.include_in_schema = include_in_schema

        self.app = endpoint

        if middleware is not None:
            for cls, args, kwargs in reversed(middleware):
                self.app = cls(self.app, *args, **kwargs)

        if methods is None:
            self.methods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        if scope.proto == "http":
            route_path = scope.path
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                if self.methods and scope.method not in self.methods:
                    return Match.PARTIAL
                else:
                    return Match.FULL
        return Match.NONE, {}

    async def handle(self,  scope: Scope, protocol: Protocol) -> None:
        if self.methods and scope.method not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            response = PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
            await response(scope, protocol)
        else:
            await self.app(scope, protocol)

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, Route)
            and self.path == other.path
            and self.endpoint == other.endpoint
            and self.methods == other.methods
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        methods = sorted(self.methods or [])
        path, name = self.path, self.name
        return f"{class_name}(path={path!r}, name={name!r}, methods={methods!r})"

class Router:
    def __init__(
        self,
        routes: typing.Sequence[BaseRoute] | None = None,
        redirect_slashes: bool = True,
        default: RSGIApp | None = None,
        on_startup: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        on_shutdown: typing.Sequence[typing.Callable[[], typing.Any]] | None = None,
        # the generic to Lifespan[AppType] is the type of the top level application
        # which the router cannot know statically, so we use typing.Any
        *,
        middleware: typing.Sequence[Middleware] | None = None,
    ):
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
        self.middleware_stack = self.app
        if middleware:
            for cls, args, kwargs in reversed(middleware):
                self.middleware_stack = cls(self.middleware_stack, *args, **kwargs)

    async def not_found(self, scope: Scope, protocol: Protocol) -> None:
        response = PlainTextResponse("Not Found", status_code=404)
        await response(scope, protocol)

    async def app(self, scope: Scope, protocol: Protocol) -> None:
        assert scope.proto in ("http", "websocket")
        partial = None
        for route in self.routes:
            # Determine if any route matches the incoming scope,
            # and hand over to the matching route if found.
            match = route.matches(scope)
            if match == Match.FULL:
                await route.handle(scope, protocol)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route

        if partial is not None:
            await partial.handle(scope, protocol)
            return
        await self.default(scope, protocol)

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """
        The main entry point to the Router class.
        """
        await self.middleware_stack(scope, protocol)
