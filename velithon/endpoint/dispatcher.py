# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
import traceback
import typing

import orjson
from pydantic import BaseModel

from velithon._utils import is_async_callable, run_in_threadpool
from velithon.exceptions import HTTPException
from velithon.requests import Request
from velithon.responses import JSONResponse, Response

from .parser import InputHandler


async def dispatch(
    handler, request: Request
) -> Response:
    try:
        is_async = is_async_callable(handler)
        signature = inspect.signature(handler)
        input_handler = InputHandler(request)
        _response_type = signature.return_annotation
        _kwargs = await input_handler.get_input_handler(signature)

        if is_async:
            response = await handler(**_kwargs)  # type: ignore
        else:
            response = await run_in_threadpool(handler, **_kwargs)
        if not isinstance(response, Response):
            if isinstance(_response_type, type) and issubclass(
                _response_type, BaseModel
            ):
                response = _response_type.model_validate(response).model_dump(
                    mode="json"
                )  # type: ignore
            response = JSONResponse(
                content={"message": response, "error_code": None},
                status_code=200,
            )

    except Exception as e:
        _res: typing.Dict = {"message": "", "error_code": "UNKNOWN_ERROR"}
        if isinstance(e, HTTPException):
            _res = e.to_dict()
            _status = e.status_code
        else:
            traceback.print_exc()
            _res["message"] = str(e)
            _status = 400
        response = JSONResponse(
            content=orjson.dumps(_res),
            status_code=_status,
        )
    return response
