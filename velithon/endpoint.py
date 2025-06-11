from __future__ import annotations

import typing

from velithon.datastructures import Protocol, Scope
from velithon.params.dispatcher import dispatch
from velithon.requests import Request
from velithon.responses import JSONResponse, Response


class HTTPEndpoint:
    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        assert scope.proto == "http"
        self.scope = scope
        self.protocol = protocol
        self._allowed_methods = [
            method
            for method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            if getattr(self, method.lower(), None) is not None
        ]

    def __await__(self) -> typing.Generator[typing.Any, None, None]:
        return self.dispatch().__await__()

    async def dispatch(self) -> Response:
        request = Request(self.scope, self.protocol)
        handler_name = (
            "get"
            if request.method == "HEAD" and not hasattr(self, "head")
            else request.method.lower()
        )
        handler: typing.Callable[[Request], typing.Any] = getattr(  # type: ignore
            self, handler_name, self.method_not_allowed
        )
        response = await dispatch(handler, request)
        await response(self.scope, self.protocol)


    def method_not_allowed(self, request: Request) -> Response:
        return JSONResponse(
            content={"message": "Method Not Allowed", "error_code": "METHOD_NOT_ALLOW"},
            status_code=405,
            headers={"Allow": ", ".join(self._allowed_methods)},
        )
