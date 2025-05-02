class InvalidPortNumber(Exception):
    pass


class OutOfScopeApplicationException(Exception):
    pass


class DBFieldValidationError(ValueError):
    """Custom exception for field validation errors."""

    pass