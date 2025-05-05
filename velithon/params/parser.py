# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
from collections.abc import Sequence
from typing import Annotated, Any, Dict, Optional, Union, get_args, get_origin

import orjson
from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from pydash import get

from velithon.datastructures import FormData, Headers, QueryParams, UploadFile
from velithon.di import Provide
from velithon.exceptions import BadRequestException, ValidationException
from velithon.params.params import Body, File, Form, Path, Query
from velithon.requests import Request


class ParamParser:
    def __init__(self, request: Request):
        self.request = request

    async def parse_data(self, param_type: str) -> dict:
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
            raise BadRequestException(
                details={"message": f"Invalid parameter type: {param_type}"}
            )
        return await parser()

    async def _parse_query_params(self) -> dict:
        query_params = self.request.query_params
        return query_params

    async def _parse_path_params(self) -> dict:
        path_params = self.request.path_params or self.request.scope.get(
            "path_params", {}
        )
        return path_params

    async def _parse_form_data(self) -> dict:
        async with self.request.form() as form:
            return form

    async def _parse_json_body(self) -> dict:
        return await self.request.json()

    async def _parse_file_data(self) -> dict:
        return await self.request.files()


class PrimitiveParser:
    def __init__(self, param_parser: 'ParamParser'):
        self.param_parser = param_parser

    async def parse(self, param_name: str, annotation: Any, param_type: str, default: Any = None) -> Any:
        data = await self.param_parser.parse_data(param_type)
        value = data.get(param_name)

        if value is None:
            if default is not None and default is not ...:
                return default
            raise BadRequestException(details={"message": f"Missing required parameter: {param_name}"})

        try:
            # Handle basic primitive types
            type_map = {
                int: int,
                float: float,
                bool: lambda v: v.lower() in ("true", "1", "yes"),
                str: str,
                bytes: lambda v: v[0] if param_type == "file_data" and isinstance(v, tuple) else v
            }
            if annotation in type_map:
                return type_map[annotation](value)

            # Handle list types
            if get_origin(annotation) is list:
                item_type = get_args(annotation)[0]
                values = value if isinstance(value, Sequence) else [value]

                list_type_map = {
                    str: lambda vs: vs,
                    int: lambda vs: [int(v) for v in vs],
                    float: lambda vs: [float(v) for v in vs],
                    bool: lambda vs: [v.lower() in ("true", "1", "yes") for v in vs],
                    bytes: lambda vs: [v[0] if param_type == "file_data" and isinstance(v, tuple) else v for v in vs]
                }
                if item_type in list_type_map:
                    return list_type_map[item_type](values)
                
                raise ValueError(f"Unsupported list item type: {item_type}")

            raise ValueError(f"Unsupported primitive type: {annotation}")

        except (ValueError, TypeError) as e:
            raise ValidationException(
                details={"field": param_name, "msg": f"Invalid value for type {annotation}: {str(e)}"}
            )

class ModelParser:
    def __init__(self, param_parser: ParamParser):
        self.param_parser = param_parser

    async def parse(
        self, param_name: str, model_class: Any, param_type: str, default: Any = None
    ) -> Any:
        try:
            data = await self.param_parser.parse_data(param_type)
            if not data and default is not None and default is not ...:
                return default

            if get_origin(model_class) is list:
                item_class = get_args(model_class)[0]
                if not isinstance(item_class, type) or not issubclass(
                    item_class, BaseModel
                ):
                    raise ValueError(
                        f"List item type must be a BaseModel, got {item_class}"
                    )
                if not isinstance(data, list):
                    data = [data]
                return [item_class(**item) for item in data]

            if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                return model_class(**data)

            raise ValueError(f"Unsupported model type: {model_class}")
        except ValidationError as e:
            invalid_fields = orjson.loads(e.json())
            raise ValidationException(
                details=[
                    {"field": get(item, "loc")[0], "msg": get(item, "msg")}
                    for item in invalid_fields
                ]
            )
        except (ValueError, TypeError) as e:
            if default is not None and default is not ...:
                return default
            raise BadRequestException(
                details={"message": f"Invalid data for {param_name}: {str(e)}"}
            )


class SpecialTypeParser:
    def __init__(self, request: 'Request'):
        self.request = request

    async def parse(self, param_name: str, annotation: Any, default: Any = None) -> Any:
        # Handle single special types
        type_map = {
            'Request': lambda: self.request,
            'FormData': lambda: self.request.form().__aenter__(),
            'Headers': lambda: self.request.headers,
            'QueryParams': lambda: self.request.query_params,
            'Dict': lambda: self.request.scope,
            'UploadFile': lambda: self._get_file(param_name, default)
        }

        try:
            # Check if annotation is a class and matches a special type
            if isinstance(annotation, type):
                for type_name, handler in type_map.items():
                    if issubclass(annotation, globals().get(type_name, object)):
                        result = handler()
                        return await result if inspect.iscoroutine(result) else result

            # Handle list of UploadFile
            if get_origin(annotation) is list and get_args(annotation)[0] is UploadFile:
                files = (await self.request.files()).get(param_name)
                if not files and default is not None and default is not ...:
                    return default
                files = files if isinstance(files, Sequence) else [files]
                if not all(isinstance(file, UploadFile) for file in files):
                    raise BadRequestException(
                        details={"message": f"Invalid file type for parameter: {param_name}"}
                    )
                return files

            return None

        except (ValueError, TypeError) as e:
            raise BadRequestException(
                details={"message": f"Invalid value for parameter {param_name}: {str(e)}"}
            )

    async def _get_file(self, param_name: str, default: Any) -> Any:
        files = (await self.request.files()).get(param_name)
        if not files and default is not None and default is not ...:
            return default
        return files[0] if files else None

class AnnotatedParser:
    def __init__(
        self,
        primitive_parser: PrimitiveParser,
        model_parser: ModelParser,
        param_parser: ParamParser,
    ):
        self.primitive_parser = primitive_parser
        self.model_parser = model_parser
        self.param_parser = param_parser
        self.param_types = {
            Query: "query_params",
            Path: "path_params",
            Body: "json_body",
            Form: "form_data",
            File: "file_data",
        }

    async def parse(self, param_name: str, annotation: Any, default: Any = None) -> Any:
        if get_origin(annotation) is not Annotated:
            return None

        base_type, *metadata = get_args(annotation)
        param_metadata = next(
            (
                m
                for m in metadata
                if isinstance(m, (Query, Path, Body, Form, File, Provide))
            ),
            None,
        )
        if not param_metadata:
            return None
        # Bypass Provide metadata
        # Provide is used for dependency injection
        # and should not be parsed as a parameter
        if isinstance(param_metadata, Provide):
            return param_metadata

        param_type = self.param_types.get(type(param_metadata), "query_params")
        metadata_default = (
            param_metadata.default
            if hasattr(param_metadata, "default")
            and param_metadata.default is not PydanticUndefined
            else None
        )
        effective_default = (
            metadata_default if metadata_default is not None else default
        )
        # Handle Optional or Union with None
        is_optional = get_origin(base_type) in (Union, Optional) and type(
            None
        ) in get_args(base_type)
        if is_optional:
            base_type = next(t for t in get_args(base_type) if t is not type(None))

        # Parse data
        data = await self.param_parser.parse_data(param_type)
        if not data and effective_default is not None and effective_default is not ...:
            return effective_default

        # Handle dict
        if base_type is dict:
            return data if data else {}

        # Handle list of items
        if get_origin(base_type) is list:
            item_type = get_args(base_type)[0]
            values = data.get(param_name, []) if isinstance(data, dict) else data
            if not isinstance(values, list):
                values = [values]
            if not values and effective_default is not None:
                return effective_default
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                return await self.model_parser.parse(
                    param_name, base_type, param_type, effective_default
                )
            elif item_type in (int, float, str, bool, bytes):
                return await self.primitive_parser.parse(
                    param_name, base_type, param_type, effective_default
                )
            else:
                raise BadRequestException(
                    details={"message": f"Unsupported list item type: {item_type}"}
                )

        # Handle BaseModel
        if isinstance(base_type, type) and issubclass(base_type, BaseModel):
            return await self.model_parser.parse(
                param_name, base_type, param_type, effective_default
            )

        # Handle primitive types
        if base_type in (int, float, str, bool, bytes):
            return await self.primitive_parser.parse(
                param_name, base_type, param_type, effective_default
            )

        # Fallback for custom types
        if base_type in (FormData, QueryParams, Headers):
            return data

        raise BadRequestException(
            details={"message": f"Unsupported Annotated type: {base_type}"}
        )


class InputHandler:
    def __init__(self, request: Request):
        self.request = request
        self.param_parser = ParamParser(request)
        self.primitive_parser = PrimitiveParser(self.param_parser)
        self.model_parser = ModelParser(self.param_parser)
        self.special_parser = SpecialTypeParser(request)
        self.annotated_parser = AnnotatedParser(
            self.primitive_parser, self.model_parser, self.param_parser
        )

    async def get_input(self, signature: inspect.Signature) -> Dict[str, Any]:
        kwargs = {}
        for param in signature.parameters.values():
            name = param.name
            annotation = param.annotation
            default = (
                param.default if param.default is not inspect.Parameter.empty else None
            )

            # Try special types
            value = await self.special_parser.parse(name, annotation, default)
            if value is not None:
                kwargs[name] = value
                continue

            # Try annotated types
            value = await self.annotated_parser.parse(name, annotation, default)
            if value is not None:
                kwargs[name] = value
                continue

            # Try Pydantic models
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                param_type = (
                    "query_params"
                    if self.request.scope.method.upper() == "GET"
                    else "json_body"
                )
                kwargs[name] = await self.model_parser.parse(
                    name, annotation, param_type, default
                )
                continue

            # Try list of Pydantic models
            if (
                get_origin(annotation) is list
                and isinstance(get_args(annotation)[0], type)
                and issubclass(get_args(annotation)[0], BaseModel)
            ):
                param_type = (
                    "query_params"
                    if self.request.scope.method.upper() == "GET"
                    else "json_body"
                )
                kwargs[name] = await self.model_parser.parse(
                    name, annotation, param_type, default
                )
                continue

            # Try primitive types
            if annotation in (int, float, str, bool):
                param_type = (
                    "query_params"
                    if name not in self.request.path_params
                    else "path_params"
                )
                kwargs[name] = await self.primitive_parser.parse(
                    name, annotation, param_type, default
                )
                continue

            # Try list of primitive types
            if get_origin(annotation) is list and get_args(annotation)[0] in (
                int,
                float,
                str,
                bool,
            ):
                param_type = (
                    "query_params"
                    if name not in self.request.path_params
                    else "path_params"
                )
                kwargs[name] = await self.primitive_parser.parse(
                    name, annotation, param_type, default
                )
                continue

            # Use default if provided
            if default is not None and default is not ...:
                kwargs[name] = default
                continue

            raise BadRequestException(
                details={
                    "message": f"Unsupported parameter type for {name}: {annotation}"
                }
            )
        return kwargs
