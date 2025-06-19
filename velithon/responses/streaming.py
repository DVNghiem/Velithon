"""Streaming Response implementation."""

from __future__ import annotations

import typing

from velithon._utils import iterate_in_threadpool
from velithon.background import BackgroundTask
from velithon.datastructures import Protocol, Scope

from .base import Response

# Type definitions for streaming content
Content = typing.Union[str, bytes, memoryview]
SyncContentStream = typing.Iterable[Content]
AsyncContentStream = typing.AsyncIterable[Content]
ContentStream = typing.Union[AsyncContentStream, SyncContentStream]


class StreamingResponse(Response):
    """Response that streams content asynchronously."""

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
        """Stream response content to the client."""
        trx = protocol.response_stream(self.status_code, self.raw_headers)
        async for chunk in self.body_iterator:
            if not isinstance(chunk, (bytes, memoryview)):
                chunk = chunk.encode(self.charset)
            await trx.send_bytes(chunk)

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Handle the streaming response."""
        try:
            await self.stream_response(protocol)
        except OSError as exc:
            raise RuntimeError(f'Network error during streaming: {exc}') from exc

        if self.background is not None:
            await self.background()
