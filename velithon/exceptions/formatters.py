"""Response formatters for HTTP exceptions in Velithon framework.

This module provides various response formatters for HTTP exceptions including
JSON API, RFC7807 Problem Details, and debug formatters.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from .base import HTTPException, ResponseFormatter


class SimpleFormatter(ResponseFormatter):
    """A simple response formatter for HTTP exceptions.

    Returns a minimal error response containing only the error code and message.
    """

    def format_error(self, exception: HTTPException) -> dict[str, Any]:
        """Format an HTTPException into a minimal error response.

        Args:
            exception (HTTPException): The exception to format.

        Returns:
            dict[str, Any]: The formatted error response containing code and message.

        """
        return {
            'code': exception.error.code if exception.error else 'UNKNOWN_ERROR',
            'message': exception.error.message
            if exception.error
            else 'Unknown error occurred',
        }


class DetailedFormatter(ResponseFormatter):
    """A detailed response formatter for HTTP exceptions.

    Returns a comprehensive error response including status, error details,
    timestamp, and request information.
    """

    def format_error(self, exception: HTTPException) -> dict[str, Any]:
        """Format an HTTPException into a detailed error response.

        Returns a dictionary containing status, error details,
            timestamp, and request info.

        Args:
            exception (HTTPException): The exception to format.

        Returns:
            dict[str, Any]: The formatted error response.

        """
        return {
            'status': {
                'code': exception.status_code,
                'text': str(exception.status_code),
            },
            'error': {
                'type': exception.error.code if exception.error else 'UNKNOWN_ERROR',
                'message': exception.error.message
                if exception.error
                else 'Unknown error occurred',
                'details': exception.details or {},
                'timestamp': datetime.now(timezone.utc).isoformat(),
            },
            'request': {'path': exception.path, 'id': str(uuid.uuid4())},
        }


class LocalizedFormatter(ResponseFormatter):
    """A response formatter that provides localized error messages.

    This formatter translates error codes into human-readable messages
    based on the specified language.

    Attributes:
        language (str): The language code for localization.
        translations (dict): Mapping of error codes to localized messages.

    """

    def __init__(self, language: str = 'en'):
        """Initialize the LocalizedFormatter with a specified language.

        Args:
            language (str): The language code for localization (default is 'en').

        """
        self.language = language
        self.translations = {
            'en': {
                'BAD_REQUEST': 'Bad request',
                'VALIDATION_ERROR': 'Validation error',
                'NOT_FOUND': 'Resource not found',
                # Add more translations
            },
            'vi': {
                'BAD_REQUEST': 'Yêu cầu không hợp lệ',
                'VALIDATION_ERROR': 'Lỗi xác thực',
                'NOT_FOUND': 'Không tìm thấy tài nguyên',
                # Add more translations
            },
        }

    def format_error(self, exception: HTTPException) -> dict[str, Any]:
        """Format an HTTPException into a localized error response.

        Args:
            exception (HTTPException): The exception to format.

        Returns:
            dict[str, Any]: The formatted error response with localized message.

        """
        error_code = exception.error.code if exception.error else 'UNKNOWN_ERROR'
        translated_message = self.translations.get(self.language, {}).get(
            error_code,
            exception.error.message if exception.error else 'Unknown error occurred',
        )

        return {
            'error': {
                'code': error_code,
                'message': translated_message,
                'details': exception.details or {},
            },
            'status': exception.status_code,
            'timestamp': datetime.now(tz=timezone.utc).isoformat(),
        }
