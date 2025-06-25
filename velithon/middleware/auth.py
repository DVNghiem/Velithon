"""Authentication middleware for Velithon framework."""

from typing import Any

from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.responses import JSONResponse
from velithon.security.exceptions import AuthenticationError, AuthorizationError


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware that handles security exceptions."""

    def __init__(self, app: Any):
        """Initialize authentication middleware with app instance."""
        super().__init__(app)

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process HTTP request and handle authentication errors."""
        try:
            await self.app(scope, protocol)
        except AuthenticationError as e:
            response = JSONResponse(
                content={
                    "error": "Authentication Failed",
                    "detail": str(e),
                    "type": "authentication_error"
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
            await response(scope, protocol)
        except AuthorizationError as e:
            response = JSONResponse(
                content={
                    "error": "Authorization Failed",
                    "detail": str(e),
                    "type": "authorization_error"
                },
                status_code=403
            )
            await response(scope, protocol)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware that adds security headers and handles global security."""

    def __init__(
        self,
        app: Any,
        *,
        add_security_headers: bool = True,
        cors_enabled: bool = False,
        **kwargs: Any
    ):
        """Initialize security middleware with configuration options."""
        super().__init__(app)
        self.add_security_headers = add_security_headers
        self.cors_enabled = cors_enabled
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        """Process request and add security headers to response."""
        # Create a wrapped protocol that adds security headers
        wrapped_protocol = SecurityProtocol(protocol, self)
        await self.app(scope, wrapped_protocol)


class SecurityProtocol:
    """Protocol wrapper that adds security headers to responses."""

    def __init__(self, protocol: Protocol, middleware: SecurityMiddleware):
        """Initialize security protocol wrapper."""
        self.protocol = protocol
        self.middleware = middleware
        self._response_sent = False

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the wrapped protocol."""
        return getattr(self.protocol, name)

    def response_bytes(
        self,
        status: int,
        headers: list[tuple[str, str]],
        body: bytes | memoryview,
    ) -> None:
        """Handle response, adding security headers if needed."""
        if not self._response_sent:
            self._response_sent = True

            if self.middleware.add_security_headers:
                # Add security headers
                security_headers = [
                    (name.encode(), value.encode())
                    for name, value in self.middleware.security_headers.items()
                ]
                headers.extend(security_headers)

        return self.protocol.response_bytes(status, headers, body)

    async def response_start(self, status: int, headers: list[tuple[str, str]]) -> None:
        """Handle response start for streaming responses."""
        if not self._response_sent:
            self._response_sent = True

            if self.middleware.add_security_headers:
                # Add security headers
                security_headers = [
                    (name.encode(), value.encode())
                    for name, value in self.middleware.security_headers.items()
                ]
                headers.extend(security_headers)

        return await self.protocol.response_start(status, headers)
