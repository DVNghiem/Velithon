"""Base Response class for Velithon framework."""

from __future__ import annotations

import http.cookies
import typing
from datetime import datetime
from email.utils import format_datetime

# Rust implementation available for complex scenarios
from velithon._velithon import header_init
from velithon.background import BackgroundTask
from velithon.datastructures import Headers, Protocol, Scope


class Response:
    """Base class for HTTP responses in Velithon framework.

    Uses high-performance Rust implementation for header initialization
    when available, falling back to Python implementation.
    """

    media_type = None
    charset = 'utf-8'

    def __init__(
        self,
        content: typing.Any = None,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """Initialize the response with content, status code, headers, media type, and background task."""  # noqa: E501
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.body = self.render(content)
        self.init_headers(headers)

    def render(self, content: typing.Any) -> bytes | memoryview:
        """Render the content to bytes or memoryview."""
        if content is None:
            return b''
        if isinstance(content, (bytes, memoryview)):
            return content
        return content.encode(self.charset)  # type: ignore

    def init_headers(self, headers: typing.Mapping[str, str] | None = None) -> None:
        """Initialize response headers using Rust implementation when available."""
        # Use high-performance Rust implementation
        # Convert headers to dict for Rust function
        headers_dict = dict(headers) if headers else None

        self.raw_headers = header_init(
            body_length=len(self.body) if self.body else 0,
            status_code=self.status_code,
            media_type=self.media_type,
            charset=self.charset,
            provided_headers=headers_dict,
        )

    @property
    def headers(self) -> Headers:
        """Return the response headers as a Headers object."""
        if not hasattr(self, '_headers'):
            self._headers = Headers(headers=self.raw_headers)
        return self._headers

    def set_cookie(
        self,
        key: str,
        value: str = '',
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str | None = '/',
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: typing.Literal['lax', 'strict', 'none'] | None = 'lax',
    ) -> None:
        """Set a cookie in the response headers."""
        cookie: http.cookies.BaseCookie[str] = http.cookies.SimpleCookie()
        cookie[key] = value
        if max_age is not None:
            cookie[key]['max-age'] = max_age
        if expires is not None:
            if isinstance(expires, datetime):
                cookie[key]['expires'] = format_datetime(expires, usegmt=True)
            else:
                cookie[key]['expires'] = expires
        if path is not None:
            cookie[key]['path'] = path
        if domain is not None:
            cookie[key]['domain'] = domain
        if secure:
            cookie[key]['secure'] = True
        if httponly:
            cookie[key]['httponly'] = True
        if samesite is not None:
            assert samesite.lower() in [
                'strict',
                'lax',
                'none',
            ], "samesite must be either 'strict', 'lax' or 'none'"
            cookie[key]['samesite'] = samesite
        cookie_val = cookie.output(header='').strip()
        self.raw_headers.append(('set-cookie', cookie_val))

    def delete_cookie(
        self,
        key: str,
        path: str = '/',
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: typing.Literal['lax', 'strict', 'none'] | None = 'lax',
    ) -> None:
        """Delete a cookie by setting its max-age and expires to 0."""
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
        """Call the response to send it over the protocol."""
        protocol.response_bytes(
            self.status_code,
            self.raw_headers,
            self.body,
        )

        if self.background is not None:
            await self.background()
