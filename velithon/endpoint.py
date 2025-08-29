"""HTTP endpoint base classes for Velithon framework.

This module provides HTTPEndpoint base class for creating structured HTTP
endpoints with automatic parameter dispatching and response handling.
"""

from __future__ import annotations

import typing

from velithon.ctx import get_or_create_request, has_request_context
from velithon.datastructures import Protocol, Scope
from velithon.params.dispatcher import dispatch
from velithon.requests import Request
from velithon.responses import JSONResponse, Response


class HTTPEndpoint:
    """
    Base class for HTTP endpoints in the Velithon framework.

    Attributes
    ----------
    scope : Scope
        The ASGI scope for the request.
    protocol : Protocol
        The protocol instance for communication.

    """

    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        """
        Initialize an HTTPEndpoint instance with the given ASGI scope and protocol.

        Parameters
        ----------
        scope : Scope
            The ASGI scope for the request.
        protocol : Protocol
            The protocol instance for communication.

        """
        assert scope.proto == 'http'
        self.scope = scope
        self.protocol = protocol
        self._allowed_methods = [
            method
            for method in ('GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS')
            if getattr(self, method.lower(), None) is not None
        ]

    def __await__(self) -> typing.Generator[typing.Any, None, None]:
        """
        Awaitable method to handle the endpoint dispatching.

        This method is called when the endpoint is awaited in an async context.
        """
        return self.dispatch().__await__()

    async def dispatch(self) -> Response:
        """Use singleton request pattern - try to get from context first."""
        if has_request_context():
            request = get_or_create_request(self.scope, self.protocol)
        else:
            # Create new request if no context exists
            request = Request(self.scope, self.protocol)

        handler_name = (
            'get'
            if request.method == 'HEAD' and not hasattr(self, 'head')
            else request.method.lower()
        )
        handler: typing.Callable[[Request], typing.Any] = getattr(  # type: ignore
            self, handler_name, self.method_not_allowed
        )
        response = await dispatch(handler, request)
        await response(self.scope, self.protocol)

    def method_not_allowed(self, request: Request) -> Response:
        """Handle method not allowed responses."""
        return JSONResponse(
            content={'message': 'Method Not Allowed', 'error_code': 'METHOD_NOT_ALLOW'},
            status_code=405,
            headers={'Allow': ', '.join(self._allowed_methods)},
        )
