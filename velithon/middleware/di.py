"""Dependency injection middleware for Velithon framework.

This module provides middleware for automatic dependency injection
in HTTP request handlers using the Velithon DI container.
"""

from typing import Any

from velithon.datastructures import Protocol, Scope
from velithon.di import current_scope
from velithon.middleware.base import BaseHTTPMiddleware


class DIMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic dependency injection in Velithon.

    This class injects the Velithon DI context into each HTTP request,
    enabling handlers to access dependencies via the DI container.
    """

    def __init__(self, app: Any, velithon: Any):
        """Initialize the DIMiddleware with the application and Velithon instance.

        Args:
            app: The RSGI application to wrap.
            velithon: The Velithon instance providing the DI container.

        """
        super().__init__(app)
        self.velithon = velithon

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Injects the Velithon DI context into the request scope and processes the HTTP request.

        Args:
            scope: The request scope containing context and metadata.
            protocol: The protocol instance for the current request.

        Returns:
            The result of the wrapped application's HTTP request processing.

        """  # noqa: E501
        scope._di_context['velithon'] = self.velithon
        token = current_scope.set(scope)
        try:
            return await self.app(scope, protocol)
        finally:
            current_scope.reset(token)
