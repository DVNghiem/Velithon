"""Core data structures for Velithon framework.

This module provides essential data structures for HTTP handling including
Headers, QueryParams, URL handling, and protocol interfaces.
"""

from __future__ import annotations

import typing
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit

from granian.rsgi import HTTPProtocol
from granian.rsgi import Scope as RSGIScope

from velithon._utils import RequestIDGenerator, run_in_threadpool

# Import the Rust-based UploadFile for better performance
from velithon._velithon import UploadFile
from velithon.base_datastructures import (
    MultiDictBase,
    PriorityDataStructure,
    UrlDataStructure,
)

request_id_generator = RequestIDGenerator()


class TempRequestContext:
    """Temporary request context for custom request ID generation.

    This class provides a minimal request-like interface that can be used
    by custom request ID generators to access request information.
    """

    def __init__(self, scope: RSGIScope) -> None:
        """Initialize a temporary request context with the given RSGI scope.

        Args:
            scope (RSGIScope): The RSGI scope object containing request information.

        """
        self._scope = scope

    @property
    def headers(self) -> Headers:
        """Access request headers."""
        return Headers(self._scope.headers)

    @property
    def method(self) -> str:
        """HTTP method of the request."""
        return self._scope.method

    @property
    def path(self) -> str:
        """Request path."""
        return self._scope.path

    @property
    def client(self) -> str:
        """Client address."""
        return self._scope.client

    @property
    def query_params(self) -> QueryParams:
        """Query parameters."""
        return QueryParams(self._scope.query_string)


class ResponseDataCapture:
    """Efficient response data capture with memory pooling.

    This class provides an optimized way to capture response data when needed
    by middleware, without impacting performance when not in use.

    Usage in middleware:
    ```python
    # Only enable capture when needed
    if need_to_process_response:
        protocol.enable_response_capture()

    # After response is sent, access the data
    response_data = protocol.response_data
    if response_data:
        # Process the captured response data
        for chunk in response_data:
            process_chunk(chunk)
    ```

    Performance benefits:
    - Zero memory allocation when capture is disabled (default)
    - Memory pool reduces GC pressure for enabled capture
    - Automatic cleanup prevents memory leaks
    """

    # Simple memory pool for byte buffers
    _buffer_pool: typing.ClassVar[list[list[bytes]]] = []
    _pool_max_size = 50

    def __init__(self, enabled: bool = False):
        """Initialize ResponseDataCapture.

        Args:
            enabled (bool): Whether to enable response data capture initially.

        """
        self.enabled = enabled
        self._data: list[bytes] | None = self._get_buffer() if enabled else None

    def enable(self) -> None:
        """Enable response data capture."""
        if not self.enabled:
            self.enabled = True
            self._data = self._get_buffer()

    def disable(self) -> None:
        """Disable response data capture and return buffer to pool."""
        if self.enabled and self._data is not None:
            self._return_buffer(self._data)
            self._data = None
            self.enabled = False

    def append(self, data: bytes | typing.Any) -> None:
        """Append data to the capture buffer if enabled."""
        if self.enabled and self._data is not None:
            self._data.append(data)

    def get_data(self) -> list[bytes] | None:
        """Get the captured data."""
        return self._data if self.enabled else None

    def get_response_size(self) -> int:
        """Get the size of the captured response data."""
        if self._data is None:
            return 0
        return sum(len(chunk) for chunk in self._data)

    @classmethod
    def _get_buffer(cls) -> list[bytes]:
        """Get a buffer from the pool or create a new one."""
        if cls._buffer_pool:
            return cls._buffer_pool.pop()
        return []

    @classmethod
    def _return_buffer(cls, buffer: list[bytes]) -> None:
        """Return a buffer to the pool after clearing it."""
        if len(cls._buffer_pool) < cls._pool_max_size:
            buffer.clear()
            cls._buffer_pool.append(buffer)

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.disable()


class Scope:
    """Wrapper for the RSGI scope object."""

    __slots__ = (
        '_path_params',
        '_request_id',
        '_scope',
        '_session',
    )

    def __init__(self, scope: RSGIScope) -> None:
        """Initialize a Scope wrapper for the given RSGI scope.

        Args:
            scope (RSGIScope): The RSGI scope object containing request information.

        """
        self._scope = scope
        # extend the scope with additional properties
        self._path_params = {}

        # Generate request ID using default generator for now
        # The request ID will be updated later by the context manager
        self._request_id = request_id_generator.generate()

        self._session = None

    @property
    def proto(self) -> typing.Literal['http', 'websocket']:
        """Get the protocol type of the request."""
        return self._scope.proto

    @property
    def rsgi_version(self) -> str:
        """Get the RSGI version of the request."""
        return self._scope.rsgi_version

    @property
    def http_version(self) -> str:
        """Get the HTTP version of the request."""
        return self._scope.http_version

    @property
    def server(self) -> str:
        """Get the server information."""
        return self._scope.server

    @property
    def client(self) -> str:
        """Get the client information."""
        return self._scope.client

    @property
    def scheme(self) -> str:
        """Get the scheme of the request."""
        return self._scope.scheme

    @property
    def method(self) -> str:
        """Get the HTTP method of the request."""
        return self._scope.method

    @property
    def path(self) -> str:
        """Get the path of the request."""
        return self._scope.path

    @property
    def query_string(self) -> str:
        """Get the query string of the request."""
        return self._scope.query_string

    @property
    def headers(self) -> typing.MutableMapping[str, str]:
        """Get the headers of the request."""
        return self._scope.headers

    @property
    def authority(self) -> str | None:
        """Get the authority of the request."""
        return self._scope.authority

    @property
    def path_params(self) -> typing.Mapping[str, str]:
        """Get the path parameters of the request."""
        return self._path_params


class Protocol:
    """
    Protocol abstraction for HTTP response handling in Velithon.

    This class wraps the underlying Granian HTTPProtocol, providing methods for
    sending responses, managing headers, status codes, and optionally capturing
    response data for middleware or debugging purposes.
    """

    __slots__ = (
        '_headers',
        '_protocol',
        '_response_capture',
        '_status_code',
    )

    def __init__(
        self, protocol: HTTPProtocol, capture_response_data: bool = False
    ) -> None:
        """Initialize the Protocol wrapper."""
        self._protocol = protocol
        self._status_code = 200
        self._headers = []
        self._response_capture = ResponseDataCapture(capture_response_data)

    @property
    def response_data(self) -> list[bytes] | None:
        """Get captured response data. Returns None if capture is disabled."""
        return self._response_capture.get_data()

    @property
    def status_code(self) -> int:
        """Get the current response status code."""
        return self._status_code

    def enable_response_capture(self) -> None:
        """Enable response data capture. Should be called before any response methods."""  # noqa: E501
        self._response_capture.enable()

    def disable_response_capture(self) -> None:
        """Disable response data capture and clear any captured data."""
        self._response_capture.disable()

    async def __call__(self, *args, **kwds) -> bytes:
        """Call the underlying protocol with the given arguments."""
        return await self._protocol(*args, **kwds)

    def __aiter__(self) -> typing.AsyncIterator[bytes]:
        """Return an async iterator for the protocol."""
        return self._protocol.__aiter__()

    async def client_disconnect(self) -> None:
        """Handle client disconnection."""
        await self._protocol.client_disconnect()

    def update_headers(self, headers: list[tuple[str, str]]) -> None:
        """Update the response headers with the given list of tuples."""
        self._headers.extend(headers)

    def response_empty(self, status: int, headers: tuple[str, str]) -> None:
        """Send an empty response with the given status and headers."""
        self._status_code = status
        self._headers.extend(headers)
        self._protocol.response_empty(status, self._headers)
        self._response_capture.append(b'')

    def response_str(self, status: int, headers: tuple[str, str], body: str) -> None:
        """Send a string response with the given status, headers, and body."""
        self._status_code = status
        self._headers.extend(headers)
        self._protocol.response_str(status, self._headers, body)
        self._response_capture.append(body.encode('utf-8'))

    def response_bytes(
        self, status: int, headers: tuple[str, str], body: bytes
    ) -> None:
        """Send a bytes response with the given status, headers, and body."""
        self._status_code = status
        self._headers.extend(headers)
        self._protocol.response_bytes(status, self._headers, body)
        self._response_capture.append(body)

    def response_file(
        self, status: int, headers: tuple[str, str], file: typing.Any
    ) -> None:
        """Send a file response with the given status, headers, and file object."""
        self._status_code = status
        self._headers.extend(headers)
        self._protocol.response_file(status, self._headers, file)
        self._response_capture.append(file)

    def response_stream(self, status: int, headers: tuple[str, str]) -> typing.Any:
        """Start a streaming response with the given status and headers."""
        self._status_code = status
        self._headers.extend(headers)
        return self._protocol.response_stream(status, self._headers)


class Address(typing.NamedTuple):
    """Represents a network address."""

    host: str
    port: int


_KeyType = typing.TypeVar('_KeyType')
# Mapping keys are invariant but their values are covariant since
# you can only read them
# that is, you can't do `Mapping[str, Animal]()["fido"] = Dog()`
_CovariantValueType = typing.TypeVar('_CovariantValueType', covariant=True)


class URL(UrlDataStructure):
    """Represents and manipulates URLs within the Velithon framework.

    This class provides properties and methods for parsing, constructing, and
    modifying URLs, supporting both direct string input and construction from
    request scope or components.
    """

    def __init__(
        self,
        url: str = '',
        scope: Scope | None = None,
        **components: typing.Any,
    ) -> None:
        """Initialize a URL object with a string, Scope, or components.

        Args:
            url (str): The URL string.
            scope (Scope | None): Optional Scope object to construct the URL from request context.
            **components: Arbitrary URL components for dynamic construction.

        Raises:
            AssertionError: If both 'url' and 'scope' or 'url' and '**components' are provided.

        """  # noqa: E501
        if scope is not None:
            assert not url, 'Cannot set both "url" and "scope".'
            assert not components, 'Cannot set both "scope" and "**components".'
            scheme = scope.scheme
            server = scope.server
            path = scope.path
            query_string = scope.query_string

            host_header = None
            for key, value in scope.headers.items():
                if key == b'host':
                    host_header = value.decode('latin-1')
                    break

            if host_header is not None:
                url = f'{scheme}://{host_header}{path}'
            elif server is None:
                url = path
            else:
                host, port = server.split(':')
                default_port = {'http': 80, 'https': 443, 'ws': 80, 'wss': 443}[scheme]
                if port == default_port:
                    url = f'{scheme}://{host}{path}'
                else:
                    url = f'{scheme}://{host}:{port}{path}'

            if query_string:
                url += '?' + query_string
        elif components:
            assert not url, 'Cannot set both "url" and "**components".'
            url = URL('').replace(**components).components.geturl()

        self._url = url

    @property
    def components(self) -> SplitResult:
        """Parse the URL into its components."""
        if not hasattr(self, '_components'):
            self._components = urlsplit(self._url)
        return self._components

    @property
    def scheme(self) -> str:
        """Get the scheme of the URL."""
        return self.components.scheme

    @property
    def netloc(self) -> str:
        """Get the network location of the URL."""
        return self.components.netloc

    @property
    def path(self) -> str:
        """Get the path of the URL."""
        return self.components.path

    @property
    def query(self) -> str:
        """Get the query string of the URL."""
        return self.components.query

    @property
    def fragment(self) -> str:
        """Get the fragment identifier of the URL."""
        return self.components.fragment

    @property
    def username(self) -> None | str:
        """Get the username of the URL."""
        return self.components.username

    @property
    def password(self) -> None | str:
        """Get the password of the URL."""
        return self.components.password

    @property
    def hostname(self) -> None | str:
        """Get the hostname of the URL."""
        return self.components.hostname

    @property
    def port(self) -> int | None:
        """Get the port of the URL."""
        return self.components.port

    @property
    def is_secure(self) -> bool:
        """Check if the URL is secure."""
        return self.scheme in ('https', 'wss')

    def replace(self, **kwargs: typing.Any) -> URL:
        """Replace components of the URL with new values."""
        if (
            'username' in kwargs
            or 'password' in kwargs
            or 'hostname' in kwargs
            or 'port' in kwargs
        ):
            hostname = kwargs.pop('hostname', None)
            port = kwargs.pop('port', self.port)
            username = kwargs.pop('username', self.username)
            password = kwargs.pop('password', self.password)

            if hostname is None:
                netloc = self.netloc
                _, _, hostname = netloc.rpartition('@')

                if hostname[-1] != ']':
                    hostname = hostname.rsplit(':', 1)[0]

            netloc = hostname
            if port is not None:
                netloc += f':{port}'
            if username is not None:
                userpass = username
                if password is not None:
                    userpass += f':{password}'
                netloc = f'{userpass}@{netloc}'

            kwargs['netloc'] = netloc

        components = self.components._replace(**kwargs)
        return self.__class__(components.geturl())

    def _get_url_string(self) -> str:
        """Return the URL as a string."""
        return self._url

    def _get_repr_attrs(self) -> dict[str, typing.Any]:
        """Return attributes to include in __repr__."""
        # URL repr is handled by UrlDataStructure base class
        # This method is required but not used for URL representation
        return {'url': str(self)}


class URLPath(str):
    """A URL path string that may also hold an associated protocol and/or host.

    Used by the routing to return `url_path_for` matches.
    """

    def __new__(cls, path: str, protocol: str = '', host: str = '') -> URLPath:
        assert protocol in ('http', 'websocket', '')
        return str.__new__(cls, path)

    def __init__(self, path: str, protocol: str = '', host: str = '') -> None:
        self.protocol = protocol
        self.host = host

    def make_absolute_url(self, base_url: str | URL) -> URL:
        if isinstance(base_url, str):
            base_url = URL(base_url)
        if self.protocol:
            scheme = {
                'http': {True: 'https', False: 'http'},
                'websocket': {True: 'wss', False: 'ws'},
            }[self.protocol][base_url.is_secure]
        else:
            scheme = base_url.scheme

        netloc = self.host or base_url.netloc
        path = base_url.path.rstrip('/') + str(self)
        return URL(scheme=scheme, netloc=netloc, path=path)


class ImmutableMultiDict(MultiDictBase, typing.Mapping[_KeyType, _CovariantValueType]):
    _dict: dict[_KeyType, _CovariantValueType]

    def __init__(
        self,
        *args: ImmutableMultiDict[_KeyType, _CovariantValueType]
        | typing.Mapping[_KeyType, _CovariantValueType]
        | typing.Iterable[tuple[_KeyType, _CovariantValueType]],
        **kwargs: typing.Any,
    ) -> None:
        assert len(args) < 2, 'Too many arguments.'

        value: typing.Any = args[0] if args else []
        if kwargs:
            value = (
                ImmutableMultiDict(value).multi_items()
                + ImmutableMultiDict(kwargs).multi_items()
            )

        if not value:
            _items: list[tuple[typing.Any, typing.Any]] = []
        elif hasattr(value, 'multi_items'):
            value = typing.cast(
                ImmutableMultiDict[_KeyType, _CovariantValueType], value
            )
            _items = list(value.multi_items())
        elif hasattr(value, 'items'):
            value = typing.cast(typing.Mapping[_KeyType, _CovariantValueType], value)
            _items = list(value.items())
        else:
            value = typing.cast('list[tuple[typing.Any, typing.Any]]', value)
            _items = list(value)

        self._dict = dict(_items)
        self._list = _items

    def getlist(self, key: typing.Any) -> list[_CovariantValueType]:
        return [item_value for item_key, item_value in self._list if item_key == key]

    def keys(self) -> typing.KeysView[_KeyType]:
        return self._dict.keys()

    def values(self) -> typing.ValuesView[_CovariantValueType]:
        return self._dict.values()

    def items(self) -> typing.ItemsView[_KeyType, _CovariantValueType]:
        return self._dict.items()

    def multi_items(self) -> list[tuple[_KeyType, _CovariantValueType]]:
        return list(self._list)

    def __getitem__(self, key: _KeyType) -> _CovariantValueType:
        return self._dict[key]

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._dict

    def __iter__(self) -> typing.Iterator[_KeyType]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._dict)


class MultiDict(ImmutableMultiDict[typing.Any, typing.Any]):
    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        self.setlist(key, [value])

    def __delitem__(self, key: typing.Any) -> None:
        self._list = [(k, v) for k, v in self._list if k != key]
        del self._dict[key]

    def pop(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        self._list = [(k, v) for k, v in self._list if k != key]
        return self._dict.pop(key, default)

    def popitem(self) -> tuple[typing.Any, typing.Any]:
        key, value = self._dict.popitem()
        self._list = [(k, v) for k, v in self._list if k != key]
        return key, value

    def poplist(self, key: typing.Any) -> list[typing.Any]:
        values = [v for k, v in self._list if k == key]
        self.pop(key)
        return values

    def clear(self) -> None:
        self._dict.clear()
        self._list.clear()

    def setdefault(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        if key not in self:
            self._dict[key] = default
            self._list.append((key, default))

        return self[key]

    def setlist(self, key: typing.Any, values: list[typing.Any]) -> None:
        if not values:
            self.pop(key, None)
        else:
            existing_items = [(k, v) for (k, v) in self._list if k != key]
            self._list = existing_items + [(key, value) for value in values]
            self._dict[key] = values[-1]

    def append(self, key: typing.Any, value: typing.Any) -> None:
        self._list.append((key, value))
        self._dict[key] = value

    def update(
        self,
        *args: MultiDict
        | typing.Mapping[typing.Any, typing.Any]
        | list[tuple[typing.Any, typing.Any]],
        **kwargs: typing.Any,
    ) -> None:
        value = MultiDict(*args, **kwargs)
        existing_items = [(k, v) for (k, v) in self._list if k not in value.keys()]
        self._list = existing_items + value.multi_items()
        self._dict.update(value)


class QueryParams(ImmutableMultiDict[str, str]):
    """An immutable multidict."""

    def __init__(
        self,
        *args: ImmutableMultiDict[typing.Any, typing.Any]
        | typing.Mapping[typing.Any, typing.Any]
        | list[tuple[typing.Any, typing.Any]]
        | str
        | bytes,
        **kwargs: typing.Any,
    ) -> None:
        """Initialize QueryParams with a string, bytes, or other iterable."""
        assert len(args) < 2, 'Too many arguments.'

        value = args[0] if args else []

        if isinstance(value, str):
            super().__init__(parse_qsl(value, keep_blank_values=True), **kwargs)
        elif isinstance(value, bytes):
            super().__init__(
                parse_qsl(value.decode('latin-1'), keep_blank_values=True), **kwargs
            )
        else:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._list = [(str(k), str(v)) for k, v in self._list]
        self._dict = {str(k): str(v) for k, v in self._dict.items()}

    def __str__(self) -> str:
        """Return the query parameters as a URL-encoded string."""
        return urlencode(self._list)

    # UploadFile is now implemented in Rust for better performance
    # Import it from the _velithon module instead

    def _get_repr_attrs(self) -> dict[str, typing.Any]:
        """Return attributes to include in __repr__."""
        return {'filename': self.filename, 'size': self.size, 'headers': self.headers}


class FormData(ImmutableMultiDict[str, typing.Union[UploadFile, str]]):
    """An immutable multidict, containing both file uploads and text input."""

    def __init__(
        self,
        *args: FormData
        | typing.Mapping[str, str | UploadFile]
        | list[tuple[str, str | UploadFile]],
        **kwargs: str | UploadFile,
    ) -> None:
        """Initialize FormData with a mapping or iterable of key-value pairs."""
        super().__init__(*args, **kwargs)

    async def close(self) -> None:
        """Close all UploadFile instances in the FormData."""
        for _, value in self.multi_items():
            if isinstance(value, UploadFile):
                # Rust UploadFile has synchronous close method
                value.close()


class Headers(MultiDictBase, typing.Mapping[str, str]):
    """An immutable, case-insensitive multidict."""

    def __init__(
        self,
        headers: list[tuple[str, str]] | None = None,
        scope: Scope | None = None,
    ) -> None:
        """Initialize Headers with a list of tuples or from a Scope object."""
        self._list: list[tuple[str, str]] = []
        if headers is not None:
            assert scope is None, 'Cannot set both "headers" and "scope".'
            self._list = headers
        elif scope is not None:
            self._list = scope.headers.items()

    @property
    def raw(self) -> list[tuple[str, str]]:
        """Return the raw headers as a list of tuples."""
        return list(self._list)

    def keys(self) -> list[str]:  # type: ignore[override]
        """Return the keys of the headers, case-insensitive."""
        return [key for key, value in self._list]

    def values(self) -> list[str]:  # type: ignore[override]
        """Return the values of the headers, case-insensitive."""
        return [value for key, value in self._list]

    def items(self) -> list[tuple[str, str]]:  # type: ignore[override]
        """Return the items of the headers as a list of tuples."""
        return [(key, value) for key, value in self._list]

    def __getitem__(self, key: str) -> str:
        """Get the value for the given header key, case-insensitive."""
        get_header_key = key.lower()
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return header_value
        raise KeyError(key)

    def __contains__(self, key: typing.Any) -> bool:
        """Check if the header key exists, case-insensitive."""
        get_header_key = key.lower()
        for header_key, _header_value in self._list:
            if header_key == get_header_key:
                return True
        return False

    def __iter__(self) -> typing.Iterator[typing.Any]:
        """Return an iterator over the header keys, case-insensitive."""
        return iter(self.keys())

    def __len__(self) -> int:
        """Return the number of unique header keys."""
        return len(self._list)

    def __setitem__(self, key: str, value: str) -> None:
        """Set the header `key` to `value`, removing any duplicate entries.

        Retains insertion order.
        """
        key = key.lower()

        found_indexes: list[int] = []
        for idx, (item_key, _item_value) in enumerate(self._list):
            if item_key == key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (key, value)
        else:
            self._list.append((key, value))


class FunctionInfo(PriorityDataStructure):
    """A data structure to hold information about a function call."""

    __slots__ = ('args', 'func', 'is_async', 'kwargs', 'priority')

    def __init__(
        self,
        func: typing.Callable[..., typing.Any],
        args: tuple[typing.Any, ...] | None = None,
        kwargs: dict[str, typing.Any] | None = None,
        is_async: bool = False,
        priority: int = 0,
    ):
        """Initialize FunctionInfo with function, arguments, async flag, and priority.

        Args:
            func (Callable): The function to be called.
            args (tuple, optional): Arguments for the function.
            kwargs (dict, optional): Keyword arguments for the function.
            is_async (bool, optional): Whether the function is asynchronous.
            priority (int, optional): Priority value for sorting or execution.

        """
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.is_async = is_async
        self.priority = priority

    def _get_hash_key(self) -> typing.Any:
        """Return the key used for hashing this object."""
        return (
            self.func,
            self.args,
            frozenset(self.kwargs.items()),
            self.is_async,
            self.priority,
        )

    def _get_repr_attrs(self) -> dict[str, typing.Any]:
        """Return attributes to include in __repr__."""
        return {
            'func': self.func,
            'args': self.args,
            'kwargs': self.kwargs,
            'is_async': self.is_async,
            'priority': self.priority,
        }

    def __hash__(self) -> int:
        """Return a hash of the function info based on its attributes."""
        return hash(self._get_hash_key())

    def __call__(self):
        """Call the function with its arguments and keyword arguments."""
        if self.is_async:
            return self.func(*self.args, **self.kwargs)
        else:
            return run_in_threadpool(self.func, *self.args, **self.kwargs)


# Export all public classes and functions
__all__ = [
    'URL',
    'Address',
    'FormData',
    'FunctionInfo',
    'Headers',
    'Protocol',
    'QueryParams',
    'ResponseDataCapture',
    'Scope',
    'UploadFile',
]
