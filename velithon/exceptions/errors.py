from .base import VelithonError


class ErrorDefinitions:
    """Standard error definitions"""

    BAD_REQUEST = VelithonError(message="Bad request", code="BAD_REQUEST")
    UNAUTHORIZED = VelithonError(message="Unauthorized access", code="UNAUTHORIZED")
    FORBIDDEN = VelithonError(message="Access forbidden", code="FORBIDDEN")
    NOT_FOUND = VelithonError(message="Resource not found", code="NOT_FOUND")
    METHOD_NOT_ALLOWED = VelithonError(message="Method not allowed", code="METHOD_NOT_ALLOWED")
    VALIDATION_ERROR = VelithonError(message="Validation error", code="VALIDATION_ERROR")
    INTERNAL_ERROR = VelithonError(message="Internal server error", code="INTERNAL_SERVER_ERROR")
    CONFLICT = VelithonError(message="Resource conflict", code="CONFLICT")
    TOO_MANY_REQUESTS = VelithonError(message="Too many requests", code="TOO_MANY_REQUESTS")