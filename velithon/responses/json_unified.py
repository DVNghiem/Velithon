"""Unified JSON Response implementation - the single, best-performing JSON response."""

from __future__ import annotations

import typing

from velithon._utils import HAS_ORJSON, get_json_encoder, get_response_cache
from velithon.background import BackgroundTask

from .base import Response

_optimized_json_encoder = get_json_encoder()
_response_cache = get_response_cache()


class JsonResponse(Response):
    """High-performance JSON response optimized for all use cases.
    
    This is the unified JSON response that combines the best of all approaches:
    - Uses orjson for maximum performance with native types
    - Intelligent caching for complex objects
    - Fast path for simple data
    - Graceful fallback for edge cases
    
    This replaces JSONResponse, OptimizedJSONResponse, and BatchJSONResponse
    to provide users with one clear, fast choice for JSON responses.
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
        """Render content to JSON bytes with optimal performance."""
        # Fast path: if we already rendered this content during __init__, use that
        if self._rendered and content is self._content:
            return self.body

        # Use orjson for maximum performance when available
        if HAS_ORJSON and isinstance(
            content, dict | list | str | int | float | bool | type(None)
        ):
            try:
                import orjson

                result = orjson.dumps(content, option=orjson.OPT_SERIALIZE_NUMPY)
                self._rendered = True
                return result
            except (TypeError, ValueError):
                # Fall back to standard encoder if orjson fails
                pass

        # For complex objects or when orjson is not available, use optimized encoder
        # Only use caching for objects that are expensive to serialize
        content_str = str(content)
        if len(content_str) > 1000:  # Only cache larger objects
            cache_key = f'json:{id(content)}'
            cached_response = _response_cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            result = _optimized_json_encoder.encode(content)
            _response_cache.put(cache_key, result)
            return result

        # For simple objects, encode directly without caching overhead
        return _optimized_json_encoder.encode(content)
