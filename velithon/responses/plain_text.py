"""Plain text Response implementation."""

from .base import Response


class PlainTextResponse(Response):
    """Response for plain text content."""

    media_type = 'text/plain'
