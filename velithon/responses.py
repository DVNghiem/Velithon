from __future__ import annotations

import http.cookies
import mimetypes
import stat
import sys
import typing
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import format_datetime
from functools import partial
from pathlib import Path
from urllib.parse import quote

import anyio

from velithon._utils import iterate_in_threadpool
from velithon.background import BackgroundTask
from velithon.datastructures import URL, Headers, Protocol, Scope
from velithon.performance import HAS_ORJSON, get_json_encoder, get_response_cache

_optimized_json_encoder = get_json_encoder()
_response_cache = get_response_cache()

has_exceptiongroups = True
if sys.version_info < (3, 11):  # pragma: no cover
    try:
        from exceptiongroup import (
            BaseExceptionGroup,  # type: ignore[unused-ignore,import-not-found]
        )
    except ImportError:
        has_exceptiongroups = False

@contextmanager
def collapse_excgroups() -> typing.Generator[None, None, None]:
    try:
        yield
    except BaseException as exc:
        if has_exceptiongroups:  # pragma: no cover
            while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
                exc = exc.exceptions[0]

        raise exc

class Response:
    media_type = None
    charset = "utf-8"

    def __init__(
        self,
        content: typing.Any = None,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.body = self.render(content)
        self.init_headers(headers)

    def render(self, content: typing.Any) -> bytes | memoryview:
        if content is None:
            return b""
        if isinstance(content, (bytes, memoryview)):
            return content
        return content.encode(self.charset)  # type: ignore

    def init_headers(self, headers: typing.Mapping[str, str] | None = None) -> None:
        if headers is None:
            raw_headers: list[tuple[str, str]] = []
            populate_content_length = True
            populate_content_type = True
        else:
            raw_headers = [(k.lower(), v) for k, v in headers.items()]
            keys = [h[0] for h in raw_headers]
            populate_content_length = "content-length" not in keys
            populate_content_type = "content-type" not in keys

        body = getattr(self, "body", None)
        if (
            body is not None
            and populate_content_length
            and not (self.status_code < 200 or self.status_code in (204, 304))
        ):
            content_length = str(len(body))
            raw_headers.append(("content-length", content_length))

        content_type = self.media_type
        if content_type is not None and populate_content_type:
            if content_type.startswith("text/") and "charset=" not in content_type.lower():
                content_type += "; charset=" + self.charset
            raw_headers.append(("content-type", content_type))

        self.raw_headers = raw_headers + [("server", "velithon")]

    @property
    def headers(self) -> Headers:
        if not hasattr(self, "_headers"):
            self._headers = Headers(headers=self.raw_headers)
        return self._headers

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: typing.Literal["lax", "strict", "none"] | None = "lax",
    ) -> None:
        cookie: http.cookies.BaseCookie[str] = http.cookies.SimpleCookie()
        cookie[key] = value
        if max_age is not None:
            cookie[key]["max-age"] = max_age
        if expires is not None:
            if isinstance(expires, datetime):
                cookie[key]["expires"] = format_datetime(expires, usegmt=True)
            else:
                cookie[key]["expires"] = expires
        if path is not None:
            cookie[key]["path"] = path
        if domain is not None:
            cookie[key]["domain"] = domain
        if secure:
            cookie[key]["secure"] = True
        if httponly:
            cookie[key]["httponly"] = True
        if samesite is not None:
            assert samesite.lower() in [
                "strict",
                "lax",
                "none",
            ], "samesite must be either 'strict', 'lax' or 'none'"
            cookie[key]["samesite"] = samesite
        cookie_val = cookie.output(header="").strip()
        self.raw_headers.append(("set-cookie", cookie_val))

    def delete_cookie(
        self,
        key: str,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: typing.Literal["lax", "strict", "none"] | None = "lax",
    ) -> None:
        self.set_cookie(
            key,
            max_age=0,
            expires=0,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        protocol.response_bytes(
            self.status_code,
            self.raw_headers,
            self.body,
        )

        if self.background is not None:
            await self.background()


class HTMLResponse(Response):
    media_type = "text/html"


class PlainTextResponse(Response):
    media_type = "text/plain"


class JSONResponse(Response):
    media_type = "application/json"

    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        # Pre-render the content when the response is created to avoid rendering twice
        self._content = content
        self._rendered = False
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: typing.Any) -> bytes:
        # Fast path: if we already rendered this content during __init__, use that
        if self._rendered and content is self._content:
            return self.body
            
        # Try direct orjson encoding for maximum performance
        if HAS_ORJSON and isinstance(content, (dict, list)):
            try:
                # Use orjson directly to avoid overhead
                import orjson
                result = orjson.dumps(content, option=orjson.OPT_SERIALIZE_NUMPY)
                self._rendered = True
                return result
            except (TypeError, ValueError):
                # Fall back to standard encoder if orjson fails
                pass
                
        # Only use caching for complex objects where serialization is expensive
        if isinstance(content, (dict, list)) and len(str(content)) > 100:
            # Create cache key for response caching - use id() for faster hashing
            cache_key = f"json:{id(content)}"
            cached_response = _response_cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Use optimized encoder
            result = _optimized_json_encoder.encode(content)
            _response_cache.put(cache_key, result)
            return result
            
        # For simple objects, skip caching overhead
        return _optimized_json_encoder.encode(content)


class RedirectResponse(Response):
    def __init__(
        self,
        url: str | URL,
        status_code: int = 307,
        headers: typing.Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(content=b"", status_code=status_code, headers=headers, background=background)
        self.headers["location"] = quote(str(url), safe=":/%#?=@[]!$&'()*+,;")


class FileResponse(Response):
    chunk_size = 64 * 1024  # 64KB chunks

    def __init__(
        self,
        path: str | Path,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        stat_result: stat.stat_result | None = None,
        method: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self.path = Path(path)
        self.status_code = status_code
        self.filename = filename
        self.method = method
        
        if media_type is None:
            media_type = mimetypes.guess_type(str(self.path))[0] or "application/octet-stream"
        self.media_type = media_type
        
        self.background = background
        self.stat_result = stat_result
        if stat_result is not None:
            self.set_stat_headers(stat_result)
        
        self.init_headers(headers)

    def set_stat_headers(self, stat_result: stat.stat_result) -> None:
        content_length = str(stat_result.st_size)
        last_modified = format_datetime(datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc), usegmt=True)
        etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
        etag = f'"{hash(etag_base)}"'

        self.headers["content-length"] = content_length
        self.headers["last-modified"] = last_modified
        self.headers["etag"] = etag

    def init_headers(self, headers: typing.Mapping[str, str] | None = None) -> None:
        if headers is None:
            raw_headers: list[tuple[str, str]] = []
        else:
            raw_headers = [(k.lower(), v) for k, v in headers.items()]

        # Set content-disposition if filename is provided
        if self.filename is not None:
            content_disposition = f'attachment; filename="{self.filename}"'
            raw_headers.append(("content-disposition", content_disposition))

        # Set content-type
        if self.media_type is not None:
            raw_headers.append(("content-type", self.media_type))

        # Add cache headers for static files
        raw_headers.append(("cache-control", "public, max-age=3600"))
        
        self.raw_headers = raw_headers + [("server", "velithon")]

    @property
    def headers(self) -> Headers:
        if not hasattr(self, "_headers"):
            self._headers = Headers(headers=self.raw_headers)
        return self._headers

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        method = scope.get("method", "GET")
        
        # Check if file exists
        if not self.path.exists():
            await self._not_found_response(protocol)
            return
            
        # Check if it's a file (not directory)
        if not self.path.is_file():
            await self._not_found_response(protocol)
            return

        # Get file stats if not provided
        if self.stat_result is None:
            try:
                self.stat_result = self.path.stat()
                self.set_stat_headers(self.stat_result)
            except OSError:
                await self._not_found_response(protocol)
                return

        # Handle HEAD requests
        if method == "HEAD":
            protocol.response_bytes(
                self.status_code,
                self.raw_headers,
                b"",
            )
        else:
            # Stream file content
            await self._stream_file(protocol)
            
        if self.background is not None:
            await self.background()

    async def _not_found_response(self, protocol: Protocol) -> None:
        """Send 404 response when file is not found."""
        headers = [("content-type", "text/plain"), ("server", "velithon")]
        protocol.response_bytes(
            404,
            headers,
            b"File not found",
        )

    async def _stream_file(self, protocol: Protocol) -> None:
        """Stream file content in chunks."""
        try:
            trx = protocol.response_stream(self.status_code, self.raw_headers)
            
            async with await anyio.open_file(self.path, mode="rb") as file:
                while True:
                    chunk = await file.read(self.chunk_size)
                    if not chunk:
                        break
                    await trx.send_bytes(chunk)
        except (OSError, IOError) as exc:
            # File read error - try to send error response if possible
            raise RuntimeError(f"Error reading file {self.path}: {exc}") from exc


Content = typing.Union[str, bytes, memoryview]
SyncContentStream = typing.Iterable[Content]
AsyncContentStream = typing.AsyncIterable[Content]
ContentStream = typing.Union[AsyncContentStream, SyncContentStream]


class StreamingResponse(Response):
    body_iterator: AsyncContentStream

    def __init__(
        self,
        content: ContentStream,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        if isinstance(content, typing.AsyncIterable):
            self.body_iterator = content
        else:
            self.body_iterator = iterate_in_threadpool(content)
        self.status_code = status_code
        self.media_type = self.media_type if media_type is None else media_type
        self.background = background
        self.init_headers(headers)

    async def stream_response(self, protocol: Protocol) -> None:
        trx = protocol.response_stream(self.status_code, self.raw_headers)
        async for chunk in self.body_iterator:
            if not isinstance(chunk, (bytes, memoryview)):
                chunk = chunk.encode(self.charset)
            await trx.send_bytes(chunk)

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        spec_version = tuple(map(int, scope.get("asgi", {}).get("spec_version", "2.0").split(".")))

        if spec_version >= (2, 4):
            try:
                await self.stream_response(protocol)
            except OSError as exc:
                raise RuntimeError(f"Network error during streaming: {exc}") from exc
        else:
            with collapse_excgroups():
                async with anyio.create_task_group() as task_group:

                    async def wrap(func: typing.Callable[[], typing.Awaitable[None]]) -> None:
                        await func()
                        task_group.cancel_scope.cancel()
                    task_group.start_soon(wrap, partial(self.stream_response, protocol))

        if self.background is not None:
            await self.background()



