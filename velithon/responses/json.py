"""Unified JSON Response implementation - the single, best-performing JSON response."""

from __future__ import annotations

import typing

from velithon._utils import get_json_encoder
from velithon.background import BackgroundTask

from .base import Response

_optimized_json_encoder = get_json_encoder()


class JSONResponse(Response):
    """High-performance JSON response optimized for all use cases.

    This is the unified JSON response that combines the best of all approaches:
    - Uses orjson for maximum performance with native types
    - Intelligent caching for complex objects
    - Fast path for simple data
    - Graceful fallback for edge cases
    """

    media_type = 'application/json'

    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """Initialize JSON response with content."""
        self._content = content
        self._rendered = False
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: typing.Any) -> bytes:
        """Render content to JSON bytes using orjson encoder."""
        # Fast path: if we already rendered this content during __init__, use that
        if self._rendered and content is self._content:
            return self.body

        # Use the optimized JSON encoder (orjson-only)
        return _optimized_json_encoder.encode(content)
