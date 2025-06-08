from typing import Any

from velithon.datastructures import Protocol, Scope
from velithon.di import current_scope
from velithon.middleware.base import BaseHTTPMiddleware


class DIMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, velithon: Any):
        super().__init__(app)
        self.velithon = velithon

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        scope._di_context["velithon"] = self.velithon
        token = current_scope.set(scope)
        try:
            return await self.app(scope, protocol)
        finally:
            current_scope.reset(token)
