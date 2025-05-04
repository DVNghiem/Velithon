import logging
import time

from velithon.datastructures import Protocol, Scope
from velithon.requests import Request
from velithon.responses import JSONResponse

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, protocol: Protocol):
        request = Request(scope, protocol)
        start_time = time.time()
        request_id = request.request_id
        client_ip = request.scope.client
        query_params = request.query_params
        method = request.method
        path = request.url.path

        logger.info(
            "Received %s %s",
            method,
            path,
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "query_params": query_params._dict,
                "headers": dict(request.headers),
            },
        )
        try:
            await self.app(scope, protocol)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Processed %s %s",
                method,
                path,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "duration_ms": round(duration_ms, 2),
                    "status": protocol._status_code,
                },
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                "Error processing %s %s",
                method,
                path,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "duration_ms": round(duration_ms, 2),
                    "status": protocol._status_code or 500,
                },
            )
            response = JSONResponse(
                content={"message": str(e), "error_code": "INTERNAL_SERVER_ERROR"},
                status_code=500,
            )
            await response(scope, protocol)
            raise e
