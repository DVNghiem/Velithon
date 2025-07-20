"""Request context middleware for Velithon framework.

This middleware manages application and request contexts, and handles custom request ID generation.
"""

from velithon.ctx import AppContext, RequestContext, RequestIDManager
from velithon.datastructures import Protocol, Scope, _TempRequestContext
from velithon.middleware.base import BaseHTTPMiddleware


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that manages request context and handles custom request ID generation.
    
    This middleware:
    1. Creates application and request contexts
    2. Handles custom request ID generation
    3. Provides context management
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.request_id_manager = RequestIDManager(app)
    
    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request with context management."""
        
        # Create a temporary request context for request ID generation
        temp_request = _TempRequestContext(scope._scope)
        
        # Generate custom request ID if configured
        if hasattr(self.app, 'request_id_generator') and self.app.request_id_generator:
            custom_request_id = self.app.request_id_generator(temp_request)
            scope._request_id = custom_request_id
        
        # Create application context
        with AppContext(self.app):
            # Create a full request object for the request context
            from velithon.requests import Request
            request = Request(scope, protocol)
            
            # Create request context
            with RequestContext(self.app, request):
                # Process the request
                await self.app(scope, protocol)
