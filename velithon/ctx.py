"""Context management system for Velithon framework.

This module provides context management with application and request contexts,
allowing for clean separation of concerns and proper context isolation across requests.
"""

import contextvars
import typing
from typing import Any, Callable, Optional

if typing.TYPE_CHECKING:
    from velithon.application import Velithon
    from velithon.datastructures import Protocol, Scope
    from velithon.requests import Request


# Context variables for thread-local storage
_app_ctx_stack: contextvars.ContextVar = contextvars.ContextVar(
    'app_ctx_stack', default=None
)
_request_ctx_stack: contextvars.ContextVar = contextvars.ContextVar(
    'request_ctx_stack', default=None
)


class AppContext:
    """Application context for Velithon applications.

    This holds application-level
    information that needs to be accessible during request processing.
    """

    def __init__(self, app: 'Velithon') -> None:
        """Initialize the AppContext with the given Velithon application.

        Args:
            app (Velithon): The Velithon application instance.

        """
        self.app = app
        self._token: Optional[contextvars.Token] = None

    def __enter__(self) -> 'AppContext':
        """Enter the application context."""
        self._token = _app_ctx_stack.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the application context and reset the context variable.

        This method is called when exiting the context manager and ensures
        the application context variable is properly reset.
        """
        if self._token is not None:
            _app_ctx_stack.reset(self._token)
            self._token = None

    async def __aenter__(self) -> 'AppContext':
        """Async context manager entry - non-blocking."""
        self._token = _app_ctx_stack.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - non-blocking cleanup."""
        if self._token is not None:
            _app_ctx_stack.reset(self._token)
            self._token = None


class RequestContext:
    """Request context for Velithon requests.

    This holds request-specific information that needs 
        to be accessible during request processing.
    Implements singleton pattern for Request objects 
        to ensure only one instance per request.
    """

    def __init__(self, app: 'Velithon', request: 'Request') -> None:
        """Initialize the RequestContext with the given application and request.

        Args:
            app (Velithon): The Velithon application instance.
            request (Request): The current request object.

        """
        self.app = app
        self.request = request
        self._token: Optional[contextvars.Token] = None

        # Additional context data that can be set during request processing
        self.g = SimpleNamespace()

    @classmethod
    def create_with_singleton_request(
        cls, app: 'Velithon', scope: 'Scope', protocol: 'Protocol'
    ) -> 'RequestContext':
        """Create a RequestContext with a singleton Request object.

        This method ensures that only one Request instance is created per request context.
        """  # noqa: E501
        from velithon.requests import Request

        request = Request(scope, protocol)
        return cls(app, request)

    def __enter__(self) -> 'RequestContext':
        """Enter the request context."""
        self._token = _request_ctx_stack.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the request context and reset the context variable.

        This method is called when exiting the context manager and ensures
        the request context variable is properly reset.
        """
        if self._token is not None:
            _request_ctx_stack.reset(self._token)
            self._token = None

    async def __aenter__(self) -> 'RequestContext':
        """Async context manager entry - non-blocking."""
        self._token = _request_ctx_stack.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - non-blocking cleanup."""
        if self._token is not None:
            _request_ctx_stack.reset(self._token)
            self._token = None


class SimpleNamespace:
    """Simple namespace for storing arbitrary data."""

    def __init__(self, **kwargs):
        """Initialize the SimpleNamespace with arbitrary keyword arguments.

        Args:
            **kwargs: Arbitrary keyword arguments to set as attributes.

        """
        self.__dict__.update(kwargs)

    def __repr__(self) -> str:
        """Return a string representation of the SimpleNamespace object."""
        keys = sorted(self.__dict__)
        items = (f'{k}={self.__dict__[k]!r}' for k in keys)
        return '{}({})'.format(type(self).__name__, ', '.join(items))


class LocalProxy:
    """A proxy object that forwards all operations to a context-local object."""

    def __init__(self, local: Callable[[], Any], name: Optional[str] = None) -> None:
        """Initialize the LocalProxy with a callable to retrieve the context-local object.

        Args:
            local (Callable[[], Any]): A callable that returns the context-local object.
            name (Optional[str]): Optional name for the proxy object.

        """  # noqa: E501
        object.__setattr__(self, '_LocalProxy__local', local)
        object.__setattr__(self, '__name__', name)

    def _get_current_object(self) -> Any:
        """Return the current object this proxy points to."""
        return self._LocalProxy__local()

    def __getattr__(self, name: str) -> Any:
        """Return the attribute of the proxied context-local object."""
        return getattr(self._get_current_object(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute on the proxied context-local object."""
        setattr(self._get_current_object(), name, value)

    def __delattr__(self, name: str) -> None:
        """Delete an attribute from the proxied context-local object."""
        delattr(self._get_current_object(), name)

    def __str__(self) -> str:
        """Return a string representation of the proxied context-local object."""
        return str(self._get_current_object())

    def __repr__(self) -> str:
        """Return a string representation of the proxied context-local object."""
        return repr(self._get_current_object())

    def __bool__(self) -> bool:
        """Return True if the proxied context-local object is truthy."""
        return bool(self._get_current_object())

    def __len__(self) -> int:
        """Return the length of the proxied context-local object if it supports len()."""  # noqa: E501
        return len(self._get_current_object())

    def __getitem__(self, key: Any) -> Any:
        """Return an item from the proxied context-local object."""
        return self._get_current_object()[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        """Set an item on the proxied context-local object."""
        self._get_current_object()[key] = value

    def __delitem__(self, key: Any) -> None:
        """Delete an item from the proxied context-local object."""
        del self._get_current_object()[key]

    def __call__(self, *args, **kwargs) -> Any:
        """Call the proxied context-local object as a function."""
        return self._get_current_object()(*args, **kwargs)


def _lookup_app_object(name: str) -> Any:
    """Lookup an object in the current application context."""
    ctx = _app_ctx_stack.get()
    if ctx is None:
        raise RuntimeError(
            'Working outside of application context. This typically means '
            'that you attempted to use functionality that needed to interface '
            'with the current application object in some way.'
        )
    return getattr(ctx, name)


def _lookup_req_object(name: str) -> Any:
    """Lookup an object in the current request context."""
    ctx = _request_ctx_stack.get()
    if ctx is None:
        raise RuntimeError(
            'Working outside of request context. This typically means that '
            'you attempted to use functionality that needed an active HTTP '
            'request.'
        )
    return getattr(ctx, name)


def get_current_app() -> 'Velithon':
    """Return the current application instance."""
    return _lookup_app_object('app')


def get_current_request() -> 'Request':
    """Return the current request object."""
    return _lookup_req_object('request')


def get_or_create_request(scope: 'Scope', protocol: 'Protocol') -> 'Request':
    """Get request from context or create new one as singleton.

    This ensures that only one Request instance exists per request context,
    implementing the singleton pattern for better memory efficiency.
    """
    try:
        # Try to get existing request from context first
        return get_current_request()
    except RuntimeError:
        # No request context exists, create new request
        from velithon.requests import Request

        return Request(scope, protocol)


def has_app_context() -> bool:
    """Check if we're currently in an application context."""
    return _app_ctx_stack.get() is not None


def has_request_context() -> bool:
    """Check if we're currently in a request context."""
    return _request_ctx_stack.get() is not None


# Proxy objects for convenient access to current app and request
current_app: 'Velithon' = LocalProxy(get_current_app, name='current_app')
request: 'Request' = LocalProxy(get_current_request, name='request')
g: SimpleNamespace = LocalProxy(lambda: _lookup_req_object('g'), name='g')


__all__ = [
    'AppContext',
    'LocalProxy',
    'RequestContext',
    'RequestIDManager',
    'SimpleNamespace',
    'copy_current_app_context',
    'copy_current_request_context',
    'current_app',
    'g',
    'get_current_app',
    'get_current_request',
    'get_or_create_request',
    'has_app_context',
    'has_request_context',
    'request',
]


class RequestIDManager:
    """Manager for request ID generation with context awareness."""

    def __init__(self, app: 'Velithon') -> None:
        """Initialize the RequestIDManager with the given Velithon application.

        Args:
            app (Velithon): The Velithon application instance.

        """
        self.app = app
        self._default_generator = None

    def generate_request_id(self, request_context: Any) -> str:
        """Generate a request ID using the configured generator."""
        if self.app.request_id_generator:
            return self.app.request_id_generator(request_context)

        # Use default generator
        if self._default_generator is None:
            from velithon._utils import RequestIDGenerator

            self._default_generator = RequestIDGenerator()

        return self._default_generator.generate()

    def set_request_id(self, request_id: str) -> None:
        """Set the request ID in the current request context."""
        if has_request_context():
            ctx = _request_ctx_stack.get()
            if ctx and hasattr(ctx.request, '_request_id'):
                ctx.request._request_id = request_id


def copy_current_app_context() -> AppContext:
    """Copy the current application context."""
    ctx = _app_ctx_stack.get()
    if ctx is None:
        raise RuntimeError('No application context to copy')
    return AppContext(ctx.app)


def copy_current_request_context() -> RequestContext:
    """Copy the current request context."""
    ctx = _request_ctx_stack.get()
    if ctx is None:
        raise RuntimeError('No request context to copy')
    return RequestContext(ctx.app, ctx.request)
