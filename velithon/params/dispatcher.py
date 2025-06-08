# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
import typing

from pydantic import BaseModel

from velithon._utils import is_async_callable, run_in_threadpool
from velithon.cache import cache_manager, signature_cache
from velithon.exceptions import HTTPException
from velithon.requests import Request
from velithon.responses import JSONResponse, Response

from .parser import InputHandler


# Cache for function signatures to avoid repeated inspection
@signature_cache()
def _get_cached_signature(func: typing.Any) -> inspect.Signature:
    """Get cached function signature."""
    return inspect.signature(func)


# Cache for class-based endpoint method lookups
@signature_cache()
def _get_method_lookup_cache(handler_class: type, method_name: str) -> typing.Any:
    """Cache method lookups for class-based endpoints."""
    return getattr(handler_class, method_name, None)


# Register caches with the global cache manager
cache_manager.register_lru_cache("signature_cache", _get_cached_signature)
cache_manager.register_lru_cache("method_lookup_cache", _get_method_lookup_cache)


async def dispatch(handler: typing.Any, request: Request) -> Response:
    """OPTIMIZED request dispatcher with caching and reduced overhead."""
    is_class_based = not (
        inspect.isfunction(handler) or inspect.iscoroutinefunction(handler)
    )

    if is_class_based:
        method_name = request.scope.method.lower()
        # Use cached method lookup
        handler_method = _get_method_lookup_cache(handler, method_name)
        if not handler_method:
            raise HTTPException(405, "Method Not Allowed", "METHOD_NOT_ALLOWED")

        # Create instance only when needed
        endpoint_instance = handler()
        handler = getattr(endpoint_instance, method_name)
        signature = _get_cached_signature(handler)
    else:
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

    # Fast response handling
    if not isinstance(response, Response):
        if isinstance(_response_type, type) and issubclass(_response_type, BaseModel):
            response = _response_type.model_validate(response).model_dump(mode="json")
        response = JSONResponse(
            content={"message": response},
            status_code=200,
        )
    return response
