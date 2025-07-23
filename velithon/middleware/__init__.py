"""Velithon Middleware Package.

This package provides middleware components for authentication, security, compression, CORS, logging, metrics, proxying, session management, and more.
All middleware classes are designed for high performance and seamless integration with the Velithon framework.
"""  # noqa: E501

import sys
from collections.abc import Iterator
from typing import Any, Protocol

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import ParamSpec
else:  # pragma: no cover
    from typing_extensions import ParamSpec

# Import middleware classes for easier discovery
from velithon.middleware.auth import AuthenticationMiddleware, SecurityMiddleware
from velithon.middleware.base import (
    BaseHTTPMiddleware,
    ConditionalMiddleware,
    PassThroughMiddleware,
    ProtocolWrapperMiddleware,
)
from velithon.middleware.compression import CompressionLevel, CompressionMiddleware
from velithon.middleware.cors import CORSMiddleware
from velithon.middleware.logging import LoggingMiddleware
from velithon.middleware.prometheus import (
    FastPrometheusMiddleware,
    PrometheusMetrics,
    PrometheusMiddleware,
    RustPrometheusMiddleware,
)
from velithon.middleware.proxy import ProxyMiddleware
from velithon.middleware.session import (
    MemorySessionInterface,
    Session,
    SessionInterface,
    SessionMiddleware,
    SignedCookieSessionInterface,
    get_session,
)
from velithon.types import RSGIApp

P = ParamSpec('P')

__all__ = [
    'AuthenticationMiddleware',
    'BaseHTTPMiddleware',
    'CORSMiddleware',
    'CompressionLevel',
    'CompressionMiddleware',
    'ConditionalMiddleware',
    'FastLoggingMiddleware',
    'FastPrometheusMiddleware',
    'LoggingMiddleware',
    'MemorySessionInterface',
    'Middleware',
    'PassThroughMiddleware',
    'PrometheusMetrics',
    'PrometheusMiddleware',
    'ProtocolWrapperMiddleware',
    'ProxyMiddleware',
    'RustLoggingMiddleware',
    'RustMiddlewareOptimizer',
    'RustPrometheusMiddleware',
    'SecurityMiddleware',
    'Session',
    'SessionInterface',
    'SessionMiddleware',
    'SignedCookieSessionInterface',
    'get_session',
]


class _MiddlewareFactory(Protocol[P]):
    def __call__(
        self, app: RSGIApp, /, *args: P.args, **kwargs: P.kwargs
    ) -> RSGIApp: ...  # pragma: no cover


class Middleware:
    """Middleware wrapper for Velithon.

    Encapsulates a middleware factory and its arguments for easy instantiation and configuration.
    Used to manage and represent middleware components within the Velithon framework.
    """  # noqa: E501

    def __init__(
        self,
        cls: _MiddlewareFactory[P],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Initialize the Middleware wrapper with a middleware factory and its arguments.

        Args:
            cls: The middleware factory class or callable.
            *args: Positional arguments to pass to the middleware factory.
            **kwargs: Keyword arguments to pass to the middleware factory.

        """  # noqa: E501
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[Any]:
        """Return an iterator over the middleware class, args, and kwargs."""
        as_tuple = (self.cls, self.args, self.kwargs)
        return iter(as_tuple)

    def __repr__(self) -> str:
        """Return a string representation of the Middleware instance."""
        class_name = self.__class__.__name__
        args_strings = [f'{value!r}' for value in self.args]
        option_strings = [f'{key}={value!r}' for key, value in self.kwargs.items()]
        name = getattr(self.cls, '__name__', '')
        args_repr = ', '.join([name, *args_strings, *option_strings])
        return f'{class_name}({args_repr})'
