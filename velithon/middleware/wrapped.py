from __future__ import annotations

import typing

from granian.rsgi import HTTPProtocol
from granian.rsgi import Scope as RSGIScope

from velithon.datastructures import Protocol, Scope


class WrappedRSGITypeMiddleware:
    """
    A middleware that wraps a given RSGI type middleware.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(
        self, scope: RSGIScope, protocol: HTTPProtocol
    ) -> typing.Callable:
        wrapped_scope = Scope(scope=scope)
        wrapped_protocol = Protocol(protocol=protocol)
        await self.app(wrapped_scope, wrapped_protocol)