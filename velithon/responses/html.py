"""HTML Response implementation."""

from .base import Response


class HTMLResponse(Response):
    """Response for HTML content."""

    media_type = 'text/html'
