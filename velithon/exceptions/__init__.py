"""Velithon exceptions and error handling module.

This module provides comprehensive error handling capabilities including
HTTP exceptions, response formatters, and custom validation error formatters.
"""

from .base import HTTPException, ResponseFormatter, VelithonError
from .errors import ErrorDefinitions
from .formatters import DetailedFormatter, LocalizedFormatter, SimpleFormatter
from .validation_formatters import (
    ValidationErrorFormatter,
    DefaultValidationErrorFormatter,
    SimpleValidationErrorFormatter,
    DetailedValidationErrorFormatter,
    JSONSchemaValidationErrorFormatter,
)
from .http import (
    BadRequestException,
    ForbiddenException,
    InternalServerException,
    InvalidMediaTypeException,
    MultiPartException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    UnsupportParameterException,
    ValidationException,
)

__all__ = [
    'BadRequestException',
    'DefaultValidationErrorFormatter',
    'DetailedFormatter',
    'DetailedValidationErrorFormatter',
    'ErrorDefinitions',
    'ForbiddenException',
    'HTTPException',
    'InternalServerException',
    'InvalidMediaTypeException',
    'JSONSchemaValidationErrorFormatter',
    'LocalizedFormatter',
    'MultiPartException',
    'NotFoundException',
    'RateLimitException',
    'ResponseFormatter',
    'SimpleFormatter',
    'SimpleValidationErrorFormatter',
    'UnauthorizedException',
    'UnsupportParameterException',
    'ValidationErrorFormatter',
    'ValidationException',
    'VelithonError',
]
