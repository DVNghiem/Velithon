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
        self._logger = logging.getLogger(__name__)

    async def __call__(self, scope: Scope, protocol: Protocol):
        # Check if logging is enabled at INFO level first to avoid timing calculations
        # if we're not going to log anything
        if not self._logger.isEnabledFor(logging.INFO):
            return await self.app(scope, protocol)

        start_time = time.time()
        request_id = scope._request_id
        client_ip = scope.client
        method = scope.method
        path = scope.path
        user_agent = scope.headers.get("user-agent", "")
        status_code = 200

        try:
            await self.app(scope, protocol)
            duration_ms = (time.time() - start_time) * 1000
        except Exception as e:
            if self._logger.isEnabledFor(logging.DEBUG):
                traceback.print_exc()
            duration_ms = (time.time() - start_time) * 1000
            status_code = 500
            if isinstance(e, HTTPException):
                status_code = e.status_code
                error_msg = e.to_dict()
            else:
                error_msg = {
                    "message": str(e),
                    "error_code": "INTERNAL_SERVER_ERROR",
                }
            response = JSONResponse(
                content=error_msg,
                status_code=status_code,
            )
            await response(scope, protocol)

        # Use a single log statement with pre-built extra dict
        extra = {
            "request_id": request_id,
            "method": method,
            "user_agent": user_agent,
            "path": path,
            "client_ip": client_ip,
            "duration_ms": round(duration_ms, 2),  # Round to 2 decimal places is usually sufficient
            "status": status_code,
        }
        self._logger.info("Processed %s %s", method, path, extra=extra)
