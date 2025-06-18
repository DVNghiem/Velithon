"""High-performance JSON response implementation using Rust-based parallel serialization."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from velithon._velithon import (
    BatchJSONSerializer,
    ParallelJSONSerializer,
)
from velithon.background import BackgroundTask

from .base import Response


class OptimizedJSONResponse(Response):
    """High-performance JSON response with parallel serialization for large objects.

    Features:
    - Automatic parallel processing for large collections (configurable threshold)
    - Fast path for simple objects (primitives, small collections)
    - Caching for frequently serialized objects
    - Memory-efficient streaming for very large objects
    - Fallback to standard JSON for compatibility
    """

    media_type = 'application/json'

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        # New optimization parameters
        parallel_threshold: int = 10000,  # Higher threshold for better performance
        use_parallel_auto: bool = True,
        enable_caching: bool = True,
        max_cache_size: int = 1000,
    ) -> None:
        """Initialize optimized JSON response with parallel processing capabilities."""
        self._content = content
        self._parallel_threshold = parallel_threshold
        self._use_parallel_auto = use_parallel_auto
        self._enable_caching = enable_caching

        # Initialize the Rust-based serializer
        self._serializer = ParallelJSONSerializer(
            parallel_threshold=parallel_threshold,
            max_depth=32,
            cache_size_limit=max_cache_size if enable_caching else 0,
        )

        # Performance tracking
        self._render_time = 0.0
        self._used_parallel = False
        self._cache_hit = False

        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: Any) -> bytes:
        """Render content to JSON bytes using optimized Rust serialization."""
        start_time = time.perf_counter()

        # Use provided content or fallback to stored content
        content_to_render = content if content is not None else self._content

        try:
            # Use the Rust-based serializer
            if self._use_parallel_auto:
                # Auto-detect when to use parallel processing
                result = self._serializer.serialize(
                    content_to_render, use_parallel=None
                )
            else:
                # Force parallel processing for large objects
                should_parallel = self._should_use_parallel_heuristic(content_to_render)
                result = self._serializer.serialize(
                    content_to_render, use_parallel=should_parallel
                )

            self._render_time = time.perf_counter() - start_time
            return bytes(result)

        except Exception as e:
            # Fallback to standard JSON serialization
            import json

            try:
                fallback_result = json.dumps(
                    content_to_render, separators=(',', ':')
                ).encode('utf-8')
                self._render_time = time.perf_counter() - start_time
                return fallback_result
            except Exception as fallback_error:
                msg = (
                    f'JSON serialization failed: {e}, '
                    f'fallback also failed: {fallback_error}'
                )
                raise ValueError(msg) from fallback_error

    def _should_use_parallel_heuristic(self, content: Any) -> bool:
        """Heuristic to determine if parallel processing would be beneficial."""
        if isinstance(content, list | tuple):
            return len(content) >= self._parallel_threshold
        elif isinstance(content, dict):
            return len(content) >= self._parallel_threshold
        elif hasattr(content, '__len__'):
            try:
                return len(content) >= self._parallel_threshold
            except (TypeError, AttributeError):
                pass
        return False

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics for this response."""
        stats = {
            'render_time_ms': self._render_time * 1000,
            'used_parallel': self._used_parallel,
            'cache_hit': self._cache_hit,
            'content_size_estimate': self._estimate_content_size(),
        }

        # Add serializer cache stats
        serializer_stats = self._serializer.get_cache_stats()
        stats.update({f'cache_{k}': v for k, v in serializer_stats.items()})

        return stats

    def _estimate_content_size(self) -> int:
        """Estimate the size of the content for performance tracking."""
        try:
            if isinstance(self._content, list | tuple):
                return len(self._content)
            elif isinstance(self._content, dict):
                return len(self._content)
            elif hasattr(self._content, '__len__'):
                return len(self._content)
            else:
                return 1  # Single object
        except (TypeError, AttributeError):
            return 0

    def clear_cache(self) -> None:
        """Clear the serialization cache."""
        self._serializer.clear_cache()


class BatchJSONResponse(Response):
    """Response class for efficiently serializing multiple objects into a JSON array.

    Optimized for scenarios where you need to return many similar objects.
    """

    media_type = 'application/json'

    def __init__(
        self,
        objects: list,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        parallel_threshold: int = 5000,  # Higher threshold for batch operations
        combine_as_array: bool = True,
    ) -> None:
        """Initialize batch JSON response for multiple objects."""
        self._objects = objects
        self._combine_as_array = combine_as_array

        # Initialize batch serializer
        self._batch_serializer = BatchJSONSerializer(
            parallel_threshold=parallel_threshold, max_depth=32, cache_size_limit=2000
        )

        self._render_time = 0.0

        super().__init__(objects, status_code, headers, media_type, background)

    def render(self, content: Any) -> bytes:
        """Render multiple objects to JSON using batch processing."""
        start_time = time.perf_counter()

        try:
            if self._combine_as_array:
                # Combine all objects into a single JSON array
                result = self._batch_serializer.serialize_batch_to_array(self._objects)
            else:
                # Serialize each object separately and combine manually
                individual_results = self._batch_serializer.serialize_batch(
                    self._objects
                )
                # Join with newlines for JSONL format
                result = b'\n'.join(individual_results)

            self._render_time = time.perf_counter() - start_time
            return bytes(result)

        except Exception as e:
            # Fallback to standard JSON serialization
            import json

            try:
                if self._combine_as_array:
                    fallback_result = json.dumps(
                        self._objects, separators=(',', ':')
                    ).encode('utf-8')
                else:
                    # JSONL fallback
                    lines = [
                        json.dumps(obj, separators=(',', ':')) for obj in self._objects
                    ]
                    fallback_result = '\n'.join(lines).encode('utf-8')

                self._render_time = time.perf_counter() - start_time
                return fallback_result
            except Exception as fallback_error:
                msg = (
                    f'Batch JSON serialization failed: {e}, '
                    f'fallback also failed: {fallback_error}'
                )
                raise ValueError(msg) from fallback_error

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics for batch processing."""
        return {
            'render_time_ms': self._render_time * 1000,
            'object_count': len(self._objects),
            'combine_as_array': self._combine_as_array,
        }


# Convenience functions for easier usage
def json_response(
    content: Any,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    parallel_threshold: int = 100,
    **kwargs,
) -> OptimizedJSONResponse:
    """Create an optimized JSON response with automatic parallel processing.

    Args:
        content: The content to serialize
        status_code: HTTP status code
        headers: Optional HTTP headers
        parallel_threshold: Minimum size for parallel processing
        **kwargs: Additional arguments passed to OptimizedJSONResponse

    Returns:
        OptimizedJSONResponse instance

    """
    return OptimizedJSONResponse(
        content=content,
        status_code=status_code,
        headers=headers,
        parallel_threshold=parallel_threshold,
        **kwargs,
    )


def batch_json_response(
    objects: list,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    parallel_threshold: int = 50,
    **kwargs,
) -> BatchJSONResponse:
    """Create a batch JSON response for multiple objects.

    Args:
        objects: List of objects to serialize
        status_code: HTTP status code
        headers: Optional HTTP headers
        parallel_threshold: Minimum size for parallel processing
        **kwargs: Additional arguments passed to BatchJSONResponse

    Returns:
        BatchJSONResponse instance

    """
    return BatchJSONResponse(
        objects=objects,
        status_code=status_code,
        headers=headers,
        parallel_threshold=parallel_threshold,
        **kwargs,
    )
