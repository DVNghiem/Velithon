"""Security exceptions for Velithon authentication system."""

from velithon.exceptions import HTTPException, VelithonError
from velithon.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN


class SecurityError(HTTPException):
    """Base security exception."""

    def __init__(
        self,
        message: str = "Security error",
        status_code: int = HTTP_401_UNAUTHORIZED,
        headers: dict[str, str] | None = None,
    ):
        """Initialize security error.

        Args:
            message: Error message
            status_code: HTTP status code
            headers: Optional HTTP headers

        """
        error = VelithonError(message=message, code="SECURITY_ERROR")
        super().__init__(
            status_code=status_code,
            error=error,
            headers=headers
        )


class AuthenticationError(SecurityError):
    """Authentication failed exception."""

    def __init__(
        self,
        message: str = "Authentication failed",
        headers: dict[str, str] | None = None,
    ):
        """Initialize authentication error.

        Args:
            message: Error message
            headers: Optional HTTP headers

        """
        super().__init__(
            message=message,
            status_code=HTTP_401_UNAUTHORIZED,
            headers=headers
        )


class AuthorizationError(SecurityError):
    """Authorization failed exception."""

    def __init__(self, message: str = "Insufficient permissions"):
        """Initialize authorization error.

        Args:
            message: Error message

        """
        super().__init__(
            message=message,
            status_code=HTTP_403_FORBIDDEN
        )


class TokenExpiredError(AuthenticationError):
    """Token has expired exception."""

    def __init__(self, message: str = "Token has expired"):
        """Initialize token expired error.

        Args:
            message: Error message

        """
        super().__init__(message=message)


class InvalidTokenError(AuthenticationError):
    """Invalid token exception."""

    def __init__(self, message: str = "Invalid token"):
        """Initialize invalid token error.

        Args:
            message: Error message

        """
        super().__init__(message=message)


class MissingTokenError(AuthenticationError):
    """Missing token exception."""

    def __init__(self, message: str = "Missing authentication token"):
        """Initialize missing token error.

        Args:
            message: Error message

        """
        super().__init__(
            message=message,
            headers={"WWW-Authenticate": "Bearer"}
        )
