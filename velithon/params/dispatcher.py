"""Request dispatcher module for controller method calls and response generation.

This module provides the main dispatch logic that handles parameter injection,
method execution, and automatic response serialization for controllers.
"""

from __future__ import annotations

import inspect
import typing

from pydantic import BaseModel

from velithon._utils import is_async_callable, run_in_threadpool
from velithon.cache import cache_manager, signature_cache
from velithon.requests import Request
from velithon.responses import JSONResponse, Response

from .parser import InputHandler


# Cache for function signatures to avoid repeated inspection
@signature_cache()
def _get_cached_signature(func: typing.Any) -> inspect.Signature:
    """Get cached function signature."""
    return inspect.signature(func)

# Register caches with the global cache manager
cache_manager.register_lru_cache('signature_cache', _get_cached_signature)


async def dispatch(handler: typing.Any, request: Request) -> Response:
    """Dispatches a request to the given handler, performing parameter injection,.

    method execution, and automatic response serialization.

    """
    signature = _get_cached_signature(handler)

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
