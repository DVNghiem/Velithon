# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
import typing

import orjson
from pydantic import BaseModel, ValidationError
from pydash import get

from velithon.exceptions import BadRequestException
from velithon.exceptions import ValidationException
from velithon.requests import Request


class ParamParser:
    def __init__(self, request: Request):
        self.request = request

    def parse_data_by_name(self, param_name: str) -> dict:
        param_name = param_name.lower()
        data_parsers = {
            "query_params": self._parse_query_params,
            "path_params": self._parse_path_params,
            "form_data": self._parse_form_data,
        }

        parser = data_parsers.get(param_name)
        if not parser:
            raise BadRequestException(details={"message": f"Invalid parameter name: {param_name}"})
        return parser()

    def _parse_query_params(self) -> dict:
        query_params = self.request.query_params
        return {k: v[0] for k, v in query_params.items()}

    def _parse_path_params(self) -> dict:
        return dict(self.request.path_params.items())

    def _parse_form_data(self) -> dict:
        return self.request.json()


class InputHandler:
    def __init__(self, request):
        self.request = request
        self.param_parser = ParamParser(request)

    async def parse_pydantic_model(self, param_name: str, model_class: typing.Type[BaseModel]) -> BaseModel:
        try:
            data = self.param_parser.parse_data_by_name(param_name)
            return model_class(**data)
        except ValidationError as e:
            invalid_fields = orjson.loads(e.json())
            raise ValidationException(
                details=[
                    {
                        "field": get(item, "loc")[0],
                        "msg": get(item, "msg"),
                    }
                    for item in invalid_fields
                ]
            )

    async def handle_special_params(self, param_name: str) -> typing.Any:
        special_params = {
            "request": lambda: self.request,
        }
        return special_params.get(param_name, lambda: None)()

    async def get_input_handler(self, signature: inspect.Signature) -> typing.Dict[str, typing.Any]:
        """
        Parse the request data and return the kwargs for the handler
        """
        kwargs = {}

        for param in signature.parameters.values():
            name = param.name
            ptype = param.annotation

            # Handle Pydantic models
            if isinstance(ptype, type) and issubclass(ptype, BaseModel):
                kwargs[name] = await self.parse_pydantic_model(name, ptype)
                continue

            # Handle special parameters
            special_value = await self.handle_special_params(name)
            if special_value is not None:
                kwargs[name] = special_value
        return kwargs