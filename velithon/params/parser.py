# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
from typing import Annotated, Any, Dict, Type, get_args, get_origin, Callable

import orjson
from pydantic import BaseModel, ValidationError
from pydash import get

from velithon.exceptions import BadRequestException, ValidationException
from velithon.params.params import Body, Form, Path, Query, File

from velithon.requests import Request

class ParamParser:
    def __init__(self, request: Request):
        self.request = request

    async def parse_data_by_name(self, param_type: str) -> dict:
        param_type = param_type.lower()
        data_parsers = {
            "query_params": self._parse_query_params,
            "path_params": self._parse_path_params,
            "form_data": self._parse_form_data,
            "json_body": self._parse_json_body,
            "file_data": self._parse_file_data,
        }

        parser = data_parsers.get(param_type)
        if not parser:
            raise BadRequestException(details={"message": f"Invalid parameter type: {param_type}"})
        return parser()

    def _parse_query_params(self) -> dict:
        query_params = self.request.query_params
        return {k: v[0] if isinstance(v, list) else v for k, v in query_params.items()}

    def _parse_path_params(self) -> dict:
        path_params = self.request.path_params or self.request.scope.get("path_params", {})
        return dict(path_params.items())

    async def _parse_form_data(self) -> dict:
        return await self.request.form()

    async def _parse_json_body(self) -> dict:
        return await self.request.json()

    async def _parse_file_data(self) -> dict:
        return await self.request.files()

class InputHandler:
    def __init__(self, request: Request, receive: Callable = None, send: Callable = None):
        self.request = request
        self.receive = receive
        self.send = send
        self.param_parser = ParamParser(request)
        self._callable_count = 0  # Track number of Callable parameters processed

    async def parse_pydantic_model(self, param_name: str, model_class: Type[BaseModel], param_type: str, default: Any = None) -> BaseModel | None:
        try:
            data = await self.param_parser.parse_data_by_name(param_type)
            if not data and default is not None and default is not ...:
                return default
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
        except ValueError:
            if default is not None and default is not ...:
                return default
            raise BadRequestException(details={"message": f"Missing or invalid data for {param_name}"})

    async def parse_primitive(self, param_name: str, param_type: str, annotation: Any, metadata: Any = None, default: Any = None) -> Any:
        data = await self.param_parser.parse_data_by_name(param_type)
        value = data.get(param_name)
        if value is None:
            if metadata and hasattr(metadata, "default") and metadata.default is not ...:
                return metadata.default
            if default is not None and default is not ...:
                return default
            raise BadRequestException(details={"message": f"Missing required parameter: {param_name}"})
        try:
            if annotation is int:
                return int(value)
            elif annotation is float:
                return float(value)
            elif annotation is bool:
                return value.lower() in ("true", "1", "yes")
            elif annotation is bytes and param_type == "file_data":
                return value
            return value
        except (ValueError, TypeError):
            raise ValidationException(details={"field": param_name, "msg": f"Invalid value for type {annotation.__name__}"})

    async def handle_special_params(self, param_name: str, annotation: Any) -> Any:
        # Define special parameter types and their handlers
        special_params = [
            (Request, lambda: self.request),
            (Dict, lambda: self.request.scope),  # Assuming scope is a Dict; adjust if Scope is a specific type
            (Callable, lambda: self.receive if self._callable_count == 0 else self.send),
        ]

        # Check if annotation matches a special parameter type
        for expected_type, handler in special_params:
            if isinstance(annotation, type) and issubclass(annotation, expected_type):
                if expected_type is Callable:
                    self._callable_count += 1  # Increment for next Callable
                value = handler()
                if value is None:
                    raise BadRequestException(details={"message": f"Special parameter of type '{expected_type.__name__}' is not available"})
                return value

        return None

    async def get_input_handler(self, signature: inspect.Signature) -> Dict[str, Any]:
        kwargs = {}
        self._callable_count = 0  # Reset callable count for each signature
        for param in signature.parameters.values():
            name = param.name
            annotation = param.annotation
            default = param.default

            if get_origin(annotation) is Annotated:
                base_type, *metadata = get_args(annotation)
                param_metadata = next((m for m in metadata if isinstance(m, (Query, Path, Body, Form, File))), None)
                if param_metadata:
                    param_type = {
                        Query: "query_params",
                        Path: "path_params",
                        Body: "json_body",
                        Form: "form_data",
                        File: "file_data",
                    }.get(type(param_metadata), "query_params")
                    if isinstance(base_type, type) and issubclass(base_type, BaseModel):
                        kwargs[name] = await self.parse_pydantic_model(name, base_type, param_type, default)
                    else:
                        kwargs[name] = await self.parse_primitive(name, param_type, base_type, param_metadata, default)
                    continue
                annotation = base_type

            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                param_type = "query_params" if self.request.scope["method"].upper() == "GET" else "json_body"
                kwargs[name] = await self.parse_pydantic_model(name, annotation, param_type, default)
                continue

            special_value = await self.handle_special_params(name, annotation)
            if special_value is not None:
                kwargs[name] = special_value
                continue

            if annotation in (int, float, str, bool):
                param_type = "query_params" if name not in self.request.path_params else "path_params"
                kwargs[name] = await self.parse_primitive(name, param_type, annotation, default=default)
                continue

            if default is not None and default is not ...:
                kwargs[name] = default

        return kwargs