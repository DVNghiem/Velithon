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
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.BAD_REQUEST,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class UnauthorizedException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.UNAUTHORIZED,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_401_UNAUTHORIZED,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class ForbiddenException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.FORBIDDEN,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_403_FORBIDDEN,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class NotFoundException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.NOT_FOUND,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class ValidationException(HTTPException):
    def __init__(
        self,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=ErrorDefinitions.VALIDATION_ERROR,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class InternalServerException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class RateLimitException(HTTPException):
    def __init__(
        self,
        retry_after: int,
        details: dict[str, Any] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            error=ErrorDefinitions.TOO_MANY_REQUESTS,
            details=details,
            headers={'Retry-After': str(retry_after)},
            formatter=formatter,
        )


class InvalidMediaTypeException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.INVALID_MEDIA_TYPE,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class UnsupportParameterException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.UNSUPPORT_PARAMETER_TYPE,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )


class MultiPartException(HTTPException):
    def __init__(
        self,
        error: VelithonError | None = ErrorDefinitions.SUBMIT_MULTIPART_ERROR,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        formatter: ResponseFormatter | None = None,
    ):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error=error,
            details=details,
            headers=headers,
            formatter=formatter,
        )
