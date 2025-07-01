"""Authentication middleware for Velithon framework."""

import typing
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

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the wrapped protocol."""
        return getattr(self.protocol, name)

    def __aiter__(self) -> typing.AsyncIterator[bytes]:
        """Delegate async iteration to the wrapped protocol."""
        return self.protocol.__aiter__()

    async def __call__(self, *args, **kwds) -> bytes:
        """Delegate call to the wrapped protocol."""
        return await self.protocol(*args, **kwds)

    async def client_disconnect(self) -> None:
        """Delegate client disconnect to the wrapped protocol."""
        await self.protocol.client_disconnect()

    def update_headers(self, headers: list[tuple[str, str]]) -> None:
        """Delegate header updates to the wrapped protocol."""
        self.protocol.update_headers(headers)

    def response_empty(self, status: int, headers: tuple[str, str]) -> None:
        """Handle empty response, adding security headers if needed."""
        headers = self._add_security_headers(headers)
        return self.protocol.response_empty(status, headers)

    def response_str(self, status: int, headers: tuple[str, str], body: str) -> None:
        """Handle string response, adding security headers if needed."""
        headers = self._add_security_headers(headers)
        return self.protocol.response_str(status, headers, body)

    def response_bytes(
        self,
        status: int,
        headers: list[tuple[str, str]],
        body: bytes | memoryview,
    ) -> None:
        """Handle response, adding security headers if needed."""
        headers = self._add_security_headers(headers)
        return self.protocol.response_bytes(status, headers, body)

    def response_file(
        self, status: int, headers: tuple[str, str], file: typing.Any
    ) -> None:
        """Handle file response, adding security headers if needed."""
        headers = self._add_security_headers(headers)
        return self.protocol.response_file(status, headers, file)

    def response_stream(self, status: int, headers: tuple[str, str]) -> typing.Any:
        """Handle stream response, adding security headers if needed."""
        headers = self._add_security_headers(headers)
        return self.protocol.response_stream(status, headers)

    async def response_start(self, status: int, headers: list[tuple[str, str]]) -> None:
        """Handle response start for streaming responses."""
        headers = self._add_security_headers(headers)
        return await self.protocol.response_start(status, headers)

    def _add_security_headers(
        self,
        headers: tuple[str, str] | list[tuple[str, str]]
    ) -> tuple[str, str] | list[tuple[str, str]]:
        """Add security headers to response headers."""
        if not self.middleware.add_security_headers:
            return headers

        # Convert to list if needed
        if isinstance(headers, tuple):
            headers_list = list(headers)
        else:
            headers_list = headers

        # Add security headers
        security_headers = [
            (name, value)
            for name, value in self.middleware.security_headers.items()
        ]
        headers_list.extend(security_headers)

        # Return in the same format as input
        if isinstance(headers, tuple):
            return tuple(headers_list)
        else:
            return headers_list
