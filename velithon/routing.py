import functools
import inspect
import re
from typing import Any, Awaitable, Callable, Dict, Sequence, Tuple, Type, TypeVar

from velithon._utils import is_async_callable, run_in_threadpool
from velithon._velithon import (
    Match,
    _RouteOptimizer,
    _RoutePatternMatcher,
    _RouterOptimizer,
    compile_path,
)
from velithon.cache import CacheConfig
from velithon.convertors import CONVERTOR_TYPES
from velithon.datastructures import Protocol, Scope
from velithon.middleware import Middleware
from velithon.openapi import swagger_generate
from velithon.params.dispatcher import dispatch
from velithon.requests import Request
from velithon.responses import PlainTextResponse, Response
from velithon.types import RSGIApp

T = TypeVar("T")
# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


def get_name(endpoint: Callable[..., Any]) -> str:
    return getattr(endpoint, "__name__", endpoint.__class__.__name__)


def request_response(
    func: Callable[[Request], Awaitable[Response] | Response],
) -> RSGIApp:
    """
    Takes a function or coroutine `func(request) -> response`,
    and returns an ARGI application.
    """
    f: Callable[[Request], Awaitable[Response]] = (
        func if is_async_callable(func) else functools.partial(run_in_threadpool, func)  # type:ignore
    )
    async def app(scope: Scope, protocol: Protocol) -> None:
        request = Request(scope, protocol)
        response = await dispatch(f, request)
        return await response(scope, protocol)
    return app


class BaseRoute:
    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        raise NotImplementedError()  # pragma: no cover

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        raise NotImplementedError()  # pragma: no cover
    
    async def openapi(self) -> tuple[Dict, Dict]:
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


class Route(BaseRoute):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Sequence[str] | None = None,
        name: str | None = None,
        middleware: Sequence[Middleware] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: Sequence[str] | None = None,
        include_in_schema: bool | None = True
    ) -> None:
        assert path.startswith("/"), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.description = description
        self.summary = summary
        self.tags = tags
        self.include_in_schema = include_in_schema

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            # Endpoint is function or method. Treat it as `func(request, ....) -> response`.
            self.app = request_response(endpoint)
            if methods is None:
                methods = ["GET"]
        else:
            # Endpoint is a class
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

        # Use Rust-optimized path compilation
        path_regex, self.path_format, self.param_convertors = compile_path(path, CONVERTOR_TYPES)
        self.path_regex = re.compile(path_regex)
        
        # Initialize Rust optimizer for enhanced performance
        methods_list = list(self.methods) if self.methods else None
        self._rust_optimizer = _RouteOptimizer(
            path_regex=path_regex,
            path_format=self.path_format,
            param_convertors=self.param_convertors,
            methods=methods_list,
            max_cache_size=CacheConfig.get_cache_size('route')
        )

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        if scope.proto == "http":
            # Use Rust-optimized matching first
            try:
                match_result, params = self._rust_optimizer.matches(scope.path, scope.method)
                if params:
                    setattr(scope, "_path_params", params)
                    return match_result, scope
                elif match_result != Match.NONE:
                    return match_result, scope
            except Exception:
                # Fall back to Python implementation if Rust optimization fails
                pass
            
            # Fallback to original Python logic
            route_path = scope.path
            
            # Check if we have this path in the path cache
            path_key = f"{route_path}:{scope.method}"
            path_cache = getattr(self, "_path_cache", {})
            
            cached_result = path_cache.get(path_key)
            if cached_result is not None:
                match_type, params = cached_result
                if params:
                    setattr(scope, "_path_params", params.copy())
                return match_type, scope
            
            # No cache hit, do the regex matching
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                setattr(scope, "_path_params", matched_params)
                
                # Determine match type
                if self.methods and scope.method not in self.methods:
                    match_type = Match.PARTIAL
                else:
                    match_type = Match.FULL
                
                # Cache the result - limit cache size to prevent memory leaks
                if not hasattr(self, "_path_cache"):
                    self._path_cache = {}
                if len(self._path_cache) >= 1000:  # Limit cache size
                    # Clear 20% of the cache when it gets too big
                    keys_to_remove = list(self._path_cache.keys())[:200]
                    for key in keys_to_remove:
                        self._path_cache.pop(key, None)
                
                self._path_cache[path_key] = (match_type, matched_params.copy() if matched_params else None)
                return match_type, scope
                
        return Match.NONE, {}

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        if self.methods and scope.method not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            response = PlainTextResponse(
                "Method Not Allowed", status_code=405, headers=headers
            )
            await response(scope, protocol)
        else:
            await self.app(scope, protocol)

    def openapi(self) -> Tuple[Dict, Dict]:
        """
        Return the OpenAPI schema for this route, handling both function-based and class-based endpoints.
        """
        paths = {}
        schemas = {}
        http_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

        if inspect.isfunction(self.endpoint) or inspect.iscoroutinefunction(self.endpoint):
            # Function-based endpoint
            if self.methods:
                for method in self.methods:
                    if method in http_methods:
                        path, schema = swagger_generate(self.endpoint, method.lower(), self.path)
                        if self.description:
                            path[self.path][method.lower()]["description"] = self.description
                        if self.tags:
                            path[self.path][method.lower()]["tags"] = list(self.tags)
                        if self.summary:
                            path[self.path][method.lower()]["summary"] = self.summary
                        if self.path not in paths:
                            paths[self.path] = {}
                        paths[self.path].update(path[self.path])
                        schemas.update(schema)
        else:
            # Class-based endpoint (HTTPEndpoint)
            for name, func in self.endpoint.__dict__.items():
                if name.upper() not in http_methods:
                    continue
                path, schema = swagger_generate(func, name.lower(), self.path)
                if self.description:
                    path[self.path][name.lower()]["description"] = self.description
                if self.tags:
                    path[self.path][name.lower()]["tags"] = list(self.tags)
                if self.summary:
                    path[self.path][name.lower()]["summary"] = self.summary
                if self.path not in paths:
                    paths[self.path] = {}
                paths[self.path].update(path[self.path])
                schemas.update(schema)

        return paths, schemas

    def __eq__(self, other: Any) -> bool:
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
        routes: Sequence[BaseRoute] | None = None,
        redirect_slashes: bool = True,
        default: RSGIApp | None = None,
        on_startup: Sequence[Callable[[], Any]] | None = None,
        on_shutdown: Sequence[Callable[[], Any]] | None = None,
        *,
        middleware: Sequence[Middleware] | None = None,
        route_class: Type[BaseRoute] = Route,
    ):
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
        self.middleware_stack = self.app
        self.route_class = route_class
        if middleware:
            for cls, args, kwargs in reversed(middleware):
                self.middleware_stack = cls(self.middleware_stack, *args, **kwargs)
        
        # Initialize Rust optimizations
        self._rust_optimizer = _RouterOptimizer(max_cache_size=CacheConfig.get_cache_size('route'))
        self._pattern_matcher = _RoutePatternMatcher()
        self._rebuild_rust_optimizations()

    def _rebuild_rust_optimizations(self):
        """Rebuild Rust optimizations for all routes"""
        try:
            self._pattern_matcher = _RoutePatternMatcher()
            
            for route in self.routes:
                if hasattr(route, 'path'):
                    # Add pattern to the pattern matcher
                    path_regex, path_format, param_convertors = compile_path(route.path, CONVERTOR_TYPES)
                    
                    # Check if this is an exact path (no parameters)
                    is_exact = "{" not in route.path
                    
                    self._pattern_matcher.add_pattern(
                        path_regex=path_regex,
                        path_format=path_format,
                        param_convertors=param_convertors,
                        is_exact_path=is_exact
                    )
        except Exception:
            # If Rust optimizations fail, continue without them
            pass

    async def not_found(self, scope: Scope, protocol: Protocol) -> None:
        response = PlainTextResponse("Not Found", status_code=404)
        await response(scope, protocol)

    async def app(self, scope: Scope, protocol: Protocol) -> None:
        assert scope.proto in ("http", "websocket")
        
        # Try Rust-optimized routing first
        if scope.proto == "http":
            try:
                cached_result = self._rust_optimizer.lookup_route(scope.path, scope.method)
                
                if cached_result is not None:
                    if cached_result == -1:  # Cached "not found"
                        await self.default(scope, protocol)
                        return
                    route = self.routes[cached_result]
                    # For cached results, we need to extract params again
                    match_result, params = route._rust_optimizer.matches(scope.path, scope.method)
                    if match_result == Match.FULL:
                        if params:
                            setattr(scope, "_path_params", params)
                        await route.handle(scope, protocol)
                        return
            except Exception:
                # Fall back to Python implementation if Rust optimization fails
                pass
        
        # Check if we have a route lookup table (fallback)
        if not hasattr(self, "_route_lookup"):
            self._route_lookup = {}
            self._exact_routes = {}
        
        # Try to match an exact path first for common routes
        route_key = f"{scope.path}:{scope.method}"
        exact_route = self._exact_routes.get(route_key)
        if exact_route is not None:
            await exact_route.handle(scope, protocol)
            return
        
        # Then check the route lookup cache
        cached_route = self._route_lookup.get(route_key)
        if cached_route is not None:
            if cached_route == "default":
                await self.default(scope, protocol)
            elif cached_route == "not_found":
                await self.default(scope, protocol)
            else:
                await cached_route.handle(scope, protocol)
            return
        
        # Fall back to checking all routes
        partial = None
        for route in self.routes:
            # Determine if any route matches the incoming scope,
            # and hand over to the matching route if found.
            match, updated_scope = route.matches(scope)
            if match == Match.FULL:
                # Cache this result for future lookups
                # Don't cache parameterized routes to avoid memory issues
                if not getattr(scope, "_path_params", None):
                    self._exact_routes[route_key] = route
                elif len(self._route_lookup) < 1000:  # Limit cache size
                    self._route_lookup[route_key] = route
                
                await route.handle(scope, protocol)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route

        # Cache the result for future lookups
        if len(self._route_lookup) < 1000:  # Limit cache size
            if partial is not None:
                self._route_lookup[route_key] = partial
            else:
                self._route_lookup[route_key] = "not_found"

        if partial is not None:
            await partial.handle(scope, protocol)
            return
            
        await self.default(scope, protocol)

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """
        The main entry point to the Router class.
        """
        await self.middleware_stack(scope, protocol)

    def add_route(
        self,
        path: str,
        endpoint: Callable[[Request], Awaitable[Response] | Response],
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
        summary: str | None = None,
        description: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:  # pragma: no cover
        route = Route(
            path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            summary=summary,
            description=description,
            tags=tags,
        )
        self.routes.append(route)
        self._rebuild_rust_optimizations()

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Sequence[str] | None = None,
        name: str | None = None,
        middleware: Sequence[Middleware] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: Sequence[str] | None = None,
        include_in_schema: bool | None = True,
        route_class_override: Type[BaseRoute] | None = None,
    ) -> None:
        route_class = route_class_override or self.route_class
        route = route_class(
            path,
            endpoint=endpoint,
            description=description,
            summary=summary,
            methods=methods,
            name=name,
            middleware=middleware,
            tags=tags,
            include_in_schema=include_in_schema,
        )
        self.routes.append(route)
        self._rebuild_rust_optimizations()

    def api_route(
        self,
        path: str,
        *,
        methods: Sequence[str] | None = None,
        name: str | None = None,
        middleware: Sequence[Middleware] | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: Sequence[str] | None = None,
        include_in_schema: bool | None = True,
        route_class_override: Type[BaseRoute] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_api_route(
                path,
                func,
                route_class_override=route_class_override,
                tags=tags,
                description=description,
                summary=summary,
                methods=methods,
                name=name,
                middleware=middleware,
                include_in_schema=include_in_schema,
            )
            return func

        return decorator
    
    def _create_http_method_decorator(
        self,
        method: str,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Generic factory method for creating HTTP method decorators.
        Eliminates code duplication across get, post, put, delete, patch, options methods.
        """
        return self.api_route(
            path=path,
            tags=tags,
            summary=summary,
            description=description,
            methods=[method.upper()],
            name=name,
            include_in_schema=include_in_schema,
        )

    def get(
        self,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Add a *path operation* using an HTTP GET operation.

        ## Example
        ```python
        router = Router()

        @router.get("/items/")
        def read_items():
            return [{"name": "Empanada"}, {"name": "Arepa"}]
        ```
        """
        return self._create_http_method_decorator(
            "get",
            path=path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
        )
    
    def post(
        self,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Add a *path operation* using an HTTP POST operation.

        ## Example
        ```python
        router = Router()

        @router.post("/items/")
        def create_item():
            return [{"name": "Empanada"}, {"name": "Arepa"}]
        ```
        """
        return self._create_http_method_decorator(
            "POST", path, tags=tags, summary=summary, description=description,
            name=name, include_in_schema=include_in_schema
        )
    
    def put(
        self,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Add a *path operation* using an HTTP PUT operation.

        ## Example
        ```python
        router = Router()

        @router.put("/items/")
        def update_item():
            return [{"name": "Empanada"}, {"name": "Arepa"}]
        ```
        """
        return self._create_http_method_decorator(
            "PUT", path, tags=tags, summary=summary, description=description,
            name=name, include_in_schema=include_in_schema
        )
    
    def delete(
        self,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Add a *path operation* using an HTTP DELETE operation.

        ## Example
        ```python
        router = Router()

        @router.delete("/items/")
        def delete_item():
            return [{"name": "Empanada"}, {"name": "Arepa"}]
        ```
        """
        return self._create_http_method_decorator(
            "DELETE", path, tags=tags, summary=summary, description=description,
            name=name, include_in_schema=include_in_schema
        )
    
    def patch(
        self,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Add a *path operation* using an HTTP PATCH operation.
        """
        return self._create_http_method_decorator(
            "PATCH", path, tags=tags, summary=summary, description=description,
            name=name, include_in_schema=include_in_schema
        )
    
    def options(
        self,
        path: str,
        *,
        tags: Sequence[str] | None = None,
        summary: str | None = None,
        description: str | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Add a *path operation* using an HTTP OPTIONS operation.
        """
        return self._create_http_method_decorator(
            "OPTIONS", path, tags=tags, summary=summary, description=description,
            name=name, include_in_schema=include_in_schema
        )
    
    def add_websocket_route(
        self,
        path: str,
        endpoint: Any,
        name: str | None = None,
    ) -> None:
        """Add a WebSocket route to the router."""
        from velithon.websocket import WebSocketRoute
        route = WebSocketRoute(path, endpoint, name)
        self.routes.append(route)
        self._rebuild_rust_optimizations()

    def websocket(
        self,
        path: str,
        *,
        name: str | None = None,
    ) -> Callable[[Any], Any]:
        """
        Decorator to add a WebSocket route.
        
        Args:
            path: The WebSocket path pattern
            name: Optional name for the route
            
        Returns:
            Decorator function
        """
        def decorator(func: Any) -> Any:
            self.add_websocket_route(path, func, name)
            return func
        return decorator

