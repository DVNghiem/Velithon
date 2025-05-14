#  @copyright (c) 2025 Starlette
from __future__ import annotations
import typing
from urllib.parse import SplitResult, parse_qsl, urlencode, urlsplit
from granian.rsgi import HTTPProtocol, Scope as RSGIScope
from velithon._utils import run_in_threadpool, RequestIDGenerator

request_id_generator = RequestIDGenerator()

class Scope:
    """
    Wrapper for the RSGI scope object.
    """
    __slots__ = (
        "_scope",
        "_path_params",
        "_request_id",
        "_di_context",
    )
    def __init__(self, scope: RSGIScope) -> None:
        self._scope = scope
        # extend the scope with additional properties
        self._path_params = {}
        self.request_id = request_id_generator.generate()
        self._di_context = {}

    @property
    def proto(self) -> typing.Literal["http", "websocket"]:
        return self._scope.proto
    @property
    def rsgi_version(self) -> str:
        return self._scope.rsgi_version
    @property
    def http_version(self) -> str:
        return self._scope.http_version
    @property
    def server(self) -> str:
        return self._scope.server
    @property
    def client(self) -> str:
        return self._scope.client
    @property
    def scheme(self) -> str:
        return self._scope.scheme
    @property
    def method(self) -> str:
        return self._scope.method
    @property
    def path(self) -> str:
        return self._scope.path
    @property
    def query_string(self) -> str:
        return self._scope.query_string
    @property
    def headers(self) -> typing.MutableMapping[str, str]:
        return self._scope.headers
    @property
    def authority(self) -> typing.Optional[str]:
        return self._scope.authority
    @property
    def path_params(self) -> typing.Mapping[str, str]:
        return self._path_params

class Protocol:

    __slots__ = (
        "_protocol",
        "_status_code",
        "_headers",
    )

    def __init__(self, protocol: HTTPProtocol) -> None:
        self._protocol = protocol
        self._status_code = 200
        self._headers = []

    async def __call__(self, *args, **kwds) -> bytes:
        return await self._protocol(*args, **kwds)
    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        return await self._protocol.__aiter__()
    async def client_disconnect(self) -> None:
        await self._protocol.client_disconnect()
    def response_empty(self, status: int, headers: typing.Tuple[str, str]) -> None:
        self._status_code = status
        self._headers = headers
        self._protocol.response_empty(status, headers)
    def response_str(
        self, status: int, headers: typing.Tuple[str, str], body: str
    ) -> None:
        self._status_code = status
        self._headers = headers
        self._protocol.response_str(status, headers, body)
    def response_bytes(
        self, status: int, headers: typing.Tuple[str, str], body: bytes
    ) -> None:
        self._status_code = status
        self._headers = headers
        self._protocol.response_bytes(status, headers, body)
    def response_file(
        self, status: int, headers: typing.Tuple[str, str], file: typing.Any
    ) -> None:
        self._status_code = status
        self._headers = headers
        self._protocol.response_file(status, headers, file)
    def response_stream(
        self, status: int, headers: typing.Tuple[str, str]
    ) -> typing.Any: 
        self._status_code = status
        self._headers = headers
        return self._protocol.response_stream(status, headers)
class Address(typing.NamedTuple):
    host: str
    port: int


_KeyType = typing.TypeVar("_KeyType")
# Mapping keys are invariant but their values are covariant since
# you can only read them
# that is, you can't do `Mapping[str, Animal]()["fido"] = Dog()`
_CovariantValueType = typing.TypeVar("_CovariantValueType", covariant=True)


class URL:
    def __init__(
        self,
        url: str = "",
        scope: Scope | None = None,
        **components: typing.Any,
    ) -> None:
        if scope is not None:
            assert not url, 'Cannot set both "url" and "scope".'
            assert not components, 'Cannot set both "scope" and "**components".'
            scheme = scope.scheme
            server = scope.server
            path = scope.path
            query_string = scope.query_string

            host_header = None
            for key, value in scope.headers.items():
                if key == b"host":
                    host_header = value.decode("latin-1")
                    break

            if host_header is not None:
                url = f"{scheme}://{host_header}{path}"
            elif server is None:
                url = path
            else:
                host, port = server.split(":")
                default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
                if port == default_port:
                    url = f"{scheme}://{host}{path}"
                else:
                    url = f"{scheme}://{host}:{port}{path}"

            if query_string:
                url += "?" + query_string
        elif components:
            assert not url, 'Cannot set both "url" and "**components".'
            url = URL("").replace(**components).components.geturl()

        self._url = url

    @property
    def components(self) -> SplitResult:
        if not hasattr(self, "_components"):
            self._components = urlsplit(self._url)
        return self._components

    @property
    def scheme(self) -> str:
        return self.components.scheme

    @property
    def netloc(self) -> str:
        return self.components.netloc

    @property
    def path(self) -> str:
        return self.components.path

    @property
    def query(self) -> str:
        return self.components.query

    @property
    def fragment(self) -> str:
        return self.components.fragment

    @property
    def username(self) -> None | str:
        return self.components.username

    @property
    def password(self) -> None | str:
        return self.components.password

    @property
    def hostname(self) -> None | str:
        return self.components.hostname

    @property
    def port(self) -> int | None:
        return self.components.port

    @property
    def is_secure(self) -> bool:
        return self.scheme in ("https", "wss")

    def replace(self, **kwargs: typing.Any) -> URL:
        if "username" in kwargs or "password" in kwargs or "hostname" in kwargs or "port" in kwargs:
            hostname = kwargs.pop("hostname", None)
            port = kwargs.pop("port", self.port)
            username = kwargs.pop("username", self.username)
            password = kwargs.pop("password", self.password)

            if hostname is None:
                netloc = self.netloc
                _, _, hostname = netloc.rpartition("@")

                if hostname[-1] != "]":
                    hostname = hostname.rsplit(":", 1)[0]

            netloc = hostname
            if port is not None:
                netloc += f":{port}"
            if username is not None:
                userpass = username
                if password is not None:
                    userpass += f":{password}"
                netloc = f"{userpass}@{netloc}"

            kwargs["netloc"] = netloc

        components = self.components._replace(**kwargs)
        return self.__class__(components.geturl())

    def __eq__(self, other: typing.Any) -> bool:
        return str(self) == str(other)

    def __str__(self) -> str:
        return self._url

    def __repr__(self) -> str:
        url = str(self)
        if self.password:
            url = str(self.replace(password="********"))
        return f"{self.__class__.__name__}({repr(url)})"


class URLPath(str):
    """
    A URL path string that may also hold an associated protocol and/or host.
    Used by the routing to return `url_path_for` matches.
    """

    def __new__(cls, path: str, protocol: str = "", host: str = "") -> URLPath:
        assert protocol in ("http", "websocket", "")
        return str.__new__(cls, path)

    def __init__(self, path: str, protocol: str = "", host: str = "") -> None:
        self.protocol = protocol
        self.host = host

    def make_absolute_url(self, base_url: str | URL) -> URL:
        if isinstance(base_url, str):
            base_url = URL(base_url)
        if self.protocol:
            scheme = {
                "http": {True: "https", False: "http"},
                "websocket": {True: "wss", False: "ws"},
            }[self.protocol][base_url.is_secure]
        else:
            scheme = base_url.scheme

        netloc = self.host or base_url.netloc
        path = base_url.path.rstrip("/") + str(self)
        return URL(scheme=scheme, netloc=netloc, path=path)

class ImmutableMultiDict(typing.Mapping[_KeyType, _CovariantValueType]):
    _dict: dict[_KeyType, _CovariantValueType]

    def __init__(
        self,
        *args: ImmutableMultiDict[_KeyType, _CovariantValueType]
        | typing.Mapping[_KeyType, _CovariantValueType]
        | typing.Iterable[tuple[_KeyType, _CovariantValueType]],
        **kwargs: typing.Any,
    ) -> None:
        assert len(args) < 2, "Too many arguments."

        value: typing.Any = args[0] if args else []
        if kwargs:
            value = ImmutableMultiDict(value).multi_items() + ImmutableMultiDict(kwargs).multi_items()

        if not value:
            _items: list[tuple[typing.Any, typing.Any]] = []
        elif hasattr(value, "multi_items"):
            value = typing.cast(ImmutableMultiDict[_KeyType, _CovariantValueType], value)
            _items = list(value.multi_items())
        elif hasattr(value, "items"):
            value = typing.cast(typing.Mapping[_KeyType, _CovariantValueType], value)
            _items = list(value.items())
        else:
            value = typing.cast("list[tuple[typing.Any, typing.Any]]", value)
            _items = list(value)

        self._dict = {k: v for k, v in _items}
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

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return sorted(self._list) == sorted(other._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        items = self.multi_items()
        return f"{class_name}({items!r})"


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
        *args: MultiDict | typing.Mapping[typing.Any, typing.Any] | list[tuple[typing.Any, typing.Any]],
        **kwargs: typing.Any,
    ) -> None:
        value = MultiDict(*args, **kwargs)
        existing_items = [(k, v) for (k, v) in self._list if k not in value.keys()]
        self._list = existing_items + value.multi_items()
        self._dict.update(value)


class QueryParams(ImmutableMultiDict[str, str]):
    """
    An immutable multidict.
    """

    def __init__(
        self,
        *args: ImmutableMultiDict[typing.Any, typing.Any]
        | typing.Mapping[typing.Any, typing.Any]
        | list[tuple[typing.Any, typing.Any]]
        | str
        | bytes,
        **kwargs: typing.Any,
    ) -> None:
        assert len(args) < 2, "Too many arguments."

        value = args[0] if args else []

        if isinstance(value, str):
            super().__init__(parse_qsl(value, keep_blank_values=True), **kwargs)
        elif isinstance(value, bytes):
            super().__init__(parse_qsl(value.decode("latin-1"), keep_blank_values=True), **kwargs)
        else:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._list = [(str(k), str(v)) for k, v in self._list]
        self._dict = {str(k): str(v) for k, v in self._dict.items()}

    def __str__(self) -> str:
        return urlencode(self._list)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        query_string = str(self)
        return f"{class_name}({query_string!r})"


class UploadFile:
    """
    An uploaded file included as part of the request data.
    """

    def __init__(
        self,
        file: typing.BinaryIO,
        *,
        size: int | None = None,
        filename: str | None = None,
        headers: Headers | None = None,
    ) -> None:
        self.filename = filename
        self.file = file
        self.size = size
        self.headers = headers or Headers()

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type", None)

    @property
    def _in_memory(self) -> bool:
        # check for SpooledTemporaryFile._rolled
        rolled_to_disk = getattr(self.file, "_rolled", True)
        return not rolled_to_disk

    async def write(self, data: bytes) -> None:
        if self.size is not None:
            self.size += len(data)

        if self._in_memory:
            self.file.write(data)
        else:
            await run_in_threadpool(self.file.write, data)

    async def read(self, size: int = -1) -> bytes:
        if self._in_memory:
            return self.file.read(size)
        return await run_in_threadpool(self.file.read, size)

    async def seek(self, offset: int) -> None:
        if self._in_memory:
            self.file.seek(offset)
        else:
            await run_in_threadpool(self.file.seek, offset)

    async def close(self) -> None:
        if self._in_memory:
            self.file.close()
        else:
            await run_in_threadpool(self.file.close)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(filename={self.filename!r}, size={self.size!r}, headers={self.headers!r})"


class FormData(ImmutableMultiDict[str, typing.Union[UploadFile, str]]):
    """
    An immutable multidict, containing both file uploads and text input.
    """

    def __init__(
        self,
        *args: FormData | typing.Mapping[str, str | UploadFile] | list[tuple[str, str | UploadFile]],
        **kwargs: str | UploadFile,
    ) -> None:
        super().__init__(*args, **kwargs)

    async def close(self) -> None:
        for key, value in self.multi_items():
            if isinstance(value, UploadFile):
                await value.close()


class Headers(typing.Mapping[str, str]):
    """
    An immutable, case-insensitive multidict.
    """

    def __init__(
        self,
        headers: list[tuple[str, str]] | None = None,
        scope: Scope | None = None,
    ) -> None:
        self._list: list[tuple[str, str]] = []
        if headers is not None:
            assert scope is None, 'Cannot set both "headers" and "scope".'
            self._list = headers
        elif scope is not None:
            self._list = scope.headers.items()

    @property
    def raw(self) -> list[tuple[str, str]]:
        return list(self._list)

    def keys(self) -> list[str]:  # type: ignore[override]
        return [key for key, value in self._list]

    def values(self) -> list[str]:  # type: ignore[override]
        return [value for key, value in self._list]

    def items(self) -> list[tuple[str, str]]:  # type: ignore[override]
        return [(key, value) for key, value in self._list]

    def __getitem__(self, key: str) -> str:
        get_header_key = key.lower()
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return header_value
        raise KeyError(key)

    def __contains__(self, key: typing.Any) -> bool:
        get_header_key = key.lower()
        for header_key, header_value in self._list:
            if header_key == get_header_key:
                return True
        return False

    def __iter__(self) -> typing.Iterator[typing.Any]:
        return iter(self.keys())
    
    def __len__(self) -> int:
        return len(self._list)
    
    def __setitem__(self, key: str, value: str) -> None:
        """
        Set the header `key` to `value`, removing any duplicate entries.
        Retains insertion order.
        """
        key = key.lower()

        found_indexes: list[int] = []
        for idx, (item_key, item_value) in enumerate(self._list):
            if item_key == key:
                found_indexes.append(idx)

        for idx in reversed(found_indexes[1:]):
            del self._list[idx]

        if found_indexes:
            idx = found_indexes[0]
            self._list[idx] = (key, value)
        else:
            self._list.append((key, value))


