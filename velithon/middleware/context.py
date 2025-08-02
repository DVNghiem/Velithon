"""Request context middleware for Velithon framework.

This middleware manages application and request contexts, and handles custom request ID generation.
"""  # noqa: E501

from velithon.ctx import AppContext, RequestContext, RequestIDManager
from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.requests import Request


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that manages request context and handles custom request ID generation.

    This middleware:
    1. Creates application and request contexts
    2. Handles custom request ID generation
    3. Provides context management
    """

    def __init__(self, app, velithon_app=None):
        """Initialize the middleware with the given application and optional Velithon app."""  # noqa: E501
        super().__init__(app)
        # Use app as velithon_app if not provided (common case for tests)
        self.velithon_app = velithon_app or app
        self.request_id_manager = RequestIDManager(self.velithon_app)

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request with async context management for optimal performance."""  # noqa: E501
        # Generate custom request ID if configured
        if (
            hasattr(self.velithon_app, 'request_id_generator')
            and self.velithon_app.request_id_generator
        ):
            request = Request(scope, protocol)
            custom_request_id = self.velithon_app.request_id_generator(request)
            scope._request_id = custom_request_id

        # Use async context managers for non-blocking context management
        async with AppContext(self.velithon_app):
            # Use the singleton request context creation method
            request_context = RequestContext.create_with_singleton_request(
                self.velithon_app, scope, protocol
            )
            async with request_context:
                # Process the request
                await self.app(scope, protocol)
