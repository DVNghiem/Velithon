"""Logging middleware for HTTP request/response logging in Velithon framework.

This module provides middleware for comprehensive HTTP request and response
logging with performance metrics and error tracking.
"""

import time
import traceback

from velithon.datastructures import Protocol, Scope
from velithon.exceptions import HTTPException
from velithon.logging import get_logger
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.responses import JSONResponse

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses in Velithon.

    This middleware logs request details, response status, and processing time.
    It also handles exceptions and logs error details if an exception occurs.
    """

    def __init__(self, app):
        """Initialize the logging middleware with the given application.

        Args:
            app: The next RSGI application in the middleware chain.

        """
        super().__init__(app)
        self._logger = get_logger(__name__)

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request and log details including performance metrics."""
        # Check if logging is enabled at INFO level first to avoid timing calculations
        # if we're not going to log anything
        if not self._logger.isEnabledFor(20):  # INFO level = 20
            return await self.app(scope, protocol)

        start_time = time.time()
        request_id = scope._request_id
        client_ip = scope.client
        method = scope.method
        path = scope.path
        user_agent = scope.headers.get('user-agent', '')
        status_code = 200

        try:
            await self.app(scope, protocol)
            duration_ms = (time.time() - start_time) * 1000
        except Exception as e:
            if self._logger.isEnabledFor(10):  # DEBUG level = 10
                traceback.print_exc()
            duration_ms = (time.time() - start_time) * 1000
            status_code = 500
            if isinstance(e, HTTPException):
                status_code = e.status_code
                error_msg = e.to_dict()
            else:
                error_msg = {
                    'message': str(e),
                    'error_code': 'INTERNAL_SERVER_ERROR',
                }
            response = JSONResponse(
                content=error_msg,
                status_code=status_code,
            )
            await response(scope, protocol)

        # Use a single log statement with pre-built extra dict
        extra = {
            'request_id': request_id,
            'method': method,
            'user_agent': user_agent,
            'path': path,
            'client_ip': client_ip,
            'duration_ms': str(round(duration_ms, 2)),  # Convert to string for Rust
            'status': str(status_code),  # Convert to string for Rust
        }
        self._logger.info('Processed %s %s', method, path, extra=extra)
