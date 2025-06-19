"""File Response implementation."""

from __future__ import annotations

import mimetypes
import stat
import typing
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import anyio

from velithon.background import BackgroundTask
from velithon.datastructures import Headers, Protocol, Scope

from .base import Response


class FileResponse(Response):
    """Response for serving files with streaming support."""

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
            media_type = (
                mimetypes.guess_type(str(self.path))[0] or 'application/octet-stream'
            )
        self.media_type = media_type

        self.background = background
        self.stat_result = stat_result
        if stat_result is not None:
            self.set_stat_headers(stat_result)

        self.init_headers(headers)

    def set_stat_headers(self, stat_result: stat.stat_result) -> None:
        """Set headers based on file statistics."""
        content_length = str(stat_result.st_size)
        last_modified = format_datetime(
            datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc), usegmt=True
        )
        etag_base = str(stat_result.st_mtime) + '-' + str(stat_result.st_size)
        etag = f'"{hash(etag_base)}"'

        self.headers['content-length'] = content_length
        self.headers['last-modified'] = last_modified
        self.headers['etag'] = etag

    def init_headers(self, headers: typing.Mapping[str, str] | None = None) -> None:
        """Initialize file response headers."""
        if headers is None:
            raw_headers: list[tuple[str, str]] = []
        else:
            raw_headers = [(k.lower(), v) for k, v in headers.items()]

        # Set content-disposition if filename is provided
        if self.filename is not None:
            content_disposition = f'attachment; filename="{self.filename}"'
            raw_headers.append(('content-disposition', content_disposition))

        # Set content-type
        if self.media_type is not None:
            raw_headers.append(('content-type', self.media_type))

        # Add cache headers for static files
        raw_headers.append(('cache-control', 'public, max-age=3600'))

        self.raw_headers = raw_headers + [('server', 'velithon')]

    @property
    def headers(self) -> Headers:
        """Get response headers."""
        if not hasattr(self, '_headers'):
            self._headers = Headers(headers=self.raw_headers)
        return self._headers

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Handle the file response."""
        method = scope.get('method', 'GET')

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
        if method == 'HEAD':
            protocol.response_bytes(
                self.status_code,
                self.raw_headers,
                b'',
            )
        else:
            # Stream file content
            await self._stream_file(protocol)

        if self.background is not None:
            await self.background()

    async def _not_found_response(self, protocol: Protocol) -> None:
        """Send 404 response when file is not found."""
        headers = [('content-type', 'text/plain'), ('server', 'velithon')]
        protocol.response_bytes(
            404,
            headers,
            b'File not found',
        )

    async def _stream_file(self, protocol: Protocol) -> None:
        """Stream file content in chunks."""
        try:
            trx = protocol.response_stream(self.status_code, self.raw_headers)

            async with await anyio.open_file(self.path, mode='rb') as file:
                while True:
                    chunk = await file.read(self.chunk_size)
                    if not chunk:
                        break
                    await trx.send_bytes(chunk)
        except OSError as exc:
            # File read error - try to send error response if possible
            raise RuntimeError(f'Error reading file {self.path}: {exc}') from exc
