"""Redirect Response implementation."""

from __future__ import annotations

import typing
from urllib.parse import quote

from velithon.background import BackgroundTask
from velithon.datastructures import URL

from .base import Response


class RedirectResponse(Response):
    """HTTP redirect response."""

    def __init__(
        self,
        url: str | URL,
        status_code: int = 307,
        headers: typing.Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        super().__init__(
            content=b'', status_code=status_code, headers=headers, background=background
        )
        self.headers['location'] = quote(str(url), safe=":/%#?=@[]!$&'()*+,;")
