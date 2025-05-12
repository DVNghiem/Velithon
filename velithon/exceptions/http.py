from typing import Any, Dict, Optional

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
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, error=error, details=details, headers=headers, formatter=formatter)


class UnauthorizedException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, error=error, details=details, headers=headers, formatter=formatter)


class ForbiddenException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.FORBIDDEN,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_403_FORBIDDEN, error=error, details=details, headers=headers, formatter=formatter)


class NotFoundException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_404_NOT_FOUND, error=error, details=details, headers=headers, formatter=formatter)


class ValidationException(HTTPException):
    def __init__(self, details: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, formatter: Optional[ResponseFormatter] = None):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, error=ErrorDefinitions.VALIDATION_ERROR, details=details, headers=headers, formatter=formatter)


class InternalServerException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_500_INTERNAL_SERVER_ERROR, error=error, details=details, headers=headers, formatter=formatter)


class RateLimitException(HTTPException):
    def __init__(self, retry_after: int, details: Optional[Dict[str, Any]] = None, formatter: Optional[ResponseFormatter] = None):
        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            error=ErrorDefinitions.TOO_MANY_REQUESTS,
            details=details,
            headers={"Retry-After": str(retry_after)},
            formatter=formatter,
        )

class InvalidMediaTypeException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.INVALID_MEDIA_TYPE,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE, error=error, details=details, headers=headers, formatter=formatter)

class UnsupportParameterException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.UNSUPPORT_PARAMETER_TYPE,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, error=error, details=details, headers=headers, formatter=formatter)

class MultiPartException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.SUBMIT_MULTIPART_ERROR,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, error=error, details=details, headers=headers, formatter=formatter)