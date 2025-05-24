import logging
import time
import traceback
from typing import Optional

from velithon.datastructures import Protocol, Scope
from velithon.exceptions import HTTPException
from velithon.responses import JSONResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self, app, enable_performance_logging: bool = True):
        self.app = app
        self.enable_performance_logging = enable_performance_logging
        self.is_debug = logger.isEnabledFor(logging.DEBUG)

    async def __call__(self, scope: Scope, protocol: Protocol):
        # Only measure time if performance logging is enabled
        start_time = time.perf_counter() if self.enable_performance_logging else 0
        status_code = 200
        error_msg: Optional[dict] = None

        try:
            await self.app(scope, protocol)
        except Exception as e:
            # Only print traceback in debug mode (check once at init for better performance)
            if self.is_debug:
                traceback.print_exc()
            
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
                status_code=status_code,  # Use correct status code
            )
            await response(scope, protocol)

        # Fast path: only log if performance logging is enabled
        if self.enable_performance_logging:
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Use format strings for better performance
            logger.info(
                "Processed %s %s",
                scope.method,
                scope.path,
                extra={
                    "request_id": scope._request_id,
                    "method": scope.method,
                    "user_agent": scope.headers.get("user-agent", ""),
                    "path": scope.path,
                    "client_ip": scope.client,
                    "duration_ms": round(duration_ms, 3),  # Less precision for better performance
                    "status": status_code,
                },
            )
