"""Routing system for Velithon framework.

This module provides routing functionality including Route classes, Router,
and route matching capabilities for HTTP requests and WebSocket connections.
"""

import functools
import inspect
import re
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar

from velithon._utils import is_async_callable, run_in_threadpool
from velithon._velithon import (
    Match,
    _RouteOptimizer,
    _UnifiedRouteOptimizer,
    compile_path,
)
from velithon.cache import CacheConfig
from velithon.convertors import CONVERTOR_TYPES
from velithon.ctx import get_or_create_request, has_request_context
from velithon.datastructures import Protocol, Scope
from velithon.middleware import Middleware
from velithon.openapi import swagger_generate
from velithon.params.dispatcher import dispatch
from velithon.requests import Request
from velithon.responses import PlainTextResponse, Response

T = TypeVar('T')
# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile('{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}')


def get_name(endpoint: Callable[..., Any]) -> str:
    """Return the name of the endpoint function or class.

    Args:
        endpoint: The endpoint callable (function or class).

    Returns:
        str: The name of the endpoint.

    """
    return getattr(endpoint, '__name__', endpoint.__class__.__name__)


def request_response(
    func: Callable[[Request], Awaitable[Response] | Response],
) -> Callable[[Scope, Protocol], Awaitable[None]]:
    """Take a function or coroutine `func(request) -> response`.

    and return an ARGI application.
    """
    f: Callable[[Request], Awaitable[Response]] = (
        func if is_async_callable(func) else functools.partial(run_in_threadpool, func)  # type:ignore
    )

    async def app(scope: Scope, protocol: Protocol) -> None:
        # Try to get request from context first (singleton pattern)
        if has_request_context():
            request = get_or_create_request(scope, protocol)
        else:
            # Create new request if no context exists
            request = Request(scope, protocol)
        response = await dispatch(f, request)
        return await response(scope, protocol)

    return app


class BaseRoute:
    """Base class for defining routes in the Velithon framework.

    This class provides the interface for route matching, handling requests,
    and generating OpenAPI documentation. Subclasses should implement the
    required methods for specific route types.
    """

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Determine if the given scope matches this route.

        Args:
            scope (Scope): The request scope containing path and method information.

        Returns:
            tuple[Match, Scope]: A tuple containing the match type and the updated scope with path parameters.

        """  # noqa: E501
        raise NotImplementedError()  # pragma: no cover

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        """Handle an incoming request for this route."""
        raise NotImplementedError()  # pragma: no cover

    async def openapi(self) -> tuple[dict, dict]:
        """Return the OpenAPI schema for this route."""
        raise NotImplementedError()  # pragma: no cover

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Use a route in isolation as a stand-alone RSGI app.

        This is a somewhat contrived case, as they'll almost always be used
        within a Router, but could be useful for some tooling and minimal apps.
        """
        match, child_scope = self.matches(scope)
        if match == Match.NONE:
            if scope['type'] == 'http':
                response = PlainTextResponse('Not Found', status_code=404)
                await response(scope, protocol)
            elif scope['type'] == 'websocket':  # pragma: no branch
                # websocket_close = WebSocketClose()
                # await websocket_close(scope, protocol)
                pass  # pragma: no cover
            return

        scope.update(child_scope)
        await self.handle(scope, protocol)


class Route(BaseRoute):
    """
    Route class for Velithon framework.

    Represents an HTTP route, including path pattern, endpoint handler, allowed methods,
    middleware, and OpenAPI documentation metadata.
    Utilizes Rust-optimized path matching for high performance.

    Attributes:
        path (str): The route path pattern.
        endpoint (Callable[..., Any]): The endpoint function or class.
        name (str): The name of the route.
        methods (set[str] | None): Allowed HTTP methods.
        middleware (Sequence[Middleware] | None): Middleware stack for this route.
        summary (str | None): Summary for documentation.
        description (str | None): Description for documentation.
        tags (Sequence[str] | None): Tags for grouping routes.
        include_in_schema (bool | None): Whether to include in OpenAPI schema.
        response_model (type | None): Response model for documentation.

    """

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
        include_in_schema: bool | None = True,
        response_model: type | None = None,
    ) -> None:
        """
        Initialize a Route instance.

        Args:
            path (str): The route path pattern.
            endpoint (Callable[..., Any]): The endpoint function or class.
            methods (Sequence[str] | None): Allowed HTTP methods.
            name (str | None): Name of the route.
            middleware (Sequence[Middleware] | None): Middleware stack for this route.
            summary (str | None): Summary for documentation.
            description (str | None): Description for documentation.
            tags (Sequence[str] | None): Tags for grouping routes.
            include_in_schema (bool | None): Whether to include in OpenAPI schema.
            response_model (type | None): Response model for documentation.

        """
        assert path.startswith('/'), "Routed paths must start with '/'"
        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.description = description
        self.summary = summary
        self.tags = tags
        self.include_in_schema = include_in_schema
        self.response_model = response_model

        endpoint_handler = endpoint
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            # Endpoint is function or method. Treat it as `func(request, ....) -> response`.  # noqa: E501
            self.app = request_response(endpoint)
            if methods is None:
                methods = ['GET']
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
            if 'GET' in self.methods:
                self.methods.add('HEAD')

        # Use Rust-optimized path compilation
        path_regex, self.path_format, self.param_convertors = compile_path(
            path, CONVERTOR_TYPES
        )
        self.path_regex = re.compile(path_regex)

        # Initialize Rust optimizer for enhanced performance
        methods_list = list(self.methods) if self.methods else None
        self._rust_optimizer = _RouteOptimizer(
            path_regex=path_regex,
            path_format=self.path_format,
            param_convertors=self.param_convertors,
            methods=methods_list,
            max_cache_size=CacheConfig.get_cache_size('route'),
        )

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """
        Determine if the given request scope matches this route.

        Args:
            scope (Scope): The request scope containing path and method information.

        Returns:
            tuple[Match, Scope]: A tuple containing the match type 
                and the updated scope with path parameters.

        """
        if scope.proto == 'http':
            # Use Rust-optimized matching for individual route checks
            try:
                match_result, params = self._rust_optimizer.matches(
                    scope.path, scope.method
                )
                if params:
                    scope._path_params = dict(params.items())
                else:
                    scope._path_params = {}
                return match_result, scope
            except Exception:
                # Fall back to Python implementation if Rust fails
                pass

            # Simplified Python fallback without redundant caching
            route_path = scope.path
            match = self.path_regex.match(route_path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                scope._path_params = matched_params

                # Determine match type
                if self.methods and scope.method not in self.methods:
                    return Match.PARTIAL, scope
                else:
                    return Match.FULL, scope

        return Match.NONE, {}

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        """
        Handle an incoming request for this route.

        Args:
            scope (Scope): The request scope containing path and method information.
            protocol (Protocol): The protocol instance for sending responses.

        Returns:
            None

        """
        if self.methods and scope.method not in self.methods:
            headers = {'Allow': ', '.join(self.methods)}
            response = PlainTextResponse(
                'Method Not Allowed', status_code=405, headers=headers
            )
            await response(scope, protocol)
        else:
            await self.app(scope, protocol)

    def openapi(self) -> tuple[dict, dict]:
        """
        Return the OpenAPI schema for this route, handling both function-based
        and class-based endpoints.

        """  # noqa: D205
        paths = {}
        schemas = {}
        http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']

        if inspect.isfunction(self.endpoint) or inspect.iscoroutinefunction(
            self.endpoint
        ):
            # Function-based endpoint
            if self.methods:
                for method in self.methods:
                    if method in http_methods:
                        path, schema = swagger_generate(
                            self.endpoint,
                            method.lower(),
                            self.path,
                            self.response_model,
                        )

                        if self.description:
                            path[self.path][method.lower()]['description'] = (
                                self.description
                            )
                        if self.tags:
                            path[self.path][method.lower()]['tags'] = list(self.tags)
                        if self.summary:
                            path[self.path][method.lower()]['summary'] = self.summary
                        if self.path not in paths:
                            paths[self.path] = {}
                        paths[self.path].update(path[self.path])
                        schemas.update(schema)
        else:
            # Class-based endpoint (HTTPEndpoint)
            for name, func in self.endpoint.__dict__.items():
                if name.upper() not in http_methods:
                    continue

                path, schema = swagger_generate(
                    func, name.lower(), self.path, self.response_model
                )

                if self.description:
                    path[self.path][name.lower()]['description'] = self.description
                if self.tags:
                    path[self.path][name.lower()]['tags'] = list(self.tags)
                if self.summary:
                    path[self.path][name.lower()]['summary'] = self.summary
                if self.path not in paths:
                    paths[self.path] = {}
                paths[self.path].update(path[self.path])
                schemas.update(schema)

        return paths, schemas

    def __eq__(self, other: Any) -> bool:
        """Check equality based on path, endpoint, and methods."""
        return (
            isinstance(other, Route)
            and self.path == other.path
            and self.endpoint == other.endpoint
            and self.methods == other.methods
        )

    def __repr__(self) -> str:
        """Return a string representation of the Route instance."""
        class_name = self.__class__.__name__
        methods = sorted(self.methods or [])
        path, name = self.path, self.name
        return f'{class_name}(path={path!r}, name={name!r}, methods={methods!r})'


class Router:
    """
    Router class for Velithon framework.

    The Router manages a collection of routes, including HTTP and WebSocket routes,
    and provides efficient request dispatching using Rust-optimized matching.
    It supports middleware, route grouping, and integration with sub-routers.

    Attributes:
        path (str): Path prefix for all routes in this router.
        redirect_slashes (bool): Whether to redirect requests with trailing slashes.
        default (RSGI app): Default handler for unmatched routes.
        on_startup (list): Startup event handlers.
        on_shutdown (list): Shutdown event handlers.
        middleware_stack (Callable): Middleware stack for request processing.
        route_class (type): Route class used for HTTP routes.
        routes (list): List of registered routes.

    """

    def __init__(
        self,
        routes: Sequence[BaseRoute] | None = None,
        *,
        path: str = '',
        redirect_slashes: bool = True,
        default: Callable[[Scope, Protocol], Awaitable[None]] | None = None,
        on_startup: Sequence[Callable[[], Any]] | None = None,
        on_shutdown: Sequence[Callable[[], Any]] | None = None,
        middleware: Sequence[Middleware] | None = None,
        route_class: type[BaseRoute] = Route,
    ):
        """
        Initialize a Router instance.

        Args:
            routes (Sequence[BaseRoute] | None): Initial list of routes to register.
            path (str): Path prefix for all routes in this router.
            redirect_slashes (bool): Whether to redirect requests with trailing slashes.
            default (Callable[[Scope, Protocol], Awaitable[None]] | None): Default handler for unmatched routes.
            on_startup (Sequence[Callable[[], Any]] | None): Startup event handlers.
            on_shutdown (Sequence[Callable[[], Any]] | None): Shutdown event handlers.
            middleware (Sequence[Middleware] | None): Middleware stack for request processing.
            route_class (type[BaseRoute]): Route class used for HTTP routes.

        """  # noqa: E501
        self.path = path.rstrip('/') if path else ''
        self.redirect_slashes = redirect_slashes
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown)
        self.middleware_stack = self.app
        self.route_class = route_class
        if middleware:
            for cls, args, kwargs in reversed(middleware):
                self.middleware_stack = cls(self.middleware_stack, *args, **kwargs)

        # Handle existing routes with path prefix
        self.routes = []
        if routes is not None:
            for route in routes:
                if hasattr(route, 'path') and hasattr(route, 'endpoint'):
                    # Check if this is a WebSocket route
                    if (
                        hasattr(route, 'matches')
                        and hasattr(route, 'handle')
                        and not hasattr(route, 'methods')
                    ):
                        # This is likely a WebSocket route - create with prefixed path
                        from velithon.websocket import WebSocketRoute

                        if isinstance(route, WebSocketRoute):
                            full_path = self._get_full_path(route.path)
                            new_route = WebSocketRoute(
                                full_path,
                                endpoint=route.endpoint,
                                name=getattr(route, 'name', None),
                            )
                            self.routes.append(new_route)
                        else:
                            # Unknown route type, just copy as-is
                            self.routes.append(route)
                    else:
                        # This is a regular HTTP route - create with prefixed path
                        full_path = self._get_full_path(route.path)
                        new_route = self.route_class(
                            full_path,
                            endpoint=route.endpoint,
                            methods=getattr(route, 'methods', None),
                            name=getattr(route, 'name', None),
                            middleware=getattr(route, 'middleware', None),
                            summary=getattr(route, 'summary', None),
                            description=getattr(route, 'description', None),
                            tags=getattr(route, 'tags', None),
                            include_in_schema=getattr(route, 'include_in_schema', True),
                            response_model=getattr(route, 'response_model', None),
                        )
                        self.routes.append(new_route)
                else:
                    # Handle other route types - just copy as-is
                    self.routes.append(route)

        # Initialize unified Rust routing optimization
        cache_size = CacheConfig.get_cache_size('route') * 2  # Larger unified cache
        self._unified_optimizer = _UnifiedRouteOptimizer(max_cache_size=cache_size)
        self._rebuild_rust_optimizations()

    def _get_full_path(self, path: str) -> str:
        """Get the full path by combining router path prefix with route path."""
        if not self.path:
            return path

        # Ensure path starts with '/'
        if not path.startswith('/'):
            path = '/' + path

        # Combine paths
        full_path = self.path + path

        # Normalize double slashes
        while '//' in full_path:
            full_path = full_path.replace('//', '/')

        return full_path

    def _rebuild_rust_optimizations(self):
        """Rebuild unified Rust optimizations for all routes."""
        try:
            # Clear previous optimizations
            self._unified_optimizer.clear_all()

            for route_index, route in enumerate(self.routes):
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    methods = list(route.methods) if route.methods else ['GET']

                    # Check if this is an exact path (no parameters)
                    if '{' not in route.path:
                        # Add as exact route for fastest matching
                        self._unified_optimizer.add_exact_route(
                            route.path, route_index, methods
                        )
                    else:
                        # Add as regex route for parameterized paths
                        path_regex, path_format, param_convertors = compile_path(
                            route.path, CONVERTOR_TYPES
                        )
                        self._unified_optimizer.add_regex_route(
                            path_regex, route_index, methods, param_convertors
                        )
        except Exception:
            # If Rust optimizations fail, continue without them
            pass

    async def not_found(self, scope: Scope, protocol: Protocol) -> None:
        """
        Send a 404 Not Found response for unmatched routes.

        Args:
            scope (Scope): The request scope containing path and method information.
            protocol (Protocol): The protocol instance for sending responses.

        """
        response = PlainTextResponse('Not Found', status_code=404)
        await response(scope, protocol)

    async def app(self, scope: Scope, protocol: Protocol) -> None:
        """Handle incoming requests with optimized unified routing.

        This method uses the unified Rust optimizer for maximum performance,
        eliminating multiple cache layers and minimizing Python/Rust boundaries.

        Args:
            scope (Scope): The request scope containing path and method information.
            protocol (Protocol): The protocol instance for sending responses.

        """
        assert scope.proto in ('http', 'websocket')

        # Use unified Rust optimizer for HTTP requests
        if scope.proto == 'http':
            try:
                route_index, match_type, params = self._unified_optimizer.match_route(
                    scope.path, scope.method
                )

                if route_index >= 0:  # Route found
                    route = self.routes[route_index]
                    if params:
                        scope._path_params = (
                            dict(params.items()) if hasattr(params, 'items') else {}
                        )
                    else:
                        scope._path_params = {}

                    if match_type == Match.FULL:
                        await route.handle(scope, protocol)
                        return
                    elif match_type == Match.PARTIAL:
                        # Method not allowed
                        await route.handle(scope, protocol)
                        return

                # If route_index is -1, no route found
                await self.default(scope, protocol)
                return

            except Exception:
                # Fall back to Python implementation if Rust optimization fails
                pass

        # Fallback implementation for WebSocket or when Rust optimization fails
        partial = None
        for route in self.routes:
            match, updated_scope = route.matches(scope)
            if match == Match.FULL:
                await route.handle(updated_scope, protocol)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route

        if partial is not None:
            await partial.handle(scope, protocol)
            return

        await self.default(scope, protocol)

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Call the main entry point to the Router class."""
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
        """
        Add a new HTTP route to the router.

        Args:
            path (str): The route path pattern.
            endpoint (Callable): The endpoint function or coroutine to handle requests.
            methods (list[str] | None): List of HTTP methods allowed for this route.
            name (str | None): Optional name for the route.
            include_in_schema (bool): Whether to include this route in the OpenAPI schema.
            summary (str | None): Optional summary for documentation.
            description (str | None): Optional description for documentation.
            tags (Sequence[str] | None): Optional tags for grouping routes.

        """  # noqa: E501
        full_path = self._get_full_path(path)
        route = Route(
            full_path,
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
        route_class_override: type[BaseRoute] | None = None,
        response_model: type | None = None,
    ) -> None:
        """
        Add an API route to the router.

        This method registers a new route with the specified path, endpoint, HTTP methods,
        and additional metadata such as middleware, summary, description, tags, and response model.

        Args:
            path (str): The route path pattern.
            endpoint (Callable[..., Any]): The endpoint function or class to handle requests.
            methods (Sequence[str] | None): List of HTTP methods allowed for this route.
            name (str | None): Optional name for the route.
            middleware (Sequence[Middleware] | None): Optional middleware stack for this route.
            summary (str | None): Optional summary for documentation.
            description (str | None): Optional description for documentation.
            tags (Sequence[str] | None): Optional tags for grouping routes.
            include_in_schema (bool | None): Whether to include this route in the OpenAPI schema.
            route_class_override (type[BaseRoute] | None): Optional custom route class to use.
            response_model (type | None): Optional response model for documentation.

        """  # noqa: E501
        route_class = route_class_override or self.route_class
        full_path = self._get_full_path(path)
        route = route_class(
            full_path,
            endpoint=endpoint,
            description=description,
            summary=summary,
            methods=methods,
            name=name,
            middleware=middleware,
            tags=tags,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        route_class_override: type[BaseRoute] | None = None,
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register an API route with the router.

        This method allows you to decorate a function or class to register it as an API route,
        specifying the path, HTTP methods, middleware, documentation, and response model.

        Args:
            path (str): The route path pattern.
            methods (Sequence[str] | None): List of HTTP methods allowed for this route.
            name (str | None): Optional name for the route.
            middleware (Sequence[Middleware] | None): Optional middleware stack for this route.
            summary (str | None): Optional summary for documentation.
            description (str | None): Optional description for documentation.
            tags (Sequence[str] | None): Optional tags for grouping routes.
            include_in_schema (bool | None): Whether to include this route in the OpenAPI schema.
            route_class_override (type[BaseRoute] | None): Optional custom route class to use.
            response_model (type | None): Optional response model for documentation.

        Returns:
            Callable[[Callable[..., Any]], Callable[..., Any]]: A decorator that registers the route.

        """ # noqa
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
                response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Create a generic factory method for HTTP method decorators.

        Eliminates code duplication across get, post, put, delete, patch, options methods.
        """  # noqa: E501
        return self.api_route(
            path=path,
            tags=tags,
            summary=summary,
            description=description,
            methods=[method.upper()],
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Add a *path operation* using an HTTP GET operation.

        ## Example
        ```python
        router = Router()


        @router.get('/items/')
        def read_items():
            return [{'name': 'Empanada'}, {'name': 'Arepa'}]
        ```
        """
        return self._create_http_method_decorator(
            'get',
            path=path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Add a *path operation* using an HTTP POST operation.

        ## Example
        ```python
        router = Router()


        @router.post('/items/')
        def create_item():
            return [{'name': 'Empanada'}, {'name': 'Arepa'}]
        ```
        """
        return self._create_http_method_decorator(
            'POST',
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Add a *path operation* using an HTTP PUT operation.

        ## Example
        ```python
        router = Router()


        @router.put('/items/')
        def update_item():
            return [{'name': 'Empanada'}, {'name': 'Arepa'}]
        ```
        """
        return self._create_http_method_decorator(
            'PUT',
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Add a *path operation* using an HTTP DELETE operation.

        ## Example
        ```python
        router = Router()


        @router.delete('/items/')
        def delete_item():
            return [{'name': 'Empanada'}, {'name': 'Arepa'}]
        ```
        """
        return self._create_http_method_decorator(
            'DELETE',
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Add a *path operation* using an HTTP PATCH operation."""
        return self._create_http_method_decorator(
            'PATCH',
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
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
        response_model: type | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Add a *path operation* using an HTTP OPTIONS operation."""
        return self._create_http_method_decorator(
            'OPTIONS',
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
        )

    def add_websocket_route(
        self,
        path: str,
        endpoint: Any,
        name: str | None = None,
    ) -> None:
        """Add a WebSocket route to the router."""
        from velithon.websocket import WebSocketRoute

        full_path = self._get_full_path(path)
        route = WebSocketRoute(full_path, endpoint, name)
        self.routes.append(route)
        self._rebuild_rust_optimizations()

    def websocket(
        self,
        path: str,
        *,
        name: str | None = None,
    ) -> Callable[[Any], Any]:
        """Add a WebSocket route decorator.

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

    def add_router(
        self,
        router: 'Router',
        *,
        prefix: str = '',
        tags: Sequence[str] | None = None,
    ) -> None:
        """Add a sub-router to this router.

        Args:
            router: The Router instance to add
            prefix: Path prefix to add to all routes in the router
            tags: Tags to add to all routes in the router

        """
        # Create new routes with the combined prefix
        for route in router.routes:
            if hasattr(route, 'path'):
                # Start with the route's original path
                new_path = route.path

                # If the router being added has a path prefix, that's already included in the route path  # noqa: E501
                # So we only need to apply the additional prefix if provided
                if prefix:
                    # If prefix is provided, prepend it to the route path
                    if not prefix.startswith('/'):
                        prefix = '/' + prefix
                    prefix = prefix.rstrip('/')

                    # If this router has its own path, prepend that too
                    if self.path:
                        new_path = self.path + prefix + new_path
                    else:
                        new_path = prefix + new_path
                else:
                    # No additional prefix, just add this router's path if it exists
                    if self.path:
                        new_path = self.path + new_path

                # Normalize double slashes
                while '//' in new_path:
                    new_path = new_path.replace('//', '/')

                # Create new route with updated path
                new_route = Route(
                    new_path,
                    endpoint=route.endpoint,
                    methods=route.methods,
                    name=route.name,
                    middleware=getattr(route, 'middleware', None),
                    summary=route.summary,
                    description=route.description,
                    tags=list(route.tags) + list(tags)
                    if route.tags and tags
                    else route.tags or tags,
                    include_in_schema=route.include_in_schema,
                    response_model=getattr(route, 'response_model', None),
                )
                self.routes.append(new_route)
            else:
                # Handle other route types (WebSocket, etc.)
                self.routes.append(route)

        # Add startup and shutdown handlers
        self.on_startup.extend(router.on_startup)
        self.on_shutdown.extend(router.on_shutdown)

        # Rebuild optimizations
        self._rebuild_rust_optimizations()
