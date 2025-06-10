import asyncio
import logging
from typing import (
    Annotated,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Sequence,
)

import granian
import granian.http
from typing_extensions import Doc

from velithon._utils import is_async_callable
from velithon.datastructures import FunctionInfo, Protocol, Scope
from velithon.di import ServiceContainer
from velithon.logging import configure_logger
from velithon.middleware import Middleware
from velithon.middleware.di import DIMiddleware
from velithon.middleware.logging import LoggingMiddleware
from velithon.middleware.wrapped import WrappedRSGITypeMiddleware
from velithon.openapi.ui import get_swagger_ui_html
from velithon.performance import get_middleware_optimizer
from velithon.requests import Request
from velithon.responses import HTMLResponse, JSONResponse, Response
from velithon.routing import BaseRoute, Router
from velithon.types import RSGIApp
from velithon.vsp import VSPManager

_middleware_optimizer = get_middleware_optimizer()

logger = logging.getLogger(__name__)


class Velithon:
    def __init__(
        self: RSGIApp,
        *,
        routes: Annotated[
            Sequence[BaseRoute] | None,
            Doc(
                """
                A list of routes to be registered with the application. If not
                provided, the application will not have any routes.
                """
            ),
        ] = None,
        middleware: Annotated[
            Sequence[Middleware] | None,
            Doc(
                """
                A list of middleware classes to be applied to the application. If
                not provided, no middleware will be applied.
                """
            ),
        ] = None,
        on_startup: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A list of callables to be executed on application startup. If not
                provided, no startup actions will be performed.
                """
            ),
        ] = None,
        on_shutdown: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A list of callables to be executed on application shutdown. If not
                provided, no shutdown actions will be performed.
                """
            ),
        ] = None,
        openapi_version: Annotated[
            str,
            Doc(
                """
                The version string of OpenAPI.
                """
            ),
        ] = "3.0.0",
        title: Annotated[
            str,
            Doc(
                """
                The title of the application. This is used for documentation
                generation and other purposes.
                """
            ),
        ] = "Velithon",
        summary: Annotated[
            str | None,
            Doc(
                """
                A short summary of the API.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = None,
        description: Annotated[
            str,
            Doc(
                """
                A description of the API. Supports Markdown (using
                [CommonMark syntax](https://commonmark.org/)).

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = "",
        version: Annotated[
            str,
            Doc(
                """
                The version of the API.

                **Note** This is the version of your application, not the version of
                the OpenAPI specification nor the version of App being used.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                """
            ),
        ] = "0.1.0",
        openapi_url: Annotated[
            str | None,
            Doc(
                """
                The URL where the OpenAPI schema will be served from.

                If you set it to `None`, no OpenAPI schema will be served publicly, and
                the default automatic endpoints `/docs` and `/redoc` will also be
                disabled.

                """
            ),
        ] = "/openapi.json",
        swagger_ui_oauth2_redirect_url: Annotated[
            str | None,
            Doc(
                """
                The OAuth2 redirect endpoint for the Swagger UI.

                By default it is `/docs/oauth2-redirect`.

                This is only used if you use OAuth2 (with the "Authorize" button)
                with Swagger UI.
                """
            ),
        ] = "/docs/oauth2-redirect",
        swagger_ui_init_oauth: Annotated[
            Dict[str, Any] | None,
            Doc(
                """
                OAuth2 configuration for the Swagger UI, by default shown at `/docs`.

                Read more about the available configuration options in the
                [Swagger UI docs](https://swagger.io/docs/open-source-tools/swagger-ui/usage/oauth2/).
                """
            ),
        ] = None,
        openapi_tags: Annotated[
            List[Dict[str, Any]] | None,
            Doc(
                """
                A list of tags used by OpenAPI, these are the same `tags` you can set
                in the *path operations*, like:

                * `@app.get("/users/", tags=["users"])`
                * `@app.get("/items/", tags=["items"])`

                The order of the tags can be used to specify the order shown in
                tools like Swagger UI, used in the automatic path `/docs`.

                It's not required to specify all the tags used.

                The tags that are not declared MAY be organized randomly or based
                on the tools' logic. Each tag name in the list MUST be unique.

                The value of each item is a `dict` containing:
                """
            ),
        ] = None,
        servers: Annotated[
            List[Dict[str, str | Any]] | None,
            Doc(
                """
                A `list` of `dict`s with connectivity information to a target server.
                """
            ),
        ] = None,
        docs_url: Annotated[
            str | None,
            Doc(
                """
                The path to the automatic interactive API documentation.
                It is handled in the browser by Swagger UI.

                The default URL is `/docs`. You can disable it by setting it to `None`.
                If `openapi_url` is set to `None`, this will be automatically disabled.
                """
            ),
        ] = "/docs",
        terms_of_service: Annotated[
            str | None,
            Doc(
                """
                A URL to the Terms of Service for your API.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                """
            ),
        ] = None,
        contact: Annotated[
            Dict[str, str | Any] | None,
            Doc(
                """
                A dictionary with the contact information for the exposed API.

                It can contain several fields.

                * `name`: (`str`) The name of the contact person/organization.
                * `url`: (`str`) A URL pointing to the contact information. MUST be in
                    the format of a URL.
                * `email`: (`str`) The email address of the contact person/organization.
                    MUST be in the format of an email address.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = None,
        license_info: Annotated[
            Dict[str, str | Any] | None,
            Doc(
                """
                A dictionary with the license information for the exposed API.

                It can contain several fields.

                * `name`: (`str`) **REQUIRED** (if a `license_info` is set). The
                    license name used for the API.
                * `identifier`: (`str`) An [SPDX](https://spdx.dev/) license expression
                    for the API. The `identifier` field is mutually exclusive of the `url`
                    field
                * `url`: (`str`) A URL to the license used for the API. This MUST be
                    the format of a URL.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = None,
        tags: Annotated[
            List[Dict[str, str | Any]] | None,
            Doc(
                """
                A list of tags used by OpenAPI, these are the same `tags` you can set
                in the *path operations*, like:

                * `@app.get("/users/", tags=["users"])`
                * `@app.get("/items/", tags=["items"])`

                The order of the tags can be used to specify the order shown in
                tools like Swagger UI, used in the automatic path `/docs`.

                It's not required to specify all the tags used.

                The tags that are not declared MAY be organized randomly or based
                on the tools' logic. Each tag name in the list MUST be unique.

                The value of each item is a `dict` containing:
                """
            ),
        ] = None,
    ):
        self.router = Router(routes, on_startup=on_startup, on_shutdown=on_shutdown)
        self.container = None

        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: RSGIApp | None = None
        self.title = title
        self.summary = summary
        self.description = description
        self.version = version
        self.openapi_version = openapi_version
        self.openapi_url = openapi_url
        self.swagger_ui_oauth2_redirect_url = swagger_ui_oauth2_redirect_url
        self.swagger_ui_init_oauth = swagger_ui_init_oauth
        self.openapi_tags = openapi_tags
        self.servers = servers or []
        self.docs_url = docs_url
        self.terms_of_service = terms_of_service
        self.contact = contact
        self.license_info = license_info
        self.tags = tags or []
        self.startup_functions: List[FunctionInfo] = []
        self.shutdown_functions: List[FunctionInfo] = []
        self.setup()

    def register_container(self, container: ServiceContainer) -> None:
        """
        Register a ServiceContainer for dependency injection.

        Args:
            container: The ServiceContainer instance containing providers.
        """
        self.container = container

    def register_vps(self, vsp_manager: VSPManager) -> None:
        """
        Register a VSPManager for managing VSP services.

        Args:
            vsp_manager: The VSPManager instance to be used by the application.
        """
        self.vsp_manager = vsp_manager

    def build_middleware_stack(self) -> RSGIApp:
        middleware = [
            Middleware(WrappedRSGITypeMiddleware),
            Middleware(LoggingMiddleware),
        ]
        if self.container:
            middleware.append(Middleware(DIMiddleware, self))
        middleware += self.user_middleware

        # Extract middleware classes for optimization
        middleware_classes = [m.cls for m in middleware]
        optimized_classes = _middleware_optimizer.optimize_middleware_stack(
            middleware_classes
        )

        # Rebuild middleware list with optimized order
        optimized_middleware = []
        for cls in optimized_classes:
            # Find corresponding middleware with args/kwargs
            for m in middleware:
                if m.cls == cls:
                    optimized_middleware.append(m)
                    break
        middleware = optimized_middleware

        app = self.router
        for cls, args, kwargs in reversed(middleware):
            app = cls(app, *args, **kwargs)
        return app

    async def __call__(self, scope: Scope, protocol: Protocol):
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, protocol)

    def setup(self) -> None:
        if self.openapi_url:
            urls = (server_data.get("url") for server_data in self.servers)
            server_urls = {url for url in urls if url}

            async def openapi(req: Request) -> JSONResponse:
                root_path = req.scope.server.rstrip("/")
                if root_path not in server_urls:
                    if root_path:
                        self.servers.insert(
                            0, {"url": req.scope.scheme + "://" + root_path}
                        )
                        server_urls.add(root_path)
                return JSONResponse(self.get_openapi())

            self.add_route(
                self.openapi_url,
                openapi,
                include_in_schema=False,
            )
        if self.openapi_url and self.docs_url:

            async def swagger_ui_html(req: Request) -> HTMLResponse:
                root_path = req.scope.scheme + "://" + req.scope.server.rstrip("/")
                openapi_url = root_path + self.openapi_url
                oauth2_redirect_url = self.swagger_ui_oauth2_redirect_url
                if oauth2_redirect_url:
                    oauth2_redirect_url = root_path + oauth2_redirect_url
                return get_swagger_ui_html(
                    openapi_url=openapi_url,
                    title=f"{self.title} - Swagger UI",
                    oauth2_redirect_url=oauth2_redirect_url,
                    init_oauth=self.swagger_ui_init_oauth,
                )

            self.add_route(
                self.docs_url,
                swagger_ui_html,
                include_in_schema=False,
            )

    def get_openapi(
        self: RSGIApp,
    ) -> Dict[str, Any]:
        main_docs = {
            "openapi": self.openapi_version,
            "info": {},
            "paths": {},
            "components": {"schemas": {}},
        }
        info: Dict[str, Any] = {"title": self.title, "version": self.version}
        if self.summary:
            info["summary"] = self.summary
        if self.description:
            info["description"] = self.description
        if self.terms_of_service:
            info["termsOfService"] = self.terms_of_service
        if self.contact:
            info["contact"] = self.contact
        if self.license_info:
            info["license"] = self.license_info
        if self.servers:
            main_docs["servers"] = self.servers
        for route in self.router.routes or []:
            if not route.include_in_schema:
                continue
            path, schema = route.openapi()
            main_docs["paths"].update(path)
            main_docs["components"]["schemas"].update(schema)
        if self.tags:
            main_docs["tags"] = self.tags
        main_docs["info"] = info
        return main_docs

    def add_route(
        self,
        path: str,
        route: Callable[[Request], Awaitable[Response] | Response],
        methods: list[str] | None = None,
        name: str | None = None,
        include_in_schema: bool = True,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> None:  # pragma: no cover
        self.router.add_route(
            path,
            route,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            summary=summary,
            description=description,
            tags=tags,
        )

    def add_websocket_route(
        self,
        path: str,
        endpoint: Any,
        name: str | None = None,
    ) -> None:
        """Add a WebSocket route to the application."""
        self.router.add_websocket_route(path, endpoint, name)

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
        Decorator to add a GET route to the application.

        Args:
            path: The path pattern
            tags: Optional tags for documentation
            summary: Optional summary for documentation
            description: Optional description for documentation
            name: Optional name for the route
            include_in_schema: Whether to include in OpenAPI schema

        Returns:
            Decorator function
        """
        return self._create_http_method_decorator(
            "get",
            path,
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
        Decorator to add a POST route to the application.

        Args:
            path: The path pattern
            tags: Optional tags for documentation
            summary: Optional summary for documentation
            description: Optional description for documentation
            name: Optional name for the route
            include_in_schema: Whether to include in OpenAPI schema

        Returns:
            Decorator function
        """
        return self._create_http_method_decorator(
            "post",
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
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
        Decorator to add a PUT route to the application.

        Args:
            path: The path pattern
            tags: Optional tags for documentation
            summary: Optional summary for documentation
            description: Optional description for documentation
            name: Optional name for the route
            include_in_schema: Whether to include in OpenAPI schema

        Returns:
            Decorator function
        """
        return self._create_http_method_decorator(
            "put",
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
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
        Decorator to add a DELETE route to the application.

        Args:
            path: The path pattern
            tags: Optional tags for documentation
            summary: Optional summary for documentation
            description: Optional description for documentation
            name: Optional name for the route
            include_in_schema: Whether to include in OpenAPI schema

        Returns:
            Decorator function
        """
        return self._create_http_method_decorator(
            "delete",
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
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
        Decorator to add a PATCH route to the application.

        Args:
            path: The path pattern
            tags: Optional tags for documentation
            summary: Optional summary for documentation
            description: Optional description for documentation
            name: Optional name for the route
            include_in_schema: Whether to include in OpenAPI schema

        Returns:
            Decorator function
        """
        return self._create_http_method_decorator(
            "patch",
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
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
        Decorator to add an OPTIONS route to the application.

        Args:
            path: The path pattern
            tags: Optional tags for documentation
            summary: Optional summary for documentation
            description: Optional description for documentation
            name: Optional name for the route
            include_in_schema: Whether to include in OpenAPI schema

        Returns:
            Decorator function
        """
        return self._create_http_method_decorator(
            "options",
            path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
        )

    def websocket(
        self,
        path: str,
        *,
        name: str | None = None,
    ) -> Callable[[Any], Any]:
        """
        Decorator to add a WebSocket route to the application.

        Args:
            path: The WebSocket path pattern
            name: Optional name for the route

        Returns:
            Decorator function
        """
        return self.router.websocket(path, name=name)

    def on_startup(self, priority: int = 0) -> None:
        """
        This decorator is used to register a function to be called on startup.
        The function can be either synchronous or asynchronous.
        The function will be called with the application instance as the first
        argument.
        The function will be called in the order of priority, with lower
        priority functions being called first.
        Args:
            priority: The priority of the function. Lower numbers are called first.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            is_async = is_async_callable(func)
            function_info = FunctionInfo(
                func=func,
                is_async=is_async,
                priority=priority,
            )
            self.startup_functions.append(function_info)
            self.startup_functions.sort()

        return decorator

    def on_shutdown(self, priority: int = 0) -> None:
        """
        This decorator is used to register a function to be called on shutdown.
        The function can be either synchronous or asynchronous.
        The function will be called with the application instance as the first
        argument.
        The function will be called in the order of priority, with lower
        priority functions being called first.

        Args:
            priority: The priority of the function. Lower numbers are called first.

        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            is_async = is_async_callable(func)
            function_info = FunctionInfo(
                func=func,
                is_async=is_async,
                priority=priority,
            )
            self.shutdown_functions.append(function_info)
            self.shutdown_functions.sort()

        return decorator

    def config_logger(self) -> None:
        configure_logger(
            log_file=self.log_file,
            level=self.log_level,
            log_format=self.log_format,
            log_to_file=self.log_to_file,
            max_bytes=self.max_bytes,
            backup_count=self.backup_count,
        )

    def __rsgi_init__(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        This method is called when the server is initialized.
        It is used to set up the server and perform any necessary
        Arg:
            loop: The event loop to be used by the server.

        ```python
        some_sync_init_task()
        loop.run_until_complete(some_async_init_task())
        ```
        """
        # configure the logger
        self.config_logger()

        # internal server startup
        if hasattr(self, "vsp_manager"):
            loop.create_task(
                self.vsp_manager.start_server(self.vsp_host, self.vsp_port, loop=loop)
            )

        # run all the startup functions from user setup
        for function_info in self.startup_functions:
            loop.run_until_complete(function_info())

        # freeze the memory
        del self.startup_functions

    def __rsgi_del__(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        This method is called when the server is shutting down.
        It is used to clean up the server and perform any necessary
        Arg:
            loop: The event loop to be used by the server.
        ```python
        some_sync_init_task()
        loop.run_until_complete(some_async_init_task())
        ```
        """
        for function_info in self.shutdown_functions:
            loop.run_until_complete(function_info())

    def _serve(
        self,
        app,
        host,
        port,
        workers,
        log_file,
        log_level,
        log_format,
        log_to_file,
        max_bytes,
        backup_count,
        reload,
        blocking_threads,
        blocking_threads_idle_timeout,
        runtime_threads,
        runtime_blocking_threads,
        runtime_mode,
        loop,
        task_impl,
        http,
        http1_buffer_size,
        http1_header_read_timeout,
        http1_keep_alive,
        http1_pipeline_flush,
        http2_adaptive_window,
        http2_initial_connection_window_size,
        http2_initial_stream_window_size,
        http2_keep_alive_interval,
        http2_keep_alive_timeout,
        http2_max_concurrent_streams,
        http2_max_frame_size,
        http2_max_headers_size,
        http2_max_send_buffer_size,
        ssl_certificate,
        ssl_keyfile,
        ssl_keyfile_password,
        backpressure,
        vsp_host,
        vsp_port,
    ) -> None:
        # Set up logging configuration
        self.log_file = log_file
        self.log_level = log_level
        self.log_format = log_format
        self.log_to_file = log_to_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.config_logger()

        self.vsp_host = vsp_host
        self.vsp_port = vsp_port

        # Configure Granian server
        server = granian.Granian(
            target=app,  # Velithon application instance
            address=host,
            port=port,
            interface="rsgi",  # Use RSGI interface
            workers=workers,
            reload=reload,
            log_enabled=False,
            blocking_threads=blocking_threads,
            blocking_threads_idle_timeout=blocking_threads_idle_timeout,
            runtime_threads=runtime_threads,
            runtime_blocking_threads=runtime_blocking_threads,
            runtime_mode=runtime_mode,
            loop=loop,
            task_impl=task_impl,
            http=http,
            ssl_cert=ssl_certificate,
            ssl_key=ssl_keyfile,
            ssl_key_password=ssl_keyfile_password,
            backpressure=backpressure,
            http1_settings=granian.http.HTTP1Settings(
                header_read_timeout=http1_header_read_timeout,
                keep_alive=http1_keep_alive,
                max_buffer_size=http1_buffer_size,
                pipeline_flush=http1_pipeline_flush,
            ),
            http2_settings=granian.http.HTTP2Settings(
                adaptive_window=http2_adaptive_window,
                initial_connection_window_size=http2_initial_connection_window_size,
                initial_stream_window_size=http2_initial_stream_window_size,
                keep_alive_interval=http2_keep_alive_interval,
                keep_alive_timeout=http2_keep_alive_timeout,
                max_concurrent_streams=http2_max_concurrent_streams,
                max_frame_size=http2_max_frame_size,
                max_headers_size=http2_max_headers_size,
                max_send_buffer_size=http2_max_send_buffer_size,
            ),
        )
        # check log level is debug then log all the parameters
        if log_level == "DEBUG":
            logger.debug(
                f"\n App: {app} \n Host: {host} \n Port: {port} \n Workers: {workers} \n "
                f"Log File: {log_file} \n Log Level: {log_level} \n Log Format: {log_format} \n "
                f"Log to File: {log_to_file} \n Max Bytes: {max_bytes} \n Backup Count: {backup_count} \n "
                f"Blocking Threads: {blocking_threads} \n Blocking Threads Idle Timeout: {blocking_threads_idle_timeout} \n "
                f"Runtime Threads: {runtime_threads} \n Runtime Blocking Threads: {runtime_blocking_threads} \n "
                f"Runtime Mode: {runtime_mode} \n Loop: {loop} \n Task Impl: {task_impl} \n "
                f"HTTP: {http} \n HTTP1 Buffer Size: {http1_buffer_size} \n "
                f"HTTP1 Header Read Timeout: {http1_header_read_timeout} \n "
                f"HTTP1 Keep Alive: {http1_keep_alive} \n HTTP1 Pipeline Flush: {http1_pipeline_flush} \n "
                f"HTTP2 Adaptive Window: {http2_adaptive_window} \n "
                f"HTTP2 Initial Connection Window Size: {http2_initial_connection_window_size} \n "
                f"HTTP2 Initial Stream Window Size: {http2_initial_stream_window_size} \n "
                f"HTTP2 Keep Alive Interval: {http2_keep_alive_interval} \n "
                f"HTTP2 Keep Alive Timeout: {http2_keep_alive_timeout} \n "
                f"HTTP2 Max Concurrent Streams: {http2_max_concurrent_streams} \n "
                f"HTTP2 Max Frame Size: {http2_max_frame_size} \n "
                f"HTTP2 Max Headers Size: {http2_max_headers_size} \n "
                f"HTTP2 Max Send Buffer Size: {http2_max_send_buffer_size} \n "
                f"SSL Certificate: {ssl_certificate} \n SSL Keyfile: {ssl_keyfile} \n "
                f"SSL Keyfile Password: {'*' * len(ssl_keyfile_password) if ssl_keyfile_password else None} \n "
                f"Backpressure: {backpressure}"
            )

        logger.info(
            f"Starting Velithon server at http://{host}:{port} with {workers} workers..."
        )
        if reload:
            logger.debug("Auto-reload enabled.")
        server.serve()

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
        # Special case for OPTIONS method - use api_route directly
        if method.upper() == "OPTIONS":
            return self.router.api_route(
                path=path,
                tags=tags,
                summary=summary,
                description=description,
                methods=["OPTIONS"],
                name=name,
                include_in_schema=include_in_schema,
            )

        return getattr(self.router, method.lower())(
            path=path,
            tags=tags,
            summary=summary,
            description=description,
            name=name,
            include_in_schema=include_in_schema,
        )
