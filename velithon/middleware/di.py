from typing import Any
from velithon.datastructures import Scope, Protocol
from velithon.di import current_scope

class DIMiddleware:
    def __init__(self, app: Any, velithon: Any):
        self.app = app
        self.velithon = velithon

    async def __call__(self, scope: Scope, protocol: Protocol):
        if scope.proto != "http":
            return await self.app(scope, protocol)
        scope._di_context["velithon"] = self.velithon
        token = current_scope.set(scope)
        try:
            return await self.app(scope, protocol)
        finally:
            current_scope.reset(token)