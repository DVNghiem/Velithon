from __future__ import annotations

import re
import typing

from velithon._velithon import Match  # Import directly from Rust module
from velithon.convertors import CONVERTOR_TYPES
from velithon.datastructures import Protocol, Scope
from velithon.routing import BaseRoute
from velithon.websocket.connection import WebSocket
from velithon.websocket.endpoint import WebSocketEndpoint, websocket_response


class WebSocketRoute(BaseRoute):
    """WebSocket route implementation that integrates with Velithon's routing system."""
    
    def __init__(
        self,
        path: str,
        endpoint: typing.Union[
            typing.Callable[[WebSocket], typing.Awaitable[None]],
            type[WebSocketEndpoint]
        ],
        name: str | None = None,
    ) -> None:
        self.path = path
        self.endpoint = endpoint
        self.name = name or getattr(endpoint, "__name__", "websocket")
        
        # Compile path regex for matching
        from velithon.routing import compile_path
        path_regex, self.path_format, self.param_convertors = compile_path(path, CONVERTOR_TYPES)
        self.path_regex = re.compile(path_regex)
        
        # Prepare the application
        if isinstance(endpoint, type) and issubclass(endpoint, WebSocketEndpoint):
            # Class-based endpoint
            async def app(scope: Scope, protocol: Protocol) -> None:
                websocket = WebSocket(scope, protocol)
                endpoint_instance = endpoint(scope, protocol)
                await endpoint_instance(websocket)
            self.app = app
        else:
            # Function-based endpoint
            self.app = websocket_response(endpoint)

    def matches(self, scope: Scope) -> tuple[Match, Scope]:
        """Check if this route matches the given scope."""
        if scope.proto == "websocket":
            route_path = scope.path
            regex_match = self.path_regex.match(route_path)
            if regex_match:
                matched_params = regex_match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                setattr(scope, "_path_params", matched_params)
                return Match.FULL, scope
        return Match.NONE, {}

    async def handle(self, scope: Scope, protocol: Protocol) -> None:
        """Handle the WebSocket connection."""
        await self.app(scope, protocol)

    async def openapi(self) -> tuple[dict[str, typing.Any], dict[str, typing.Any]]:
        """WebSocket routes don't generate OpenAPI docs."""
        return {}, {}

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, WebSocketRoute)
            and self.path == other.path
            and self.endpoint == other.endpoint
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        path, name = self.path, self.name
        return f"{class_name}(path={path!r}, name={name!r})"


def websocket_route(path: str, name: str | None = None) -> typing.Callable:
    """
    Decorator for creating WebSocket routes.
    
    Args:
        path: The WebSocket path pattern
        name: Optional name for the route
        
    Returns:
        Decorator function
    """
    def decorator(
        func: typing.Callable[[WebSocket], typing.Awaitable[None]]
    ) -> WebSocketRoute:
        return WebSocketRoute(path, func, name)
    return decorator