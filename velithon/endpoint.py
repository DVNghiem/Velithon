from __future__ import annotations

import typing

from velithon._utils import is_async_callable
from velithon.concurrency import run_in_threadpool
from velithon.exceptions import HTTPException
from velithon.requests import Request
from velithon.responses import PlainTextResponse, Response
from velithon.types import Scope, Protocol


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

    async def dispatch(self) -> None:
        request = Request(self.scope, self.protocol)
        handler_name = "get" if request.method == "HEAD" and not hasattr(self, "head") else request.method.lower()

        handler: typing.Callable[[Request], typing.Any] = getattr(self, handler_name, self.method_not_allowed)
        is_async = is_async_callable(handler)
        if is_async:
            response = await handler(request)
        else:
            response = await run_in_threadpool(handler, request)
        await response(self.scope, self.protocol)

    async def method_not_allowed(self, request: Request) -> Response:
        # If we're running inside a velithon application then raise an
        # exception, so that the configurable exception handler can deal with
        # returning the response. For plain ASGI apps, just return the response.
        headers = {"Allow": ", ".join(self._allowed_methods)}
        if "app" in self.scope:
            raise HTTPException(status_code=405, headers=headers)
        return PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)

