from http import HTTPStatus
from typing import Any, Dict, Optional

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
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, error=error, details=details, headers=headers, formatter=formatter)


class UnauthorizedException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTPStatus.UNAUTHORIZED, error=error, details=details, headers=headers, formatter=formatter)


class ForbiddenException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.FORBIDDEN,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTPStatus.FORBIDDEN, error=error, details=details, headers=headers, formatter=formatter)


class NotFoundException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, error=error, details=details, headers=headers, formatter=formatter)


class ValidationException(HTTPException):
    def __init__(self, details: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, formatter: Optional[ResponseFormatter] = None):
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, error=ErrorDefinitions.VALIDATION_ERROR, details=details, headers=headers, formatter=formatter)


class InternalServerException(HTTPException):
    def __init__(
        self,
        error: Optional[VelithonError] = ErrorDefinitions.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        super().__init__(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, error=error, details=details, headers=headers, formatter=formatter)


class RateLimitException(HTTPException):
    def __init__(self, retry_after: int, details: Optional[Dict[str, Any]] = None, formatter: Optional[ResponseFormatter] = None):
        super().__init__(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            error=ErrorDefinitions.TOO_MANY_REQUESTS,
            details=details,
            headers={"Retry-After": str(retry_after)},
            formatter=formatter,
        )