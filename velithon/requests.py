"""HTTP request handling for Velithon framework.

This module provides Request class for handling HTTP requests, including
body parsing, header management, and parameter extraction.
"""

from __future__ import annotations

import typing
from http import cookies as http_cookies

import orjson

from velithon._velithon import parse_options_header
from velithon.datastructures import (
    URL,
    Address,
    FormData,
    Headers,
    Protocol,
    QueryParams,
    Scope,
    UploadFile,
)
from velithon.formparsers import FormParser, MultiPartException, MultiPartParser

T_co = typing.TypeVar('T_co', covariant=True)


class AwaitableOrContextManager(
    typing.Awaitable[T_co], typing.AsyncContextManager[T_co], typing.Protocol[T_co]
):
    """Protocol for objects that are both awaitable and async context managers.

    This is used to type objects that can be awaited or used in an async with statement.
    """

    ...


class SupportsAsyncClose(typing.Protocol):
    """Protocol for objects that support asynchronous close operations.

    Classes implementing this protocol must provide an async close() method.
    """

    async def close(self) -> None:
        """Asynchronously close the connection or resource.

        This method should be implemented to release any resources or perform cleanup
        when the object is no longer needed.
        """
        ... 

SupportsAsyncCloseType = typing.TypeVar(
    'SupportsAsyncCloseType', bound=SupportsAsyncClose, covariant=False
)


class AwaitableOrContextManagerWrapper(typing.Generic[SupportsAsyncCloseType]):
    """
    Wraps an awaitable object to provide both await and async context manager capabilities.

    This class allows an awaitable object that supports asynchronous closing to be used
    with 'await' or 'async with' syntax, ensuring proper resource cleanup.
    """  # noqa: E501

    __slots__ = ('aw', 'entered')

    def __init__(self, aw: typing.Awaitable[SupportsAsyncCloseType]) -> None:
        """Initialize the wrapper with an awaitable object."""
        self.aw = aw

    def __await__(self) -> typing.Generator[typing.Any, None, SupportsAsyncCloseType]:
        """Await the wrapped awaitable object."""
        return self.aw.__await__()

    async def __aenter__(self) -> SupportsAsyncCloseType:
        """Enter the async context manager, awaiting the wrapped object."""
        self.entered = await self.aw
        return self.entered

    async def __aexit__(self, *args: typing.Any) -> None | bool:
        """Exit the async context manager, closing the entered object."""
        await self.entered.close()
        return None


def cookie_parser(cookie_string: str) -> dict[str, str]:
    """Parse a ``Cookie`` HTTP header into a dict of key/value pairs.

    It attempts to mimic browser cookie parsing behavior: browsers and web servers
    frequently disregard the spec (RFC 6265) when setting and reading cookies,
    so we attempt to suit the common scenarios here.

    This function has been adapted from Django 3.1.0.
    Note: we are explicitly _NOT_ using `SimpleCookie.load` because it is based
    on an outdated spec and will fail on lots of input we want to support
    """
    cookie_dict: dict[str, str] = {}
    for chunk in cookie_string.split(';'):
        if '=' in chunk:
            key, val = chunk.split('=', 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = '', chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookie_dict[key] = http_cookies._unquote(val)
    return cookie_dict


class HTTPConnection(typing.Mapping[str, typing.Any]):
    """A base class for incoming HTTP connections, that is used to provide.

    any functionality that is common to both `Request` and `WebSocket`.
    """

    __slots__ = ('protocol', 'scope')

    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        """Initialize the HTTPConnection with scope and protocol."""
        assert scope.proto in ('http', 'websocket')
        self.scope = scope
        self.protocol = protocol

    def __getitem__(self, key: str) -> typing.Any:
        """Get an item from the scope by key."""
        return self.scope[key]

    def __iter__(self) -> typing.Iterator[str]:
        """Return an iterator over the keys in the scope."""
        return iter(self.scope)

    def __len__(self) -> int:
        """Return the number of items in the scope."""
        return len(self.scope)

    # Don't use the `abc.Mapping.__eq__` implementation.
    # Connection instances should never be considered equal
    # unless `self is other`.
    __eq__ = object.__eq__
    __hash__ = object.__hash__

    @property
    def url(self) -> URL:
        """Return the URL object for this connection."""
        if not hasattr(self, '_url'):  # pragma: no branch
            self._url = URL(scope=self.scope)
        return self._url

    @property
    def headers(self) -> Headers:
        """Return the headers for this connection as a Headers object."""
        if not hasattr(self, '_headers'):
            self._headers = Headers(headers=self.scope.headers.items())
        return self._headers

    @property
    def query_params(self) -> QueryParams:
        """Return the query parameters for this connection as a QueryParams object.

        This property parses the query string from the scope and returns a QueryParams instance
        representing all query parameters included in the request URL.
        """  # noqa: E501
        if not hasattr(self, '_query_params'):  # pragma: no branch
            self._query_params = QueryParams(self.scope.query_string)
        return self._query_params

    @property
    def path_params(self) -> dict[str, typing.Any]:
        """Return the path parameters extracted from the request URL.

        This property provides a dictionary of path parameters parsed from the route,
        allowing access to dynamic segments defined in the URL pattern.
        """
        return self.scope.path_params

    @property
    def cookies(self) -> dict[str, str]:
        """Return the cookies sent by the client as a dictionary.

        This property parses the 'Cookie' HTTP header and returns a dictionary
        of cookie key-value pairs provided by the client.
        """
        if not hasattr(self, '_cookies'):
            cookies: dict[str, str] = {}
            cookie_header = self.headers.get('cookie')

            if cookie_header:
                cookies = cookie_parser(cookie_header)
            self._cookies = cookies
        return self._cookies

    @property
    def client(self) -> Address | None:
        """Return the client address as an Address object or None if missing.

        This property parses the client information from the scope and returns
        an Address instance containing the host and port, or None if unavailable.
        """
        # client is a 2 item tuple of (host, port), None if missing
        client_info = self.scope.get('client')
        if client_info and ':' in client_info:
            try:
                host, port = client_info.rsplit(':', 1)
                return Address(host, int(port))
            except (ValueError, TypeError):
                pass
        return None


class Request(HTTPConnection):
    """Represents an HTTP request in the Velithon framework.

    This class provides methods and properties for accessing request data,
    including headers, cookies, query parameters, body, form data, files,
    and session information. It extends HTTPConnection to offer additional
    request-specific functionality.
    """

    _form: FormData | None

    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        """Initialize a Request instance with the given scope and protocol.

        Args:
            scope (Scope): The ASGI scope containing request information.
            protocol (Protocol): The protocol handler for the request.

        """
        super().__init__(scope, protocol)
        assert scope.proto == 'http'
        self._form = None

    @property
    def request_id(self) -> str:
        """Return the unique request ID for this HTTP request.

        This property provides the identifier assigned to the request, which can be used
        for tracing, logging, or correlation purposes.
        """
        return self.scope._request_id

    @property
    def method(self) -> str:
        """Return the HTTP method used for this request.

        This property provides the HTTP method (e.g., 'GET', 'POST', etc.) of the incoming request.
        """  # noqa: E501
        return self.scope.method

    @property
    def session(self) -> typing.Any:
        """Access session data. Returns empty dict if session middleware not enabled."""
        if hasattr(self.scope, '_session'):
            return self.scope._session
        # Return empty dict-like object if session middleware is not enabled
        from velithon.middleware.session import Session

        return Session()

    async def stream(self) -> typing.AsyncGenerator[bytes, None]:
        """Asynchronously yield chunks of the request body.

        This method provides an async generator that yields bytes objects representing
        the incoming request body data as it is received from the client.
        """
        async for chunk in self.protocol:
            yield chunk

    async def body(self, max_size: int = 1024 * 1024 * 16) -> bytes:
        """Asynchronously read and return the entire request body as bytes.

        This method collects all chunks from the request stream and returns the complete body.
        """  # noqa: E501
        if not hasattr(self, '_body'):
            chunks: list[bytes] = []
            total_size = 0
            async for chunk in self.stream():
                total_size += len(chunk)
                if total_size > max_size:
                    raise ValueError(
                        f"Request body too large: {total_size} > {max_size}"
                    )
                chunks.append(chunk)
            self._body = b''.join(chunks)
        return self._body

    async def json(self) -> typing.Any:
        """Asynchronously parse and return the request body as JSON.

        This method reads the request body and deserializes it using orjson,
        returning the parsed JSON object.
        """
        if not hasattr(self, '_json'):
            try:
                body = await self.body()
                self._json = orjson.loads(body)
            except orjson.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}") from e
        return self._json

    async def _get_form(
        self,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
        max_part_size: int = 1024 * 1024,
    ) -> FormData:
        if self._form is None:  # pragma: no branch
            assert (
                parse_options_header is not None
            ), 'The `python-multipart` library must be installed to use form parsing.'
            content_type_header = self.headers.get('Content-Type')
            content_type: bytes
            content_type, _ = parse_options_header(content_type_header)
            if content_type == b'multipart/form-data':
                try:
                    multipart_parser = MultiPartParser(
                        self.headers,
                        self.stream(),
                        max_files=max_files,
                        max_fields=max_fields,
                        max_part_size=max_part_size,
                    )
                    self._form = await multipart_parser.parse()
                except MultiPartException as exc:
                    raise exc
            elif content_type == b'application/x-www-form-urlencoded':
                form_parser = FormParser(self.headers, self.stream())
                self._form = await form_parser.parse()
            else:
                self._form = FormData()
        return self._form

    def form(
        self,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
        max_part_size: int = 1024 * 1024,
    ) -> AwaitableOrContextManager[FormData]:
        """Return an awaitable or async context manager for parsing form data.

        This method provides an interface to parse form data from the request body,
        supporting both 'application/x-www-form-urlencoded' and 'multipart/form-data' content types.

        Args:
            max_files (int | float, optional): Maximum number of files to accept. Defaults to 1000.
            max_fields (int | float, optional): Maximum number of fields to accept. Defaults to 1000.
            max_part_size (int, optional): Maximum size of each part in bytes. Defaults to 1MB.

        Returns:
            AwaitableOrContextManager[FormData]: An awaitable or async context manager yielding FormData.

        """  # noqa: E501
        return AwaitableOrContextManagerWrapper(
            self._get_form(
                max_files=max_files, max_fields=max_fields, max_part_size=max_part_size
            )
        )

    async def files(self) -> dict[str, list[UploadFile]]:
        """Asynchronously retrieve uploaded files from the request form data.

        Returns:
            dict[str, list[UploadFile]]: A dictionary mapping form field names to lists of UploadFile objects.

        """  # noqa: E501
        form = await self._get_form()
        files: dict[str, list[UploadFile]] = {}
        for field_name, field_value in form.multi_items():
            if isinstance(field_value, UploadFile):
                files.setdefault(field_name, []).append(field_value)
            elif isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, UploadFile):
                        files.setdefault(field_name, []).append(item)
        return files

    async def close(self) -> None:
        """Asynchronously close any resources associated with the request.

        This method closes the form data if it has been initialized, releasing any resources held.
        """  # noqa: E501
        if self._form is not None:  # pragma: no branch
            await self._form.close()
