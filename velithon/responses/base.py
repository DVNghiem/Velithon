"""Base Response class for Velithon framework."""

from __future__ import annotations

import http.cookies
import typing
from datetime import datetime
from email.utils import format_datetime

from velithon.background import BackgroundTask
from velithon.datastructures import Headers


class Response:
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
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.body = self.render(content)
        self.init_headers(headers)

    def render(self, content: typing.Any) -> bytes | memoryview:
        if content is None:
            return b''
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
            populate_content_length = 'content-length' not in keys
            populate_content_type = 'content-type' not in keys

        body = getattr(self, 'body', None)
        if (
            body is not None
            and populate_content_length
            and not (self.status_code < 200 or self.status_code in (204, 304))
        ):
            content_length = str(len(body))
            raw_headers.append(('content-length', content_length))

        content_type = self.media_type
        if content_type is not None and populate_content_type:
            if (
                content_type.startswith('text/')
                and 'charset=' not in content_type.lower()
            ):
                content_type += '; charset=' + self.charset
            raw_headers.append(('content-type', content_type))

        self.raw_headers = raw_headers + [('server', 'velithon')]

    @property
    def headers(self) -> Headers:
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
