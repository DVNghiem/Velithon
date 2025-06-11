from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from velithon.status import HTTP_400_BAD_REQUEST


class ResponseFormatter(ABC):
    @abstractmethod
    def format_error(self, exception: "HTTPException") -> Dict[str, Any]:
        """Format exception into response dictionary"""
        pass


class DefaultFormatter(ResponseFormatter):
    def format_error(self, exception: "HTTPException") -> Dict[str, Any]:
        return {
            "error": {
                "code": exception.error.code if exception.error else "UNKNOWN_ERROR",
                "message": exception.error.message
                if exception.error
                else "Unknown error occurred",
                "details": exception.details or {},
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
            "status": exception.status_code,
        }


class VelithonError:
    """Base error definition"""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code


class HTTPException(Exception):
    """Base HTTP exception"""

    _formatter: ResponseFormatter = DefaultFormatter()

    @classmethod
    def set_formatter(cls, formatter: ResponseFormatter) -> None:
        cls._formatter = formatter

    def __init__(
        self,
        status_code: int = HTTP_400_BAD_REQUEST,
        error: Optional[VelithonError] = None,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[ResponseFormatter] = None,
    ):
        self.status_code = status_code
        self.error = error
        self.details = details or {}
        self.headers = headers or {}
        self._instance_formatter = formatter

    def to_dict(self) -> Dict[str, Any]:
        formatter = self._instance_formatter or self._formatter
        return formatter.format_error(self)
