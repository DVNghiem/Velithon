"""Base exception classes and formatters for Velithon framework.

This module provides abstract base classes for exception handling, response
formatting, and common exception functionality across the framework.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from velithon.status import HTTP_400_BAD_REQUEST


class ResponseFormatter(ABC):
    """Abstract base class for formatting exceptions into response dictionaries.

    Implementations should provide a method to convert HTTPException instances
    into structured response data for the Velithon framework.
    """

    @abstractmethod
    def format_error(self, exception: 'HTTPException') -> dict[str, Any]:
        """Format exception into response dictionary."""
        pass


class DefaultFormatter(ResponseFormatter):
    """Default implementation of ResponseFormatter for Velithon exceptions.

    Formats HTTPException instances into structured response dictionaries
    with error details, status code, and timestamp.
    """

    def format_error(self, exception: 'HTTPException') -> dict[str, Any]:
        """Format an HTTPException into a structured response dictionary.

        Args:
            exception (HTTPException): The exception instance to format.

        Returns:
            dict[str, Any]: A dictionary containing error details, status code, and timestamp.

        """  # noqa: E501
        return {
            'error': {
                'code': exception.error.code if exception.error else 'UNKNOWN_ERROR',
                'message': exception.error.message
                if exception.error
                else 'Unknown error occurred',
                'details': exception.details or {},
                'timestamp': datetime.now(tz=timezone.utc).isoformat(),
            },
            'status': exception.status_code,
        }


class VelithonError:
    """Base error definition."""

    def __init__(self, message: str, code: str):
        """Initialize a VelithonError with a message and error code.

        Args:
            message (str): The error message.
            code (str): The error code.

        """
        self.message = message
        self.code = code


class HTTPException(Exception):
    """Base HTTP exception."""

    _formatter: ResponseFormatter = DefaultFormatter()

    @classmethod
    def set_formatter(cls, formatter: ResponseFormatter) -> None:
        """Set the response formatter for HTTPException class.

        Args:
            formatter (ResponseFormatter): The formatter to use for formatting exceptions.

        """  # noqa: E501
        cls._formatter = formatter

    def __init__(
        self,
        status_code: int = HTTP_400_BAD_REQUEST,
        error: VelithonError | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        """Initialize an HTTPException with status code, error, details, headers, and optional formatter.

        Args:
            status_code (int): HTTP status code for the exception.
            error (VelithonError | None): Optional VelithonError instance describing the error.
            details (dict[str, Any] | None): Optional dictionary with additional error details.
            headers (dict[str, str] | None): Optional dictionary of HTTP headers.
            formatter (ResponseFormatter | None): Optional custom response formatter for this exception.

        """  # noqa: E501
        self.status_code = status_code
        self.error = error
        self.details = details or {}
        self.headers = headers or {}
        self._instance_formatter = formatter

    def to_dict(self) -> dict[str, Any]:
        """Convert the HTTPException instance into a structured response dictionary.

        Returns:
            dict[str, Any]: A dictionary containing formatted error details and status code.

        """  # noqa: E501
        formatter = self._instance_formatter or self._formatter
        return formatter.format_error(self)
