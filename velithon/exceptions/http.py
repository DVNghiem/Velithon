"""HTTP exception classes for Velithon framework.

This module provides specific HTTP exception classes for various HTTP status
codes including client errors, server errors, and authentication exceptions.
"""

from typing import Any

from velithon.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from .base import HTTPException, ResponseFormatter, VelithonError
from .errors import ErrorDefinitions


class BadRequestException(HTTPException):
    """Exception raised for HTTP 400 Bad Request errors.

    This exception is used when the client sends a malformed or invalid request.
    It allows customization of error details, headers, and response formatting.
    """  # noqa

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.BAD_REQUEST,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize BadRequestException with optional error, details, headers, and formatter.

        Args:
            error (VelithonError | None): The error definition for the exception.
            details (dict[str, Any] | None): Additional details about the error.
            headers (dict[str, str] | None): Optional HTTP headers for the response.
            formatter (ResponseFormatter | None): Optional response formatter.

        """  # noqa: E501
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class UnauthorizedException(HTTPException):
    """Exception raised for HTTP 401 Unauthorized errors.

    This exception is used when authentication is required and has failed or has
    not yet been provided.
    It allows customization of error details, headers, and response formatting.
    """

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.UNAUTHORIZED,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize UnauthorizedException with optional error, details, headers, and formatter.

        This exception is used when authentication is required and has failed or has
        not yet been provided.
        """  # noqa

        super().__init__(
            status_code=HTTP_401_UNAUTHORIZED,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class ForbiddenException(HTTPException):
    """Exception raised for HTTP 403 Forbidden errors.

    This exception is used when the client does not have permission to access the requested resource.
    It allows customization of error details, headers, and response formatting.
    """  # noqa: E501

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.FORBIDDEN,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize ForbiddenException for HTTP 403 Forbidden errors.

        Args:
            error (VelithonError | None): The error definition for the exception.
            details (dict[str, Any] | None): Additional details about the error.
            headers (dict[str, str] | None): Optional HTTP headers for the response.
            formatter (ResponseFormatter | None): Optional response formatter.

        """
        super().__init__(
            status_code=HTTP_403_FORBIDDEN,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class NotFoundException(HTTPException):
    """Exception raised for HTTP 404 Not Found errors.

    This exception is used when the requested resource could not be found.
    It allows customization of error details, headers, and response formatting.
    """  # noqa

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.NOT_FOUND,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize NotFoundException with optional error, details, headers, and formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class ValidationException(HTTPException):
    """Exception raised for HTTP 400 Bad Request errors due to validation issues.

    This exception is used when the request data does not meet validation criteria.
    """

    def __init__(
        self,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize ValidationException with optional details, headers, and formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=ErrorDefinitions.VALIDATION_ERROR,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class InternalServerException(HTTPException):
    """Exception raised for HTTP 500 Internal Server Error."""

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize InternalServerException with optional error, details, headers, and formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class RateLimitException(HTTPException):
    """Exception raised for HTTP 429 Too Many Requests errors."""

    def __init__(
        self,
        retry_after: int,
        details: dict[str, Any] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize RateLimitException with retry_after, details, and optional formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            error=ErrorDefinitions.TOO_MANY_REQUESTS,
            details=details,
            headers={'Retry-After': str(retry_after)},
            formatter=formatter,
        )


class InvalidMediaTypeException(HTTPException):
    """Exception raised for HTTP 415 Unsupported Media Type errors."""

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.INVALID_MEDIA_TYPE,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize InvalidMediaTypeException with optional error, details, headers, and formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class UnsupportParameterException(HTTPException):
    """Exception raised for HTTP 400 Bad Request errors due to unsupported parameter types."""  # noqa: E501

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.UNSUPPORT_PARAMETER_TYPE,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize UnsupportParameterException with optional error, details, headers, and formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class MultiPartException(HTTPException):
    """Exception raised for HTTP 400 Bad Request errors due to multipart submission issues."""  # noqa: E501

    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.SUBMIT_MULTIPART_ERROR,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize MultiPartException with optional error, details, headers, and formatter."""  # noqa: E501
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )
