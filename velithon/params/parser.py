"""Parameter parsing and validation for Velithon framework.

Simplified parameter parsing system for maximum performance.
"""

from __future__ import annotations

import inspect
import logging
from typing import Annotated, Any, Union, get_args, get_origin

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


def convert_value(value: Any, target_type: type) -> Any:
    """Convert value to target type with optimized converters."""
    if value is None:
        return None

    if target_type is bool:
        return str(value).lower() in ('true', '1', 'yes', 'on')
    elif target_type is bytes:
        return value.encode() if isinstance(value, str) else value
    elif target_type in (int, float, str):
        return target_type(value)

    return value


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
                return 'path'
            elif isinstance(meta, Query):
                return 'query'
            elif isinstance(meta, Form):
                return 'form'
            elif isinstance(meta, Body):
                return 'body'
            elif isinstance(meta, File):
                return 'file'
            elif isinstance(meta, Header):
                return 'header'
            elif isinstance(meta, Cookie):
                return 'cookie'
            elif isinstance(meta, Provide):
                return 'dependency'
        annotation = base_type

    # Handle special types
    if annotation == Request:
        return 'request'
    elif annotation in (FormData, Headers, QueryParams):
        return 'special'
    elif annotation == UploadFile or (
        get_origin(annotation) is list
        and len(get_args(annotation)) > 0
        and get_args(annotation)[0] == UploadFile
    ):
        return 'file'
    elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
        # For BaseModel, default to 'query' for GET methods, 'body' for others
        # This is inferred during resolve_parameter when we have access to the request
        return 'infer'

    # Default: check if it's a path parameter, otherwise query
    return 'path' if param.name in getattr(param, '_path_params', {}) else 'query'


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

        if source == 'query':
            data = dict(self.request.query_params)
        elif source == 'path':
            data = dict(self.request.path_params)
        elif source == 'body':
            data = await self.request.json()
        elif source == 'form':
            form = await self.request.form()
            data = {}
            for key, value in form.multi_items():
                if key in data:
                    if not isinstance(data[key], list):
                        data[key] = [data[key]]
                    data[key].append(value)
                else:
                    data[key] = value
        elif source == 'file':
            data = await self.request.files()
        elif source == 'header':
            data = dict(self.request.headers)
        elif source == 'cookie':
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

        # Skip auth dependencies - they're handled in the main resolve method
        if _is_auth_dependency(annotation):
            return default

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

        # For BaseModel without explicit annotation, infer based on HTTP method
        if (
            source == 'infer'
            and isinstance(base_type, type)
            and issubclass(base_type, BaseModel)
        ):
            method = getattr(self.request, 'method', 'GET')
            if method in ('GET', 'DELETE', 'HEAD'):
                source = 'query'
            else:
                source = 'body'

        # Handle path parameters specially
        if source == 'path':
            value = self.request.path_params.get(param_name)
        elif source == 'dependency':
            # This should have been handled above
            return default
        else:
            data = await self.get_data(source)
            if source == 'body':
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
                and source in ('query', 'form')
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
            if source == 'file' and base_type == UploadFile:
                return value

            # Handle list of file uploads
            if (
                source == 'file'
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
        """Resolve all parameters for a function signature."""
        kwargs = {}

        for param in signature.parameters.values():
            try:
                # Check if this is an auth dependency first
                if _is_auth_dependency(param.annotation):
                    # Handle auth dependency
                    if get_origin(param.annotation) is Annotated:
                        _, *metadata = get_args(param.annotation)
                        for meta in metadata:
                            if isinstance(meta, Provide):
                                if callable(meta.service):
                                    sig = inspect.signature(meta.service)
                                    if sig.parameters:
                                        result = meta.service(self.request)
                                        kwargs[param.name] = (
                                            await result
                                            if inspect.iscoroutine(result)
                                            else result
                                        )
                                    else:
                                        result = meta.service()
                                        kwargs[param.name] = (
                                            await result
                                            if inspect.iscoroutine(result)
                                            else result
                                        )
                                else:
                                    kwargs[param.name] = meta.service
                                break
                else:
                    kwargs[param.name] = await self.resolve_parameter(param)
            except Exception as e:
                logger.error(f'Failed to resolve parameter {param.name}: {e}')
                raise

        return kwargs


def _is_auth_dependency(annotation: Any) -> bool:
    """Check if a parameter annotation represents a dependency.

    Args:
        annotation: The parameter annotation to check

    Returns:
        True if this is a dependency, False otherwise

    """
    if get_origin(annotation) is Annotated:
        _, *metadata = get_args(annotation)
        return any(isinstance(meta, Provide) for meta in metadata)
    return False


class InputHandler:
    """Input handler for resolving parameters from a request."""

    def __init__(self, request: Request):
        """Initialize the InputHandler with the request."""
        self.resolver = ParameterResolver(request)

    async def get_input(self, signature: inspect.Signature) -> dict[str, Any]:
        """Resolve parameters from the request based on the function signature."""
        return await self.resolver.resolve(signature)

