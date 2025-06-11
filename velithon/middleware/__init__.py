#  @Copyright (c) 2025 Starlette
from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import Any, Protocol

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

# Import middleware classes for easier discovery
from velithon.middleware.base import (
    BaseHTTPMiddleware,
    ConditionalMiddleware,
    PassThroughMiddleware,
    ProtocolWrapperMiddleware,
)
from velithon.middleware.compression import CompressionLevel, CompressionMiddleware
from velithon.middleware.cors import CORSMiddleware
from velithon.middleware.logging import LoggingMiddleware
from velithon.middleware.session import (
    MemorySessionInterface,
    Session,
    SessionInterface,
    SessionMiddleware,
    SignedCookieSessionInterface,
    get_session,
)
from velithon.types import RSGIApp

P = ParamSpec("P")

__all__ = [
    "Middleware",
    "BaseHTTPMiddleware",
    "PassThroughMiddleware", 
    "ConditionalMiddleware",
    "ProtocolWrapperMiddleware",
    "CompressionMiddleware", 
    "CompressionLevel",
    "CORSMiddleware",
    "LoggingMiddleware",
    "RustLoggingMiddleware",
    "FastLoggingMiddleware",
    "RustMiddlewareOptimizer",
    "SessionMiddleware",
    "SessionInterface",
    "MemorySessionInterface",
    "SignedCookieSessionInterface",
    "Session",
    "get_session",
]


class _MiddlewareFactory(Protocol[P]):
    def __call__(self, app: RSGIApp, /, *args: P.args, **kwargs: P.kwargs) -> RSGIApp: ...  # pragma: no cover


class Middleware:
    def __init__(
        self,
        cls: _MiddlewareFactory[P],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[Any]:
        as_tuple = (self.cls, self.args, self.kwargs)
        return iter(as_tuple)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        args_strings = [f"{value!r}" for value in self.args]
        option_strings = [f"{key}={value!r}" for key, value in self.kwargs.items()]
        name = getattr(self.cls, "__name__", "")
        args_repr = ", ".join([name] + args_strings + option_strings)
        return f"{class_name}({args_repr})"
