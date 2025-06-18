"""Proxy Response implementation."""

from __future__ import annotations

from velithon.datastructures import Protocol, Scope

from .base import Response


class ProxyResponse(Response):
    """Custom response class for proxy responses."""

    def __init__(
        self,
        content: bytes,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self.body = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = self.headers.get('content-type', 'application/octet-stream')

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Send the response."""
        # Convert headers to list of tuples
        header_list = [(k.encode(), v.encode()) for k, v in self.headers.items()]

        await protocol.response_start(self.status_code, header_list)
        await protocol.response_body(self.body)
