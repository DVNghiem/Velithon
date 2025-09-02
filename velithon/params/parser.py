"""Parameter parsing and validation for Velithon framework.

Simplified parameter parsing system for maximum performance.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import (
    Annotated,
    Any,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from pydantic import BaseModel, ValidationError

from velithon.datastructures import FormData, Headers, QueryParams, UploadFile
from velithon.di import Provide
from velithon.exceptions import (
    BadRequestException,
    ValidationException,
)
from velithon.params.params import Body, Cookie, File, Form, Header, Path, Query
from velithon.requests import Request

logger = logging.getLogger(__name__)

TRUTHY_VALUES = frozenset(['true', '1', 'yes', 'on']) 
READ_ONLY_METHODS = frozenset(['GET', 'DELETE', 'HEAD', 'OPTIONS'])
BODY_METHODS = frozenset(['POST', 'PUT', 'PATCH'])

class ParameterSource:  # noqa: D101
    PATH = 'path'
    QUERY = 'query'
    BODY = 'body'
    FORM = 'form'
    FILE = 'file'
    HEADER = 'header'
    COOKIE = 'cookie'
    REQUEST = 'request'
    SPECIAL = 'special'
    DEPENDENCY = 'dependency'
    FUNCTION_DEPENDENCY = 'function_dependency'
    INFER = 'infer'


T = TypeVar('T')


@overload
def convert_value(value: Any, target_type: type[bool]) -> bool: ...

@overload
def convert_value(value: Any, target_type: type[bytes]) -> bytes: ...

@overload
def convert_value(value: Any, target_type: type[int]) -> int: ...

@overload
def convert_value(value: Any, target_type: type[float]) -> float: ...

@overload
def convert_value(value: Any, target_type: type[str]) -> str: ...

@overload
def convert_value(value: Any, target_type: type[T]) -> T: ...


def convert_value(value: Any, target_type: type[T]) -> T:
    """Convert value to target type with optimized converters.

    Args:
        value: The value to convert
        target_type: The target type to convert to

    Returns:
        The converted value of the target type

    Raises:
        ValueError: If conversion fails
        TypeError: If conversion is not possible

    """
    if value is None:
        return None  # type: ignore[return-value]

    if target_type is bool:
        return str(value).lower() in TRUTHY_VALUES  # type: ignore[return-value]
    elif target_type is bytes:
        return value.encode() if isinstance(value, str) else value  # type: ignore[return-value]
    elif target_type in (int, float, str):
        return target_type(value)  # type: ignore[return-value]

    return value  # type: ignore[return-value]


def get_base_type(annotation: Any) -> Any:
    """Extract the base type from Annotated types."""
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


def get_param_source(param: inspect.Parameter, annotation: Any) -> str:
    """Determine parameter source based on annotation and parameter name."""
    # Handle Annotated types
    if get_origin(annotation) is Annotated:
        base_type, *metadata = get_args(annotation)
        for meta in metadata:
            if isinstance(meta, Path):
                return ParameterSource.PATH
            elif isinstance(meta, Query):
                return ParameterSource.QUERY
            elif isinstance(meta, Form):
                return ParameterSource.FORM
            elif isinstance(meta, Body):
                return ParameterSource.BODY
            elif isinstance(meta, File):
                return ParameterSource.FILE
            elif isinstance(meta, Header):
                return ParameterSource.HEADER
            elif isinstance(meta, Cookie):
                return ParameterSource.COOKIE
            elif isinstance(meta, Provide):
                return ParameterSource.DEPENDENCY
            elif callable(meta):
                return ParameterSource.FUNCTION_DEPENDENCY
        annotation = base_type

    # Handle special types
    if annotation == Request:
        return ParameterSource.REQUEST
    elif annotation in (FormData, Headers, QueryParams):
        return ParameterSource.SPECIAL
    elif annotation == UploadFile or (
        get_origin(annotation) is list
        and len(get_args(annotation)) > 0
        and get_args(annotation)[0] == UploadFile
    ):
        return ParameterSource.FILE
    elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
        # For BaseModel, default to 'query' for GET methods, 'body' for others
        # This is inferred during resolve_parameter when we have access to the request
        return ParameterSource.INFER

    # Default: check if it's a path parameter, otherwise query
    return (
        ParameterSource.PATH
        if param.name in getattr(param, '_path_params', {})
        else ParameterSource.QUERY
    )


class ParameterResolver:
    """Simplified parameter resolver inspired."""

    def __init__(self, request: Request):
        """Initialize the parameter resolver with a request object."""
        self.request = request
        self._data_cache = {}

    async def get_data(self, source: str) -> Any:
        """Get data from request based on source."""
        if source in self._data_cache:
            return self._data_cache[source]

        if source == ParameterSource.QUERY:
            data = dict(self.request.query_params)
        elif source == ParameterSource.PATH:
            data = dict(self.request.path_params)
        elif source == ParameterSource.BODY:
            data = await self.request.json()
        elif source == ParameterSource.FORM:
            form = await self.request.form()
            data = {}
            for key, value in form.multi_items():
                if key in data:
                    if not isinstance(data[key], list):
                        data[key] = [data[key]]
                    data[key].append(value)
                else:
                    data[key] = value
        elif source == ParameterSource.FILE:
            data = await self.request.files()
        elif source == ParameterSource.HEADER:
            data = dict(self.request.headers)
        elif source == ParameterSource.COOKIE:
            data = dict(self.request.cookies)
        else:
            data = {}

        self._data_cache[source] = data
        return data

    def get_param_value(self, data: dict, param_name: str) -> Any:
        """Get parameter value from data, trying name and alias."""
        # Try exact name
        if param_name in data:
            return data[param_name]

        # Try with underscores converted to hyphens
        alias = param_name.replace('_', '-')
        if alias in data:
            return data[alias]

        return None

    def parse_value(self, value: Any, annotation: Any, param_name: str) -> Any:
        """Parse value based on type annotation."""
        if value is None:
            return None

        # Handle Union types (including Optional)
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            # Try each type in the Union
            for arg_type in args:
                if arg_type is type(None):
                    continue
                try:
                    return self.parse_value(value, arg_type, param_name)
                except (ValueError, TypeError, ValidationError, ValidationException):
                    continue
            raise ValidationException(
                details={
                    'field': param_name,
                    'msg': f'Could not parse value {value} as any of {args}',
                }
            )

        # Handle List types
        elif origin is list:
            if not isinstance(value, list):
                # Split comma-separated values
                if isinstance(value, str):
                    value = [v.strip() for v in value.split(',') if v.strip()]
                else:
                    value = [value]

            args = get_args(annotation)
            if args:
                item_type = args[0]
                return [self.parse_value(item, item_type, param_name) for item in value]
            return value

        # Handle Pydantic models
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if isinstance(value, dict):
                try:
                    return annotation(**value)
                except ValidationError as e:
                    raise ValidationException(
                        details={'field': param_name, 'msg': str(e)}
                    ) from e
            elif isinstance(value, str):
                # Handle JSON string in form data
                try:
                    import json

                    data = json.loads(value)
                    return annotation(**data)
                except (json.JSONDecodeError, ValidationError) as e:
                    raise ValidationException(
                        details={'field': param_name, 'msg': str(e)}
                    ) from e
            raise ValidationException(
                details={
                    'field': param_name,
                    'msg': f'Expected dict or JSON string for {annotation}, '
                    f'got {type(value)}',
                }
            )

        # Handle primitive types
        elif annotation in (int, float, str, bool, bytes):
            try:
                return convert_value(value, annotation)
            except (ValueError, TypeError) as e:
                raise ValidationException(
                    details={
                        'field': param_name,
                        'msg': f'Invalid {annotation.__name__}: {e}',
                    }
                ) from e

        # Return as-is for other types
        return value

    async def resolve_parameter(self, param: inspect.Parameter) -> Any:
        """Resolve a single parameter."""
        param_name = param.name
        annotation = (
            param.annotation if param.annotation != inspect.Parameter.empty else str
        )
        default = param.default if param.default != inspect.Parameter.empty else None
        is_required = param.default == inspect.Parameter.empty

        # Handle special types
        base_type = get_base_type(annotation)
        if base_type == Request:
            return self.request
        elif base_type == FormData:
            return await self.request.form()
        elif base_type == Headers:
            return self.request.headers
        elif base_type == QueryParams:
            return self.request.query_params

        # Get parameter source and data
        source = get_param_source(param, annotation)

        # Handle function dependencies
        if source == ParameterSource.FUNCTION_DEPENDENCY:
            if get_origin(annotation) is Annotated:
                _, *metadata = get_args(annotation)
                for meta in metadata:
                    if callable(meta):
                        result = meta(self.request)
                        # Handle async functions
                        if inspect.iscoroutine(result):
                            return await result
                        else:
                            return result
            return default

        # For BaseModel without explicit annotation, infer based on HTTP method
        if (
            source == ParameterSource.INFER
            and isinstance(base_type, type)
            and issubclass(base_type, BaseModel)
        ):
            method = getattr(self.request, 'method', 'GET')
            if method in ('GET', 'DELETE', 'HEAD'):
                source = ParameterSource.QUERY
            else:
                source = ParameterSource.BODY

        # Handle path parameters specially
        if source == ParameterSource.PATH:
            value = self.request.path_params.get(param_name)
        elif source == ParameterSource.DEPENDENCY:
            # This should have been handled above
            return default
        else:
            data = await self.get_data(source)
            if source == ParameterSource.BODY:
                # For body parameters, the data IS the value
                value = data
            else:
                value = self.get_param_value(data, param_name)

        # Parse the value
        try:
            base_type = get_base_type(annotation)

            # Special handling for BaseModel with query/form parameters
            if (
                isinstance(base_type, type)
                and issubclass(base_type, BaseModel)
                and source in (ParameterSource.QUERY, ParameterSource.FORM)
            ):
                # For BaseModel in query/form, collect all relevant parameters
                data = await self.get_data(source)

                # If the value is a single JSON string (common in form uploads),
                # parse it as JSON first
                if isinstance(value, str) and value.startswith('{'):
                    try:
                        import json

                        value = json.loads(value)
                        if isinstance(value, dict):
                            try:
                                return base_type(**value)
                            except ValidationError as e:
                                raise ValidationException(
                                    details={'field': param_name, 'msg': str(e)}
                                ) from e
                    except json.JSONDecodeError:
                        # If JSON parsing fails, fall back to field-by-field parsing
                        pass

                # Filter data to only include fields that the model expects
                if hasattr(base_type, 'model_fields'):
                    model_fields = base_type.model_fields
                else:
                    model_fields = base_type.model_fields
                model_data = {k: v for k, v in data.items() if k in model_fields}

                if not model_data and is_required:
                    raise BadRequestException(
                        details={'message': f'Missing required parameter: {param_name}'}
                    )
                elif not model_data:
                    return default

                try:
                    return base_type(**model_data)
                except ValidationError as e:
                    raise ValidationException(
                        details={'field': param_name, 'msg': str(e)}
                    ) from e

            # Handle file uploads
            if source == ParameterSource.FILE and base_type == UploadFile:
                return value

            # Handle list of file uploads
            if (
                source == ParameterSource.FILE
                and get_origin(base_type) is list
                and get_args(base_type)
                and get_args(base_type)[0] == UploadFile
            ):
                return value if isinstance(value, list) else [value]

            # Handle missing values for non-BaseModel types
            if value is None:
                if is_required:
                    raise BadRequestException(
                        details={'message': f'Missing required parameter: {param_name}'}
                    )
                return default

            return self.parse_value(value, base_type, param_name)
        except Exception as e:
            logger.error(f'Failed to parse parameter {param_name}: {e}')
            raise

    async def resolve(self, signature: inspect.Signature) -> dict[str, Any]:
        """Resolve all parameters concurrently."""
        tasks = []
        param_names = []

        for param in signature.parameters.values():
            tasks.append(self.resolve_parameter(param))
            param_names.append(param.name)

        try:
            results = await asyncio.gather(*tasks)
            return dict(zip(param_names, results))
        except Exception as e:
            logger.error(f'Failed to resolve parameters: {e}')
            raise


class InputHandler:
    """Input handler for resolving parameters from a request."""

    def __init__(self, request: Request):
        """Initialize the InputHandler with the request."""
        self.resolver = ParameterResolver(request)

    async def get_input(self, signature: inspect.Signature) -> dict[str, Any]:
        """Resolve parameters from the request based on the function signature."""
        return await self.resolver.resolve(signature)
