"""Request dispatcher module for controller method calls and response generation.

This module provides the main dispatch logic that handles parameter injection,
method execution, and automatic response serialization for controllers.
"""

from __future__ import annotations

import inspect
import typing

from pydantic import BaseModel

from velithon._utils import is_async_callable, run_in_threadpool
from velithon.cache import cache_manager
from velithon.requests import Request
from velithon.responses import JSONResponse, Response

from .parser import InputHandler


# Cache for function signatures to avoid repeated inspection
class _SignatureCache:
    """Custom signature cache with proper cache_clear interface."""

    def __init__(self):
        """Initialize the signature cache."""
        self._cache: dict[str, inspect.Signature] = {}

    def get(self, cache_key: str, func: typing.Any) -> inspect.Signature:
        """Get cached function signature using a cache key for consistency."""
        if cache_key not in self._cache:
            self._cache[cache_key] = inspect.signature(func)
        return self._cache[cache_key]

    def cache_clear(self) -> None:
        """Clear the signature cache."""
        self._cache.clear()

_signature_cache = _SignatureCache()


def _get_cached_signature(cache_key: str, func: typing.Any) -> inspect.Signature:
    """Get cached function signature using a cache key for consistency."""
    return _signature_cache.get(cache_key, func)

def _get_signature_cache_key(func: typing.Any) -> str:
    """Generate a consistent cache key for function signatures.

    For bound methods, use the method name and class to ensure consistent
    caching across different instances of the same class.
    """
    if hasattr(func, '__self__') and hasattr(func, '__func__'):
        # Bound method - use class and method name for consistent caching
        cls = func.__self__.__class__
        method_name = func.__func__.__name__
        return f"{cls.__module__}.{cls.__qualname__}.{method_name}"
    elif hasattr(func, '__name__'):
        # Regular function or unbound method
        module = getattr(func, '__module__', '')
        qualname = getattr(func, '__qualname__', func.__name__)
        return f"{module}.{qualname}"
    else:
        # Fallback for other callable objects
        return f"{type(func).__module__}.{type(func).__name__}.{id(func)}"

# Register caches with the global cache manager
cache_manager.register_lru_cache('signature_cache', _signature_cache)


async def dispatch(handler: typing.Any, request: Request) -> Response:
    """Dispatches a request to the given handler, performing parameter injection.

    This function handles method execution and automatic response serialization.
    """
    # Generate consistent cache key and get cached signature
    cache_key = _get_signature_cache_key(handler)
    signature = _get_cached_signature(cache_key, handler)

    # Pre-check if handler is async to avoid repeated calls
    is_async = is_async_callable(handler)

    # Optimize input handling
    input_handler = InputHandler(request)
    _response_type = signature.return_annotation
    _kwargs = await input_handler.get_input(signature)

    # Execute handler
    if is_async:
        response = await handler(**_kwargs)
    else:
        response = await run_in_threadpool(handler, **_kwargs)

    # Enhanced response handling with automatic serialization
    if not isinstance(response, Response):
        # Try automatic serialization first
        try:
            from velithon.serialization import auto_serialize_response

            response = auto_serialize_response(response, status_code=200)
        except (ImportError, TypeError):
            # Fallback to original logic for backward compatibility
            if isinstance(_response_type, type) and issubclass(
                _response_type, BaseModel
            ):
                response = _response_type.model_validate(response).model_dump(
                    mode='json'
                )
            response = JSONResponse(
                content={'message': response},
                status_code=200,
            )
    return response
