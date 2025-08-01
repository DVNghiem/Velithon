"""Parameter parsing and validation for Velithon framework.

This module provides functionality for parsing and validating HTTP request
parameters including query parameters, path parameters, and request bodies.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Optional, Union, get_args, get_origin

import orjson
from jsonschema import ValidationError as JsonSchemaError
from jsonschema import validate
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
from velithon.params.params import Body, Cookie, File, Form, Header, Path, Query
from velithon.requests import Request

logger = logging.getLogger(__name__)

def _convert_underscore_to_hyphen(name: str) -> str:
    """Convert underscore to hyphen for parameter name aliases."""
    return name.replace('_', '-')

def _is_auth_dependency(annotation: Any) -> bool:
    """Check if a parameter annotation represents a dependency.

    Args:
        annotation: The parameter annotation to check

    Returns:
        True if this is a dependency, False otherwise

    """
    if get_origin(annotation) is Annotated:
        _, *metadata = get_args(annotation)
        return any(isinstance(meta, (Provide)) for meta in metadata)
    return False

# Performance optimization: Pre-compiled type converters
_TYPE_CONVERTERS = {
    int: int,
    float: float,
    str: str,
    bool: lambda v: str(v).lower() in ('true', '1', 'yes', 'on'),
    bytes: lambda v: v.encode() if isinstance(v, str) else v,
}

class ParameterResolver:
    """Parameter resolver for Velithon request handlers."""

    def __init__(self, request: Request):
        """Initialize the ParameterResolver with the request."""
        self.request = request
        self.data_cache = {}  # Per-request cache
        self._lock = asyncio.Lock()  # Ensure thread-safety for async access
        self.type_handlers = {
            int: self._parse_primitive,
            float: self._parse_primitive,
            str: self._parse_primitive,
            bool: self._parse_primitive,
            bytes: self._parse_primitive,
            list: self._parse_list,
            dict: self._parse_dict,
            Union: self._parse_union,
            Request: self._parse_special,
            FormData: self._parse_special,
            Headers: self._parse_special,
            QueryParams: self._parse_special,
            UploadFile: self._parse_special,
        }
        self.custom_handlers = {}  # Map custom types to handlers
        self.param_types = {
            Query: 'query_params',
            Path: 'path_params',
            Body: 'json_body',
            Form: 'form_data',
            File: 'file_data',
            Header: 'headers',
            Cookie: 'cookies',
        }

    def register_custom_handler(self, type_: type, handler: callable):
        """Register a custom type handler."""
        self.custom_handlers[type_] = handler

    async def _fetch_data(self, param_type: str) -> Any:
        """Fetch and cache request data for the given parameter type."""
        async with self._lock:
            if param_type not in self.data_cache:
                parsers = {
                    'query_params': lambda: self.request.query_params,
                    'path_params': lambda: self.request.path_params,
                    'form_data': self._get_form_data,
                    'json_body': self.request.json,
                    'file_data': self.request.files,
                    'headers': lambda: self.request.headers,
                    'cookies': lambda: self.request.cookies,
                }
                parser = parsers.get(param_type)
                if not parser:
                    raise BadRequestException(
                        details={'message': f'Invalid parameter type: {param_type}'}
                    )

                result = parser()
                self.data_cache[param_type] = (
                    await result if inspect.iscoroutine(result) else result
                )
            return self.data_cache[param_type]

    def _get_param_value_with_alias(
        self, data: Any, param_name: str, param_metadata: Any = None
    ) -> Any:
        """Get parameter value from data, trying the actual parameter name.

        Also tries explicit alias and auto-generated alias (underscore to hyphen).
        """
        if param_metadata and hasattr(param_metadata, 'alias') and param_metadata.alias:
            value = get(data, param_metadata.alias)
            if value is not None:
                return value

        value = get(data, param_name)
        if value is not None:
            return value

        if '_' in param_name:
            auto_alias = _convert_underscore_to_hyphen(param_name)
            value = get(data, auto_alias)
            if value is not None:
                return value

        return None

    async def _get_form_data(self):
        """Return form data, preserving multi-valued fields."""
        form = await self.request._get_form()
        result = {}
        for key, value in form.multi_items():
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        return result

    def _get_type_key(self, annotation: Any) -> Any:
        """Determine the key for type dispatching, handling nested types."""
        origin = get_origin(annotation)
        if origin in (list, Annotated, Union, Optional, dict):
            if origin is Annotated:
                base_type = get_args(annotation)[0]
                return self._get_type_key(base_type)
            if origin in (Union, Optional):
                non_none_types = [
                    t for t in get_args(annotation)
                    if t is not type(None)
                ]
                if len(non_none_types) == 1:
                    return self._get_type_key(non_none_types[0])
                return Union
            if origin is list:
                args = get_args(annotation)
                return list if not args else (list, self._get_type_key(args[0]))
            if origin is dict:
                args = get_args(annotation)
                return dict if not args else (dict, self._get_type_key(args[1]))
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
        param_metadata: Any = None,
    ) -> Any:
        """Parse primitive types (int, float, str, bool, bytes)."""
        value = self._get_param_value_with_alias(data, param_name, param_metadata)
        if value is None:
            if default is not None and default is not ...:
                return default
            if is_required:
                raise BadRequestException(
                    details={'message': f'Missing required parameter: {param_name}'}
                )

        try:
            converter = _TYPE_CONVERTERS.get(annotation)
            if converter:
                return converter(value)
            return annotation(value)
        except (ValueError, TypeError) as e:
            raise ValidationException(
                details={
                    'field': param_name,
                    'msg': f'Invalid value for type {annotation.__name__}: {e!s}',
                    'expected_type': annotation.__name__,
                    'received_value': str(value)[:100],
                    'request': f'{self.request.method} {self.request.url}',
                }
            ) from e

    async def _parse_list(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
        param_metadata: Any = None,
    ) -> Any:
        """Parse list types, including query parameter arrays."""
        values = self._get_param_value_with_alias(data, param_name, param_metadata)
        if values is None:
            values = []
        if isinstance(values, str):
            values = [v.strip() for v in values.split(',') if v.strip()]
        elif not isinstance(values, Sequence):
            values = [values]
        if not values and default is not None and default is not ...:
            return default
        if not values and is_required:
            raise BadRequestException(
                details={'message': f'Missing required parameter: {param_name}'}
            )

        item_type = get_args(annotation)[0]
        if item_type in (int, float, str, bool, bytes):
            list_type_map = {
                str: lambda vs: vs,
                int: lambda vs: [int(v) for v in vs],
                float: lambda vs: [float(v) for v in vs],
                bool: lambda vs: [v.lower() in ('true', '1', 'yes') for v in vs],
                bytes: lambda vs: [v[0] if isinstance(v, tuple) else v for v in vs],
            }
            try:
                return list_type_map[item_type](values)
            except (ValueError, TypeError) as e:
                raise ValidationException(
                    details={
                        'field': param_name,
                        'msg': f'Invalid list item type {item_type}: {e!s}',
                    }
                ) from e
        elif isinstance(item_type, type) and issubclass(item_type, BaseModel):
            try:
                return [item_type(**item) for item in values]
            except ValidationError as e:
                invalid_fields = orjson.loads(e.json())
                raise ValidationException(
                    details=[
                        {'field': get(item, 'loc')[0], 'msg': get(item, 'msg')}
                        for item in invalid_fields
                    ]
                ) from e
        elif item_type is UploadFile:
            if not all(isinstance(v, UploadFile) for v in values):
                raise BadRequestException(
                    details={
                        'message': f'Invalid file type for parameter: {param_name}'
                    }
                )
            return values
        raise BadRequestException(
            details={'message': f'Unsupported list item type: {item_type}'}
        )

    async def _parse_dict(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
        param_metadata: Any = None,
    ) -> Any:
        """Parse dictionary types."""
        value = self._get_param_value_with_alias(data, param_name, param_metadata)
        if value is None:
            if default is not None and default is not ...:
                return default
            if is_required:
                raise BadRequestException(
                    details={'message': f'Missing required parameter: {param_name}'}
                )
        args = get_args(annotation)
        if not args or args[1] is Any:
            return dict(value) if isinstance(value, Mapping) else value
        value_type = args[1]
        handler = self.type_handlers.get(
            self._get_type_key(value_type),
            self._parse_primitive,
        )
        result = {}
        for k, v in value.items():
            result[k] = await handler(param_name, value_type, {k: v}, None, False)
        return result

    async def _parse_union(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
        param_metadata: Any = None,
    ) -> Any:
        """Parse union types by trying each type in order, including nested unions."""
        value = self._get_param_value_with_alias(data, param_name, param_metadata)
        if value is None:
            if default is not None and default is not ...:
                return default
            if is_required:
                raise BadRequestException(
                    details={'message': f'Missing required parameter: {param_name}'}
                )

        errors = []
        for typ in get_args(annotation):
            if typ is type(None):
                continue
            if get_origin(typ) in (Union, Optional):
                # Recursively parse nested unions
                try:
                    return await self._parse_union(
                        param_name,
                        typ,
                        data,
                        default,
                        is_required,
                        param_metadata,
                    )
                except (ValidationException, BadRequestException) as e:
                    errors.append(str(e))
                    continue
            handler = self.type_handlers.get(
                self._get_type_key(typ),
                self._parse_primitive,
            )
            try:
                return await handler(
                    param_name,
                    typ,
                    data,
                    default,
                    is_required,
                    param_metadata,
                )
            except (ValidationException, BadRequestException) as e:
                errors.append(str(e))

        raise ValidationException(
            details={
                'field': param_name,
                'msg': (
                    f'Failed to parse value as any of {get_args(annotation)}: '
                    f'{errors}'
                ),
                'request': f'{self.request.method} {self.request.url}',
            }
        )

    async def _parse_model(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
    ) -> Any:
        """Parse Pydantic models or JSON schema."""
        if not data and default is not None and default is not ...:
            return default
        if not data and is_required:
            raise BadRequestException(
                details={'message': f'Missing required parameter: {param_name}'}
            )
        try:
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                return annotation(**data)
            elif isinstance(annotation, dict):  # JSON schema
                validate(instance=data, schema=annotation)
                return data
            raise ValueError('Invalid data format for model')
        except (ValidationError, JsonSchemaError) as e:
            raise ValidationException(
                details={'field': param_name, 'msg': str(e)}
            ) from e

    async def _parse_special(
        self,
        param_name: str,
        annotation: Any,
        data: Any,
        default: Any,
        is_required: bool,
        param_metadata: Any = None,
    ) -> Any:
        """Parse special types (Request, FormData, Headers, etc.)."""
        type_map = {
            Request: lambda: self.request,
            FormData: lambda: self.request.form().__aenter__(),
            Headers: lambda: self.request.headers,
            QueryParams: lambda: self.request.query_params,
            dict: lambda: self.request.scope,
            UploadFile: lambda: self._get_file(
                param_name, data, default, is_required, param_metadata, annotation
            ),
        }
        handler = type_map.get(annotation)
        if handler:
            result = handler()
            return await result if inspect.iscoroutine(result) else result
        raise BadRequestException(
            details={'message': f'Unsupported special type: {annotation}'}
        )

    async def _get_file(
        self,
        param_name: str,
        data: Any,
        default: Any,
        is_required: bool,
        param_metadata: Any = None,
        annotation: Any = None,
    ) -> Any:
        """Handle file uploads, supporting single or multiple files."""
        files = self._get_param_value_with_alias(data, param_name, param_metadata)
        if not files:
            if default is not None and default is not ...:
                return default
            if is_required:
                raise BadRequestException(
                    details={
                        'message': f'Missing required file parameter: {param_name}'
                    }
                )

        if isinstance(files, UploadFile):
            return [files] if get_origin(annotation) is list else files
        if isinstance(files, list):
            if not files:
                return default if default is not None and default is not ... else None
            if not all(isinstance(f, UploadFile) for f in files):
                raise BadRequestException(
                    details={
                        'message': (
                            f'Invalid file type for parameter: {param_name}'
                        )
                    }
                )
            return files if get_origin(annotation) is list else files[0]
        raise BadRequestException(
            details={'message': f'Invalid file data for parameter: {param_name}'}
        )

    @parser_cache()
    def _resolve_param_metadata(
        self, param: inspect.Parameter
    ) -> tuple[Any, str, Any, bool, Any]:
        """
        Cache parameter metadata (annotation, param_type, default, is_required,
        param_metadata).

        """  # noqa: D205
        annotation = param.annotation
        default = (
            param.default if param.default is not inspect.Parameter.empty else None
        )
        is_required = default is None and param.default is inspect.Parameter.empty
        param_type = 'query_params'  # Default
        param_metadata = None

        if get_origin(annotation) is Annotated:
            base_type, *metadata = get_args(annotation)
            if _is_auth_dependency(annotation):
                provider = next(
                    (m for m in metadata if isinstance(m, (Provide))),
                    Provide(),
                )
                return (
                    base_type,
                    'provide',
                    provider,
                    is_required,
                    None,
                )

            param_types = (
                Query,
                Path,
                Body,
                Form,
                File,
                Header,
                Cookie,
                Provide,
            )
            param_metadata = next(
                (m for m in metadata if isinstance(m, param_types)),
                None,
            )
            if not param_metadata:
                raise InvalidMediaTypeException(
                    details={
                        'message': f'Unsupported parameter metadata for '
                        f'{param.name}: {annotation}'
                    }
                )

            if hasattr(param_metadata, 'media_type'):
                content_type = (
                    self.request.headers.get('Content-Type', '')
                    .split(';')[0]
                    .strip()
                )
                expected_media_type = param_metadata.media_type.split(';')[0].strip()
                if (
                    content_type != expected_media_type
                    and not content_type.startswith(expected_media_type + '/')
                ):
                    raise InvalidMediaTypeException(
                        details={
                            'message': (
                                f'Expected media type {expected_media_type}, got {content_type}'  # noqa: E501
                            )
                        }
                    )

            if isinstance(param_metadata, (Provide)):
                return (
                    base_type,
                    'provide',
                    param_metadata.dependency,
                    is_required,
                    param_metadata,
                )
            param_type = self.param_types.get(type(param_metadata), 'query_params')
            metadata_default = (
                param_metadata.default
                if hasattr(param_metadata, 'default')
                and param_metadata.default is not PydanticUndefined
                else None
            )
            default = metadata_default if metadata_default is not None else default
            is_required = False if metadata_default is not None else is_required
            annotation = base_type
            if isinstance(param_metadata, File):
                return annotation, 'file_data', default, is_required, param_metadata
            elif isinstance(param_metadata, Form):
                return annotation, 'form_data', default, is_required, param_metadata

        if annotation is inspect._empty:
            param_type = (
                'path_params'
                if param.name in self.request.path_params
                else 'query_params'
            )
        elif annotation is UploadFile:
            param_type = 'file_data'
        elif (
            get_origin(annotation) is list
            and len(get_args(annotation)) > 0
            and get_args(annotation)[0] is UploadFile
        ):
            param_type = 'file_data'
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            param_type = (
                'json_body' if self.request.method.upper() != 'GET' else 'query_params'
            )
        elif (
            get_origin(annotation) is list
            and isinstance(get_args(annotation)[0], type)
            and issubclass(get_args(annotation)[0], BaseModel)
        ):
            param_type = (
                'json_body' if self.request.method.upper() != 'GET' else 'query_params'
            )
        elif param.name in self.request.path_params:
            param_type = 'path_params'

        return annotation, param_type, default, is_required, param_metadata

    async def resolve(self, signature: inspect.Signature) -> dict[str, Any]:
        """Resolve all parameters for the given function signature."""
        kwargs = {}
        try:
            for param in signature.parameters.values():
                (
                    annotation,
                    param_type,
                    default,
                    is_required,
                    param_metadata,
                ) = self._resolve_param_metadata(param)
                name = param.name

                if annotation is inspect._empty:
                    annotation = str

                if param_type == 'provide':
                    if callable(default):
                        func_sig = inspect.signature(default)
                        if len(func_sig.parameters) > 0:
                            kwargs[name] = await default(self.request)
                        else:
                            kwargs[name] = await default()
                    else:
                        kwargs[name] = default
                    continue

                type_key = self._get_type_key(annotation)
                handler = self.type_handlers.get(type_key)
                if not handler:
                    handler = self.custom_handlers.get(
                        annotation,
                        self._parse_model
                        if (
                            isinstance(annotation, type)
                            and issubclass(annotation, BaseModel)
                        )
                        else None,
                    )
                if not handler:
                    if default is not None and default is not ...:
                        kwargs[name] = default
                        continue
                    raise UnsupportParameterException(
                        details={
                            'message': f'Unsupported parameter type for {name}: '
                            f'{annotation}'
                        }
                    )
                data = await self._fetch_data(param_type)
                if handler in (
                    self._parse_primitive,
                    self._parse_list,
                    self._parse_dict,
                    self._parse_union,
                    self._parse_special,
                ):
                    kwargs[name] = await handler(
                        name, annotation, data, default, is_required, param_metadata
                    )
                else:
                    kwargs[name] = await handler(
                        name, annotation, data, default, is_required
                    )
        except Exception as e:
            logger.error(f"Failed to resolve parameters for {signature}: {e!s}")
            raise
        return kwargs

class InputHandler:
    """Input handler for resolving parameters from a request."""

    def __init__(self, request: Request):
        """Initialize the InputHandler with the request."""
        self.resolver = ParameterResolver(request)

    async def get_input(self, signature: inspect.Signature) -> dict[str, Any]:
        """Resolve parameters from the request based on the function signature."""
        return await self.resolver.resolve(signature)
