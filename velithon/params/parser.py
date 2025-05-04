# -*- coding: utf-8 -*-
from __future__ import annotations

import inspect
from typing import Annotated, Any, Dict, Optional, Union, get_args, get_origin

import orjson
from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from pydash import get

from velithon.datastructures import FormData, Headers, QueryParams, UploadFile
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

    def _parse_query_params(self) -> dict:
        query_params = self.request.query_params
        return {k: v[0] if isinstance(v, list) else v for k, v in query_params.items()}

    def _parse_path_params(self) -> dict:
        path_params = self.request.path_params or self.request.scope.get(
            "path_params", {}
        )
        return dict(path_params.items())

    async def _parse_form_data(self) -> dict:
        async with self.request.form() as form:
            return form

    async def _parse_json_body(self) -> dict:
        return await self.request.json()

    async def _parse_file_data(self) -> dict:
        return await self.request.files()


class PrimitiveParser:
    def __init__(self, param_parser: ParamParser):
        self.param_parser = param_parser

    async def parse(
        self, param_name: str, annotation: Any, param_type: str, default: Any = None
    ) -> Any:
        data = await self.param_parser.parse_data(param_type)
        value = data.get(param_name)
        if value is None:
            if default is not None and default is not ...:
                return default
            raise BadRequestException(
                details={"message": f"Missing required parameter: {param_name}"}
            )
        try:
            if annotation is int:
                return int(value)
            elif annotation is float:
                return float(value)
            elif annotation is bool:
                return value.lower() in ("true", "1", "yes")
            elif annotation is str:
                return str(value)
            elif annotation is bytes and param_type == "file_data":
                return value[0] if isinstance(value, tuple) else value
            elif get_origin(annotation) is list:
                item_type = get_args(annotation)[0]
                values = value if isinstance(value, list) else [value]
                if item_type is str:
                    return values
                elif item_type is int:
                    return [int(v) for v in values]
                elif item_type is float:
                    return [float(v) for v in values]
                elif item_type is bool:
                    return [v.lower() in ("true", "1", "yes") for v in values]
                elif item_type is bytes and param_type == "file_data":
                    return [v[0] if isinstance(v, tuple) else v for v in values]
                else:
                    raise ValueError(f"Unsupported list item type: {item_type}")
            else:
                raise ValueError(f"Unsupported primitive type: {annotation}")
        except (ValueError, TypeError) as e:
            raise ValidationException(
                details={
                    "field": param_name,
                    "msg": f"Invalid value for type {annotation}: {str(e)}",
                }
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
    def __init__(self, request: Request):
        self.request = request

    async def parse(self, param_name: str, annotation: Any, default: Any = None) -> Any:
        if isinstance(annotation, type):
            if issubclass(annotation, Request):
                return self.request
            elif issubclass(annotation, Dict):
                return self.request.scope
            elif issubclass(annotation, UploadFile):
                files = await self.request.files()
                file_data = files.get(param_name)
                if file_data is None:
                    if default is not None and default is not ...:
                        return default
                    raise BadRequestException(
                        details={"message": f"Missing file for parameter: {param_name}"}
                    )
                if isinstance(file_data, list):
                    file_data = file_data[0]  # Take first file for single UploadFile
                content, filename, content_type = file_data
                if not content:
                    raise ValidationException(
                        details={"field": param_name, "msg": "Empty file content"}
                    )
                return UploadFile(
                    filename=filename, content=content, content_type=content_type
                )

        if get_origin(annotation) is list and get_args(annotation)[0] is UploadFile:
            files = await self.request.files()
            file_data = files.get(param_name, [])
            if not file_data and default is not None and default is not ...:
                return default
            if not isinstance(file_data, list):
                file_data = [file_data]
            result = [
                UploadFile(filename=v[1], content=v[0], content_type=v[2])
                for v in file_data
                if v[0]
            ]
            if not result and file_data:
                raise ValidationException(
                    details={"field": param_name, "msg": "Empty file content"}
                )
            return result

        return None


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
            (m for m in metadata if isinstance(m, (Query, Path, Body, Form, File))),
            None,
        )
        if not param_metadata:
            return None

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
            default = param.default

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
                    if self.request.scope["method"].upper() == "GET"
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
                    if self.request.scope["method"].upper() == "GET"
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
