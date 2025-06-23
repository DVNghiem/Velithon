"""Gateway module for Velithon framework.

This module provides gateway functionality to forward requests to backend services,
enabling gradual migration from monolithic to microservice architecture.
"""

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from velithon._velithon import ProxyClient, ProxyLoadBalancer
from velithon.datastructures import Protocol, Scope
from velithon.requests import Request
from velithon.responses import JSONResponse, Response
from velithon.routing import BaseRoute, Match

logger = logging.getLogger(__name__)


class GatewayRoute(BaseRoute):
    """A route that forwards requests to backend services.

    This route can forward requests to a single backend or multiple backends
    with load balancing capabilities.
    """

    def __init__(
        self,
        path: str,
        targets: str | list[str],
        *,
        methods: Sequence[str] | None = None,
        name: str | None = None,
        strip_path: bool = False,
        preserve_host: bool = False,
        timeout_ms: int = 30000,
        max_retries: int = 3,
        load_balancing_strategy: str = 'round_robin',
        weights: list[int] | None = None,
        health_check_path: str | None = None,
        headers_to_add: dict[str, str] | None = None,
        headers_to_remove: list[str] | None = None,
        path_rewrite: str | None = None,
        middleware: Sequence[Any] | None = None,
    ):
        """Initialize a gateway route.

        Args:
            path: The path pattern to match (supports Velithon path parameters)
            targets: Single target URL or list of target URLs for load balancing
            methods: HTTP methods to match (defaults to all methods)
            name: Optional name for the route
            strip_path: Whether to strip the matched path from forwarded request
            preserve_host: Whether to preserve the original Host header
            timeout_ms: Request timeout in milliseconds
            max_retries: Maximum number of retries
            load_balancing_strategy: Strategy for load balancing ("round_robin", "random", "weighted")
            weights: Weights for weighted load balancing (required if strategy is "weighted")
            health_check_path: Path for health checks (defaults to "/health")
            headers_to_add: Headers to add to forwarded requests
            headers_to_remove: Headers to remove from forwarded requests
            path_rewrite: Rewrite the path before forwarding (supports regex patterns)
            middleware: Middleware to apply to this route

        """
        self.path = path
        self.methods = list(methods) if methods else None
        self.name = name or f'gateway_{path}'
        self.strip_path = strip_path
        self.preserve_host = preserve_host
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.headers_to_add = headers_to_add or {}
        self.headers_to_remove = headers_to_remove or []
        self.path_rewrite = path_rewrite
        self.middleware = middleware or []

        # Compile path pattern using Velithon's routing
        from velithon._velithon import compile_path
        from velithon.convertors import CONVERTOR_TYPES

        path_regex, self.path_format, self.path_converters = compile_path(
            path, CONVERTOR_TYPES
        )
        import re

        self.path_regex = re.compile(path_regex)

        # Initialize proxy client(s)
        if isinstance(targets, str):
            # Single target
            self.proxy_client = ProxyClient(
                target_url=targets, timeout_ms=timeout_ms, max_retries=max_retries
            )
            self.load_balancer = None
        else:
            # Multiple targets with load balancing
            self.load_balancer = ProxyLoadBalancer(
                targets=targets,
                strategy=load_balancing_strategy,
                weights=weights,
                health_check_url=health_check_path,
            )
            self.proxy_client = None

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """Check if this route matches the incoming request."""
        if scope.proto != 'http':
            return Match.NONE, scope

        method = scope.method
        path = scope.path

        # Check HTTP method
        if self.methods is not None and method not in self.methods:
            return Match.NONE, scope

        # Check path
        match = self.path_regex.match(path)
        if not match:
            return Match.NONE, scope

        matched_params = match.groupdict()
        converted_params = {}

        for key, value in matched_params.items():
            if key in self.path_converters:
                converted_value = self.path_converters[key].convert(value)
                converted_params[key] = converted_value
            else:
                converted_params[key] = value

        # Set path params on scope like other routes do
        scope._path_params = converted_params
        return Match.FULL, scope

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        """Handle the incoming request and forward it to backend."""
        request = Request(scope, protocol)

        try:
            # Get target URL
            if self.load_balancer:
                target_url = await self.load_balancer.get_next_target()
            else:
                target_url = self.proxy_client.target_url

            # Prepare forwarded request
            forwarded_path = await self._prepare_path(request)
            forwarded_headers = await self._prepare_headers(request)
            forwarded_body = await self._prepare_body(request)
            query_params = dict(request.query_params)

            # Forward request
            if self.proxy_client:
                # Single target
                status, body, headers = await self.proxy_client.forward_request(
                    method=request.method,
                    path=forwarded_path,
                    headers=forwarded_headers,
                    body=forwarded_body,
                    query_params=query_params if query_params else None,
                )
            else:
                # Load balanced targets
                # Create a temporary proxy client for the selected target
                temp_client = ProxyClient(
                    target_url=target_url,
                    timeout_ms=self.timeout_ms,
                    max_retries=self.max_retries,
                )
                status, body, headers = await temp_client.forward_request(
                    method=request.method,
                    path=forwarded_path,
                    headers=forwarded_headers,
                    body=forwarded_body,
                    query_params=query_params if query_params else None,
                )

            # Create response
            response = Response(content=body, status_code=status, headers=dict(headers))

        except Exception as e:
            logger.error(f'Gateway error for {request.url}: {e}')
            response = JSONResponse(
                content={'error': 'Gateway error', 'detail': str(e)},
                status_code=502,  # Bad Gateway
            )

        await response(scope, protocol)

    async def _prepare_path(self, request: Request) -> str:
        """Prepare the path for forwarding."""
        path = request.url.path

        # Apply path rewriting if configured
        if self.path_rewrite:
            import re

            # Check if path_rewrite is a direct replacement (starts with /)
            if self.path_rewrite.startswith('/'):
                # Direct path replacement
                path = self.path_rewrite
            else:
                # Pattern-based replacement
                path = re.sub(self.path, self.path_rewrite, path)

        # Strip matched path if configured
        if self.strip_path:
            # Remove the matched portion
            match = self.path_regex.match(path)
            if match:
                matched_part = match.group(0)
                path = path[len(matched_part) :]
                if not path.startswith('/'):
                    path = '/' + path

        return path

    async def _prepare_headers(self, request: Request) -> dict[str, str] | None:
        """Prepare headers for forwarding."""
        headers = dict(request.headers)

        # Remove specified headers
        for header_name in self.headers_to_remove:
            headers.pop(header_name.lower(), None)

        # Add specified headers
        headers.update(self.headers_to_add)

        # Handle Host header
        if not self.preserve_host:
            headers.pop('host', None)

        return headers if headers else None

    async def _prepare_body(self, request: Request) -> bytes | None:
        """Prepare request body for forwarding."""
        try:
            body = await request.body()
            return body if body else None
        except Exception:
            return None

    async def openapi(self) -> tuple[dict, dict]:
        """Generate OpenAPI documentation for this gateway route."""
        # Basic OpenAPI spec for gateway routes
        path_spec = {
            'summary': 'Gateway to backend service',
            'description': 'Forwards requests to backend service(s)',
            'tags': ['Gateway'],
            'responses': {
                '200': {'description': 'Successful response from backend'},
                '502': {'description': 'Bad Gateway - Backend service error'},
                '503': {'description': 'Service Unavailable - No healthy backends'},
            },
        }

        methods = self.methods or ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        path_methods = {}
        for method in methods:
            path_methods[method.lower()] = path_spec

        return {self.path: path_methods}, {}


class Gateway:
    """High-level gateway configuration and management.

    Provides convenient methods to create gateway routes and manage
    backend services.
    """

    def __init__(self):
        self.routes: list[GatewayRoute] = []
        self.load_balancers: dict[str, ProxyLoadBalancer] = {}

    def add_route(self, path: str, targets: str | list[str], **kwargs) -> GatewayRoute:
        """Add a gateway route."""
        route = GatewayRoute(path, targets, **kwargs)
        self.routes.append(route)
        return route

    def forward_to(
        self, targets: str | list[str], **route_kwargs
    ) -> Callable[[Callable], GatewayRoute]:
        """Decorator to create gateway routes.

        Usage:
            @gateway.forward_to("http://backend:8080")
            def api_v1():
                pass  # This will create a route at the function's path
        """  # noqa: D401

        def decorator(func: Callable) -> GatewayRoute:
            # Use function name to determine path if not specified
            path = route_kwargs.pop('path', f'/{func.__name__}')
            name = route_kwargs.pop('name', func.__name__)

            route = GatewayRoute(path=path, targets=targets, name=name, **route_kwargs)
            self.routes.append(route)
            return route

        return decorator

    async def health_check_all(self) -> dict[str, Any]:
        """Perform health checks on all load balancers."""
        results = {}

        for name, lb in self.load_balancers.items():
            try:
                await lb.health_check()
                status = await lb.get_health_status()
                results[name] = status
            except Exception as e:
                results[name] = {'error': str(e)}

        return results

    def get_routes(self) -> list[GatewayRoute]:
        """Get all gateway routes."""
        return self.routes.copy()


# Convenience functions for creating gateway routes
def gateway_route(path: str, targets: str | list[str], **kwargs) -> GatewayRoute:
    """Create a gateway route."""
    return GatewayRoute(path, targets, **kwargs)


def forward_to(
    path: str, target: str, **kwargs
) -> Callable[[Request], Awaitable[Response]]:
    """Create a simple forwarding function.

    This can be used as a regular endpoint function in Velithon routes.
    """
    client = ProxyClient(
        target_url=target,
        timeout_ms=kwargs.get('timeout_ms', 30000),
        max_retries=kwargs.get('max_retries', 3),
    )

    async def forward_request(request: Request) -> Response:
        try:
            # Prepare request data
            forwarded_path = request.url.path
            if kwargs.get('strip_path'):
                # Simple path stripping - remove the matched part
                forwarded_path = forwarded_path.replace(path.rstrip('/*'), '', 1)
                if forwarded_path and not forwarded_path.startswith('/'):
                    forwarded_path = '/' + forwarded_path

            headers = dict(request.headers)
            if not kwargs.get('preserve_host'):
                headers.pop('host', None)

            body = await request.body()
            query_params = dict(request.query_params)

            # Forward request
            status, response_body, response_headers = await client.forward_request(
                method=request.method,
                path=forwarded_path,
                headers=headers if headers else None,
                body=body if body else None,
                query_params=query_params if query_params else None,
            )

            return Response(
                content=response_body,
                status_code=status,
                headers=dict(response_headers),
            )

        except Exception as e:
            logger.error(f'Forward error for {request.url}: {e}')
            return JSONResponse(
                content={'error': 'Gateway error', 'detail': str(e)}, status_code=502
            )

    return forward_request
