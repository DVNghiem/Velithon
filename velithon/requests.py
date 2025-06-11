from __future__ import annotations

import typing
from http import cookies as http_cookies

import orjson
from python_multipart.multipart import parse_options_header

from velithon.datastructures import URL, Address, FormData, Headers, Protocol, QueryParams, Scope, UploadFile
from velithon.formparsers import FormParser, MultiPartException, MultiPartParser

T_co = typing.TypeVar("T_co", covariant=True)


class AwaitableOrContextManager(
    typing.Awaitable[T_co], typing.AsyncContextManager[T_co], typing.Protocol[T_co]
): ...


class SupportsAsyncClose(typing.Protocol):
    async def close(self) -> None: ...  # pragma: no cover


SupportsAsyncCloseType = typing.TypeVar(
    "SupportsAsyncCloseType", bound=SupportsAsyncClose, covariant=False
)


class AwaitableOrContextManagerWrapper(typing.Generic[SupportsAsyncCloseType]):
    __slots__ = ("aw", "entered")

    def __init__(self, aw: typing.Awaitable[SupportsAsyncCloseType]) -> None:
        self.aw = aw

    def __await__(self) -> typing.Generator[typing.Any, None, SupportsAsyncCloseType]:
        return self.aw.__await__()

    async def __aenter__(self) -> SupportsAsyncCloseType:
        self.entered = await self.aw
        return self.entered

    async def __aexit__(self, *args: typing.Any) -> None | bool:
        await self.entered.close()
        return None


def cookie_parser(cookie_string: str) -> dict[str, str]:
    """
    This function parses a ``Cookie`` HTTP header into a dict of key/value pairs.

    It attempts to mimic browser cookie parsing behavior: browsers and web servers
    frequently disregard the spec (RFC 6265) when setting and reading cookies,
    so we attempt to suit the common scenarios here.

    This function has been adapted from Django 3.1.0.
    Note: we are explicitly _NOT_ using `SimpleCookie.load` because it is based
    on an outdated spec and will fail on lots of input we want to support
    """
    cookie_dict: dict[str, str] = {}
    for chunk in cookie_string.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            cookie_dict[key] = http_cookies._unquote(val)
    return cookie_dict


class HTTPConnection(typing.Mapping[str, typing.Any]):
    """
    A base class for incoming HTTP connections, that is used to provide
    any functionality that is common to both `Request` and `WebSocket`.
    """

    __slots__ = ("scope", "protocol")

    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        assert scope.proto in ("http", "websocket")
        self.scope = scope
        self.protocol = protocol

    def __getitem__(self, key: str) -> typing.Any:
        return self.scope[key]

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.scope)

    def __len__(self) -> int:
        return len(self.scope)

    # Don't use the `abc.Mapping.__eq__` implementation.
    # Connection instances should never be considered equal
    # unless `self is other`.
    __eq__ = object.__eq__
    __hash__ = object.__hash__

    @property
    def url(self) -> URL:
        if not hasattr(self, "_url"):  # pragma: no branch
            self._url = URL(scope=self.scope)
        return self._url

    @property
    def headers(self) -> Headers:
        if not hasattr(self, "_headers"):
            self._headers = Headers(headers=self.scope.headers.items())
        return self._headers

    @property
    def query_params(self) -> QueryParams:
        if not hasattr(self, "_query_params"):  # pragma: no branch
            self._query_params = QueryParams(self.scope.query_string)
        return self._query_params

    @property
    def path_params(self) -> dict[str, typing.Any]:
        return self.scope.path_params

    @property
    def cookies(self) -> dict[str, str]:
        if not hasattr(self, "_cookies"):
            cookies: dict[str, str] = {}
            cookie_header = self.headers.get("cookie")

            if cookie_header:
                cookies = cookie_parser(cookie_header)
            self._cookies = cookies
        return self._cookies

    @property
    def client(self) -> Address | None:
        # client is a 2 item tuple of (host, port), None if missing
        host_port = self.scope.client.split(":")
        if host_port is not None:
            return Address(*host_port)
        return None


class Request(HTTPConnection):
    _form: FormData | None

    def __init__(self, scope: Scope, protocol: Protocol) -> None:
        super().__init__(scope, protocol)
        assert scope.proto == "http"
        self._form = None
    
    @property
    def request_id(self) -> str:
        return self.scope._request_id

    @property
    def method(self) -> str:
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
        if hasattr(self, "_body"):
            yield self._body
            return
        yield await self.protocol()

    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            chunks: list[bytes] = []
            async for chunk in self.stream():
                chunks.append(chunk)
            self._body = b"".join(chunks)
        return self._body

    async def json(self) -> typing.Any:
        if not hasattr(self, "_json"):  # pragma: no branch
            body = await self.body()
            self._json = orjson.loads(body)
        return self._json

    async def _get_form(
        self,
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
        max_part_size: int = 1024 * 1024,
    ) -> FormData:
        if self._form is None:  # pragma: no branch
            assert parse_options_header is not None, (
                "The `python-multipart` library must be installed to use form parsing."
            )
            content_type_header = self.headers.get("Content-Type")
            content_type: bytes
            content_type, _ = parse_options_header(content_type_header)
            if content_type == b"multipart/form-data":
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
            elif content_type == b"application/x-www-form-urlencoded":
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
        return AwaitableOrContextManagerWrapper(
            self._get_form(
                max_files=max_files, max_fields=max_fields, max_part_size=max_part_size
            )
        )
    
    async def files(self) -> typing.Dict[str, typing.List[UploadFile]]:
        async with self.form() as form:
            files: typing.Dict[str, typing.List[UploadFile]] = {}
            for field_name, field_value in form.multi_items():
                if isinstance(field_value, UploadFile):
                    files.setdefault(field_name, []).append(field_value)
                elif isinstance(field_value, list):
                    for item in field_value:
                        if isinstance(item, UploadFile):
                            files.setdefault(field_name, []).append(item)
            return files
    
    async def close(self) -> None:
        if self._form is not None:  # pragma: no branch
            await self._form.close()
