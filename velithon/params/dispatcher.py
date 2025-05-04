# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
import typing

from pydantic import BaseModel

from velithon._utils import is_async_callable, run_in_threadpool
from velithon.exceptions import HTTPException
from velithon.requests import Request
from velithon.responses import JSONResponse, Response

from .parser import InputHandler

async def dispatch(handler: typing.Any, request: Request) -> Response:
    is_class_based = not (inspect.isfunction(handler) or inspect.iscoroutinefunction(handler))
    if is_class_based:
        method_name = request.scope.method.lower()
        endpoint_instance = handler()
        handler_method = getattr(endpoint_instance, method_name, None)
        if not handler_method:
            raise HTTPException(405, "Method Not Allowed", "METHOD_NOT_ALLOWED")
        handler = handler_method
        signature = inspect.signature(handler)
    else:
        signature = inspect.signature(handler)

    is_async = is_async_callable(handler)
    input_handler = InputHandler(request)
    _response_type = signature.return_annotation
    _kwargs = await input_handler.get_input(signature)

    if is_async:
        response = await handler(**_kwargs)
    else:
        response = await run_in_threadpool(handler, **_kwargs)

    if not isinstance(response, Response):
        if isinstance(_response_type, type) and issubclass(_response_type, BaseModel):
            response = _response_type.model_validate(response).model_dump(mode="json")
        response = JSONResponse(
            content={"message": response, "error_code": None},
            status_code=200,
        )
    return response