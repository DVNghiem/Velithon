"""Server-Sent Events (SSE) Response implementation."""

from __future__ import annotations

import typing

from velithon._utils import get_json_encoder, iterate_in_threadpool
from velithon.background import BackgroundTask
from velithon.datastructures import Protocol, Scope

from .base import Response

_optimized_json_encoder = get_json_encoder()


class SSEResponse(Response):
    """Server-Sent Events (SSE) response for real-time streaming.

    SSE allows a server to push data to a client over HTTP in a standardized format.
    This is useful for real-time applications like live updates, notifications, or streaming data.

    The SSE format includes:
    - data: The actual data to send
    - event: Optional event type
    - id: Optional unique identifier for the event
    - retry: Optional retry time in milliseconds

    Example:
        @app.get('/events')
        async def stream_events():
            async def generate():
                for i in range(10):
                    yield {'data': f'Event {i}', 'id': str(i)}
                    await asyncio.sleep(1)

            return SSEResponse(generate())

    """

    media_type = 'text/event-stream'

    def __init__(
        self,
        content: typing.AsyncIterable[str | dict | typing.Any]
        | typing.Iterable[str | dict | typing.Any],
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        ping_interval: int | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """Initialize SSE response.

        Args:
            content: Async or sync iterable that yields SSE events
            status_code: HTTP status code (default: 200)
            headers: Additional HTTP headers
            ping_interval: Interval in seconds to send ping events (keeps connection alive)
            background: Background task to run after streaming

        """
        if isinstance(content, typing.AsyncIterable):
            self.body_iterator = content
        else:
            self.body_iterator = iterate_in_threadpool(content)

        self.status_code = status_code
        self.ping_interval = ping_interval
        self.background = background

        # Set up SSE headers
        sse_headers = {
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
        }

        if headers:
            sse_headers.update(headers)

        self.init_headers(sse_headers)

    def _format_sse_event(self, event_data: typing.Any) -> str:
        """Format data as SSE event.

        Args:
            event_data: Can be a string, dict with SSE fields, or any serializable object

        Returns:
            Formatted SSE event string

        """
        if isinstance(event_data, str):
            return f'data: {event_data}\n\n'

        if isinstance(event_data, dict):
            lines = []

            # Handle standard SSE fields
            if 'data' in event_data:
                data = event_data['data']
                if not isinstance(data, str):
                    # Convert non-string data to JSON
                    data = _optimized_json_encoder.encode(data).decode('utf-8')
                lines.append(f'data: {data}')

            if 'event' in event_data:
                lines.append(f'event: {event_data["event"]}')

            if 'id' in event_data:
                lines.append(f'id: {event_data["id"]}')

            if 'retry' in event_data:
                lines.append(f'retry: {event_data["retry"]}')

            # If no standard fields, treat the whole dict as data
            if not any(
                field in event_data for field in ['data', 'event', 'id', 'retry']
            ):
                data = _optimized_json_encoder.encode(event_data).decode('utf-8')
                lines.append(f'data: {data}')

            return '\n'.join(lines) + '\n\n'

        # For any other type, serialize as JSON data
        data = _optimized_json_encoder.encode(event_data).decode('utf-8')
        return f'data: {data}\n\n'

    def _format_ping_event(self) -> str:
        """Format a ping event to keep connection alive."""
        return ': ping\n\n'

    async def stream_response(self, protocol: Protocol) -> None:
        """Stream SSE events to the client."""
        import asyncio

        trx = protocol.response_stream(self.status_code, self.raw_headers)

        # Setup ping task if ping_interval is specified
        ping_task = None
        if self.ping_interval:

            async def send_ping():
                while True:
                    await asyncio.sleep(self.ping_interval)
                    try:
                        ping_data = self._format_ping_event().encode(self.charset)
                        await trx.send_bytes(ping_data)
                    except Exception:
                        # Connection closed, stop pinging
                        break

            ping_task = asyncio.create_task(send_ping())

        try:
            async for event_data in self.body_iterator:
                sse_event = self._format_sse_event(event_data)
                event_bytes = sse_event.encode(self.charset)
                await trx.send_bytes(event_bytes)

        finally:
            # Cancel ping task when done
            if ping_task:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

    async def __call__(self, scope: Scope, protocol: Protocol) -> None:
        """Handle the RSGI call for SSE response."""
        try:
            await self.stream_response(protocol)
        except OSError as exc:
            raise RuntimeError(f'Network error during SSE streaming: {exc}') from exc

        if self.background is not None:
            await self.background()
