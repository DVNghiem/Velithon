"""JSON Response implementation."""

from __future__ import annotations

import typing

from velithon._utils import HAS_ORJSON, get_json_encoder, get_response_cache
from velithon.background import BackgroundTask

from .base import Response

_optimized_json_encoder = get_json_encoder()
_response_cache = get_response_cache()


class JSONResponse(Response):
    """JSON response with optimized serialization."""

    media_type = 'application/json'

    def __init__(
        self,
        content: typing.Any,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        # Pre-render the content when the response is created to avoid rendering twice
        self._content = content
        self._rendered = False
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: typing.Any) -> bytes:
        """Render content to JSON bytes with optimization."""
        # Fast path: if we already rendered this content during __init__, use that
        if self._rendered and content is self._content:
            return self.body

        # Try direct orjson encoding for maximum performance
        if HAS_ORJSON and isinstance(content, (dict, list)):
            try:
                # Use orjson directly to avoid overhead
                import orjson

                result = orjson.dumps(content, option=orjson.OPT_SERIALIZE_NUMPY)
                self._rendered = True
                return result
            except (TypeError, ValueError):
                # Fall back to standard encoder if orjson fails
                pass

        # Only use caching for complex objects where serialization is expensive
        if isinstance(content, (dict, list)) and len(str(content)) > 100:
            # Create cache key for response caching - use id() for faster hashing
            cache_key = f'json:{id(content)}'
            cached_response = _response_cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Use optimized encoder
            result = _optimized_json_encoder.encode(content)
            _response_cache.put(cache_key, result)
            return result

        # For simple objects, skip caching overhead
        return _optimized_json_encoder.encode(content)
