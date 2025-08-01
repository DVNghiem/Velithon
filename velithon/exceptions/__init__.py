"""Velithon exceptions package.

This package provides exception classes, error definitions, and response formatters
used throughout the Velithon framework for robust error handling and reporting.
"""

from .base import HTTPException, ResponseFormatter, VelithonError
from .errors import ErrorDefinitions
from .formatters import DetailedFormatter, LocalizedFormatter, SimpleFormatter
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
    'DetailedFormatter',
    'ErrorDefinitions',
    'ForbiddenException',
    'HTTPException',
    'InternalServerException',
    'InvalidMediaTypeException',
    'LocalizedFormatter',
    'MultiPartException',
    'NotFoundException',
    'RateLimitException',
    'ResponseFormatter',
    'SimpleFormatter',
    'UnauthorizedException',
    'UnsupportParameterException',
    'ValidationException',
    'VelithonError',
]
