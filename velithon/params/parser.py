from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Dict, Optional, Union, get_args, get_origin

import orjson
from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from pydash import get

from velithon.cache import parser_cache
from velithon.datastructures import FormData, Headers, QueryParams, UploadFile
from velithon.di import Provide
from velithon.exceptions import (
    BadRequestException,
    InvalidMediaTypeException,
    UnsupportParameterException,
    ValidationException,
)
from velithon.params.params import Body, File, Form, Path, Query
from velithon.requests import Request

# Performance optimization: Pre-compiled type converters
_TYPE_CONVERTERS = {
    int: int,
    float: float,
    str: str,
    bool: lambda v: str(v).lower() in ("true", "1", "yes", "on"),
    bytes: lambda v: v.encode() if isinstance(v, str) else v,
}


class ParameterResolver:
    def __init__(self, request: Request):
        self.request = request
        self.data_cache = {}
        self.type_handlers = {
            int: self._parse_primitive,
            float: self._parse_primitive,
            str: self._parse_primitive,
            bool: self._parse_primitive,
            bytes: self._parse_primitive,
            list: self._parse_list,
            Request: self._parse_special,
            FormData: self._parse_special,
            Headers: self._parse_special,
            QueryParams: self._parse_special,
            UploadFile: self._parse_special,
            dict: self._parse_special,
        }
        self.param_types = {
            Query: "query_params",
            Path: "path_params",
            Body: "json_body",
            Form: "form_data",
            File: "file_data",
        }

    async def _fetch_data(self, param_type: str) -> Any:
        """Fetch and cache request data for the given parameter type."""
        if param_type not in self.data_cache:
            parsers = {
                "query_params": lambda: self.request.query_params,
                "path_params": lambda: self.request.path_params,
                "form_data": self._get_form_data,
                "json_body": self.request.json,
                "file_data": self.request.files,
            }
            parser = parsers.get(param_type)
            if not parser:
                raise BadRequestException(
                    details={"message": f"Invalid parameter type: {param_type}"}
                )

            result = parser()
            # Check if the result is a coroutine and await it if necessary
            self.data_cache[param_type] = (
                await result if inspect.iscoroutine(result) else result
            )
        return self.data_cache[param_type]

    async def _get_form_data(self):
        """Helper to handle async context manager for form data."""
        async with self.request.form() as form:
            # Convert form data to a dictionary for Pydantic parsing
            return dict(form)

    def _get_type_key(self, annotation: Any) -> Any:
        """Determine the key for type dispatching, handling inheritance."""
        origin = get_origin(annotation)
        if origin in (list, Annotated, Union, Optional):
            if origin is Annotated:
                base_type = get_args(annotation)[0]
                return self._get_type_key(base_type)
            if origin in (Union, Optional) and any(
                t is type(None) for t in get_args(annotation)
            ):
                base_type = next(t for t in get_args(annotation) if t is not type(None))
                return self._get_type_key(base_type)
            return list
        # Handle Pydantic models by checking if annotation is a subclass of BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return BaseModel
        return annotation if isinstance(annotation, type) else type(annotation)

    async def _parse_primitive(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
    ) -> Any:
        """Parse primitive types (int, float, str, bool, bytes) - OPTIMIZED."""
        value = data.get(param_name)
        if value is None:
            if default is not None and default is not ...:
                return default
            if is_required:
                raise BadRequestException(
                    details={"message": f"Missing required parameter: {param_name}"}
                )

        try:
            # Use optimized type converters
            converter = _TYPE_CONVERTERS.get(annotation)
            if converter:
                return converter(value)

            # Fallback for bytes type
            if annotation is bytes:
                return value[0] if isinstance(value, tuple) else value
            return annotation(value)
        except (ValueError, TypeError) as e:
            raise ValidationException(
                details={
                    "field": param_name,
                    "msg": f"Invalid value for type {annotation}: {str(e)}",
                }
            )

    async def _parse_list(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
    ) -> Any:
        """Parse list types."""
        item_type = get_args(annotation)[0]
        values = data.get(param_name, [])
        if not isinstance(values, Sequence):
            values = [values]
        if not values and default is not None and default is not ...:
            return default
        if not values and is_required:
            raise BadRequestException(
                details={"message": f"Missing required parameter: {param_name}"}
            )

        if item_type in (int, float, str, bool, bytes):
            list_type_map = {
                str: lambda vs: vs,
                int: lambda vs: [int(v) for v in vs],
                float: lambda vs: [float(v) for v in vs],
                bool: lambda vs: [v.lower() in ("true", "1", "yes") for v in vs],
                bytes: lambda vs: [v[0] if isinstance(v, tuple) else v for v in vs],
            }
            try:
                return list_type_map[item_type](values)
            except (ValueError, TypeError) as e:
                raise ValidationException(
                    details={
                        "field": param_name,
                        "msg": f"Invalid list item type {item_type}: {str(e)}",
                    }
                )
        elif isinstance(item_type, type) and issubclass(item_type, BaseModel):
            try:
                return [item_type(**item) for item in values]
            except ValidationError as e:
                invalid_fields = orjson.loads(e.json())
                raise ValidationException(
                    details=[
                        {"field": get(item, "loc")[0], "msg": get(item, "msg")}
                        for item in invalid_fields
                    ]
                )
        raise BadRequestException(
            details={"message": f"Unsupported list item type: {item_type}"}
        )

    async def _parse_model(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
    ) -> Any:
        """Parse Pydantic models."""
        if not data and default is not None and default is not ...:
            return default
        if not data and is_required:
            raise BadRequestException(
                details={"message": f"Missing required parameter: {param_name}"}
            )
        try:
            # Accept any Mapping type for Pydantic model
            if isinstance(data, Mapping):
                return annotation(**data)
            raise ValueError("Invalid data format for model: expected a mapping")
        except ValidationError as e:
            invalid_fields = orjson.loads(e.json())
            raise ValidationException(
                details=[
                    {"field": get(item, "loc")[0], "msg": get(item, "msg")}
                    for item in invalid_fields
                ]
            )

    async def _parse_special(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
    ) -> Any:
        """Parse special types (Request, FormData, Headers, etc.)."""
        type_map = {
            Request: lambda: self.request,
            FormData: lambda: self.request.form().__aenter__(),
            Headers: lambda: self.request.headers,
            QueryParams: lambda: self.request.query_params,
            dict: lambda: self.request.scope,
            UploadFile: lambda: self._get_file(param_name, data, default, is_required),
        }
        handler = type_map.get(annotation)
        if handler:
            result = handler()
            return await result if inspect.iscoroutine(result) else result
        raise BadRequestException(
            details={"message": f"Unsupported special type: {annotation}"}
        )

    async def _get_file(
        self, param_name: str, data: Any, default: Any, is_required: bool
    ) -> Any:
        """Handle file uploads."""
        files = data.get(param_name)
        if not files and default is not None and default is not ...:
            return default
        if not files and is_required:
            raise BadRequestException(
                details={"message": f"Missing required parameter: {param_name}"}
            )
        if isinstance(files, Sequence) and get_origin(UploadFile) is list:
            if not all(isinstance(f, UploadFile) for f in files):
                raise BadRequestException(
                    details={
                        "message": f"Invalid file type for parameter: {param_name}"
                    }
                )
            return files
        return files[0] if files else None

    @parser_cache()
    def _resolve_param_metadata(
        self, param: inspect.Parameter
    ) -> tuple[Any, str, Any, bool]:
        """Cache parameter metadata (annotation, param_type, default, is_required)."""
        annotation = param.annotation
        default = (
            param.default if param.default is not inspect.Parameter.empty else None
        )
        is_required = default is None and param.default is inspect.Parameter.empty
        param_type = "query_params"  # Default

        if get_origin(annotation) is Annotated:
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
                raise InvalidMediaTypeException(
                    details={
                        "message": f"Unsupported parameter metadata for {param.name}: {annotation}"
                    }
                )

            if hasattr(param_metadata, "media_type"):
                if param_metadata.media_type != self.request.headers.get(
                    "Content-Type", ""
                ):
                    raise InvalidMediaTypeException(
                        details={
                            "message": f"Invalid media type for parameter: {param.name}"
                        }
                    )

            if isinstance(param_metadata, Provide):
                return base_type, "provide", param_metadata, is_required
            param_type = self.param_types.get(type(param_metadata), "query_params")
            metadata_default = (
                param_metadata.default
                if hasattr(param_metadata, "default")
                and param_metadata.default is not PydanticUndefined
                else None
            )
            default = metadata_default if metadata_default is not None else default
            annotation = base_type
            # If Form() is used, ensure param_type remains form_data even for BaseModel
            if isinstance(param_metadata, Form):
                return annotation, "form_data", default, is_required

        if annotation is inspect._empty:
            param_type = (
                "path_params"
                if param.name in self.request.path_params
                else "query_params"
            )
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            param_type = (
                "json_body"
                if self.request.scope.method.upper() != "GET"
                else "query_params"
            )
        elif (
            get_origin(annotation) is list
            and isinstance(get_args(annotation)[0], type)
            and issubclass(get_args(annotation)[0], BaseModel)
        ):
            param_type = (
                "json_body"
                if self.request.scope.method.upper() != "GET"
                else "query_params"
            )
        elif param.name in self.request.path_params:
            param_type = "path_params"

        return annotation, param_type, default, is_required

    async def resolve(self, signature: inspect.Signature) -> Dict[str, Any]:
        """Resolve all parameters for the given function signature."""
        kwargs = {}
        for param in signature.parameters.values():
            annotation, param_type, default, is_required = self._resolve_param_metadata(
                param
            )
            name = param.name

            if param_type == "provide":
                kwargs[name] = default  # Provide dependency injection
                continue

            type_key = self._get_type_key(annotation)
            # Special handling for BaseModel subclasses
            handler = self.type_handlers.get(type_key)
            if (
                not handler
                and isinstance(annotation, type)
                and issubclass(annotation, BaseModel)
            ):
                handler = self._parse_model
            if not handler:
                if default is not None and default is not ...:
                    kwargs[name] = default
                    continue
                raise UnsupportParameterException(
                    details={
                        "message": f"Unsupported parameter type for {name}: {annotation}"
                    }
                )
            data = await self._fetch_data(param_type)
            kwargs[name] = await handler(name, annotation, data, default, is_required)

        return kwargs


class InputHandler:
    def __init__(self, request: Request):
        self.resolver = ParameterResolver(request)

    async def get_input(self, signature: inspect.Signature) -> Dict[str, Any]:
        return await self.resolver.resolve(signature)
