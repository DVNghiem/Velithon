import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from .base import HTTPException, ResponseFormatter


class SimpleFormatter(ResponseFormatter):
    def format_error(self, exception: HTTPException) -> Dict[str, Any]:
        return {
            "code": exception.error.code if exception.error else "UNKNOWN_ERROR",
            "message": exception.error.message if exception.error else "Unknown error occurred",
        }


class DetailedFormatter(ResponseFormatter):
    def format_error(self, exception: HTTPException) -> Dict[str, Any]:
        return {
            "status": {"code": exception.status_code, "text": str(exception.status_code)},
            "error": {
                "type": exception.error.code if exception.error else "UNKNOWN_ERROR",
                "message": exception.error.message if exception.error else "Unknown error occurred",
                "details": exception.details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "request": {"path": exception.path, "id": str(uuid.uuid4())},
        }


class LocalizedFormatter(ResponseFormatter):
    def __init__(self, language: str = "en"):
        self.language = language
        self.translations = {
            "en": {
                "BAD_REQUEST": "Bad request",
                "VALIDATION_ERROR": "Validation error",
                "NOT_FOUND": "Resource not found",
                # Add more translations
            },
            "vi": {
                "BAD_REQUEST": "Yêu cầu không hợp lệ",
                "VALIDATION_ERROR": "Lỗi xác thực",
                "NOT_FOUND": "Không tìm thấy tài nguyên",
                # Add more translations
            },
        }

    def format_error(self, exception: HTTPException) -> Dict[str, Any]:
        error_code = exception.error.code if exception.error else "UNKNOWN_ERROR"
        translated_message = self.translations.get(self.language, {}).get(error_code, exception.error.message if exception.error else "Unknown error occurred")

        return {
            "error": {"code": error_code, "message": translated_message, "details": exception.details or {}},
            "status": exception.status_code,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }