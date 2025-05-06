import logging
import time
import traceback

from velithon.datastructures import Protocol, Scope
from velithon.exceptions import HTTPException
from velithon.responses import JSONResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, protocol: Protocol):
        start_time = time.time()
        request_id = scope.request_id
        client_ip = scope.client
        method = scope.method
        path = scope.path
        headers = scope.headers.items()
        status_code = 200
        message = "Processed %s %s"

        try:
            await self.app(scope, protocol)
            duration_ms = (time.time() - start_time) * 1000
        except Exception as e:
            if logger.level == logging.DEBUG:
                traceback.print_exc()
            duration_ms = (time.time() - start_time) * 1000
            error_msg = ""
            status_code = 500
            if isinstance(e, HTTPException):
                error_msg = e.to_dict()
                status_code = e.status_code
            else:
                error_msg = {
                    "message": str(e),
                    "error_code": "INTERNAL_SERVER_ERROR",
                }
            response = JSONResponse(
                content=error_msg,
                status_code=500,
            )
            await response(scope, protocol)
        logger.info(
            message,
            method,
            path,
            extra={
                "request_id": request_id,
                "method": method,
                "headers": headers,
                "path": path,
                "client_ip": client_ip,
                "duration_ms": round(duration_ms, 5),
                "status": status_code,
            },
        )
