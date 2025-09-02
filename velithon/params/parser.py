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
    """Simplified parameter resolver for high-performance parameter extraction."""

    def __init__(self, request: Request):
        """Initialize the parameter resolver with a request object."""
        self.request = request
        self._data_cache = {}

    async def _extract_query_data(self) -> dict:
        """Extract query parameters from request."""
        return dict(self.request.query_params)

    async def _extract_path_data(self) -> dict:
        """Extract path parameters from request."""
        return dict(self.request.path_params)

    async def _extract_body_data(self) -> Any:
        """Extract JSON body from request."""
        return await self.request.json()

    async def _extract_form_data(self) -> dict:
        """Extract form data from request, handling multiple values."""
        form = await self.request.form()
        data = {}
        for key, value in form.multi_items():
            if key in data:
                if not isinstance(data[key], list):
                    data[key] = [data[key]]
                data[key].append(value)
            else:
                data[key] = value
        return data

    async def _extract_file_data(self) -> Any:
        """Extract file uploads from request."""
        return await self.request.files()

    async def _extract_header_data(self) -> dict:
        """Extract headers from request."""
        return dict(self.request.headers)

    async def _extract_cookie_data(self) -> dict:
        """Extract cookies from request."""
        return dict(self.request.cookies)

    async def get_data(self, source: str) -> Any:
        """Get data from request based on source with caching."""
        if source in self._data_cache:
            return self._data_cache[source]

        # Use specific extraction methods for better performance
        extractors = {
            ParameterSource.QUERY: self._extract_query_data,
            ParameterSource.PATH: self._extract_path_data,
            ParameterSource.BODY: self._extract_body_data,
            ParameterSource.FORM: self._extract_form_data,
            ParameterSource.FILE: self._extract_file_data,
            ParameterSource.HEADER: self._extract_header_data,
            ParameterSource.COOKIE: self._extract_cookie_data,
        }

        extractor = extractors.get(source)
        if extractor:
            data = await extractor()
        else:
            data = {}

        self._data_cache[source] = data
        return data

    def get_param_value(self, data: dict, param_name: str) -> Any:
        """Get parameter value from data, trying name and alias."""
        # Try exact name first (most common case)
        if param_name in data:
            return data[param_name]

        # Try with underscores converted to hyphens for compatibility
        alias = param_name.replace('_', '-')
        if alias in data:
            return data[alias]

        return None

    def _parse_union_type(self, value: Any, args: tuple, param_name: str) -> Any:
        """Parse value against Union type arguments."""
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

    def _parse_list_type(self, value: Any, args: tuple, param_name: str) -> list:
        """Parse value as list type."""
        if not isinstance(value, list):
            # Split comma-separated values for string inputs
            if isinstance(value, str):
                value = [v.strip() for v in value.split(',') if v.strip()]
            else:
                value = [value]

        if args:
            item_type = args[0]
            return [self.parse_value(item, item_type, param_name) for item in value]
        return value

    def _parse_pydantic_model(
        self, value: Any, annotation: type, param_name: str
    ) -> BaseModel:
        """Parse value as Pydantic BaseModel."""
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

    def _parse_primitive_type(
        self, value: Any, annotation: type, param_name: str
    ) -> Any:
        """Parse value as primitive type."""
        try:
            return convert_value(value, annotation)
        except (ValueError, TypeError) as e:
            raise ValidationException(
                details={
                    'field': param_name,
                    'msg': f'Invalid {annotation.__name__}: {e}',
                }
            ) from e

    def parse_value(self, value: Any, annotation: Any, param_name: str) -> Any:
        """Parse value based on type annotation using specialized parsers."""
        if value is None:
            return None

        origin = get_origin(annotation)

        # Handle Union types (including Optional)
        if origin is Union:
            args = get_args(annotation)
            return self._parse_union_type(value, args, param_name)

        # Handle List types
        elif origin is list:
            args = get_args(annotation)
            return self._parse_list_type(value, args, param_name)

        # Handle Pydantic models
        elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return self._parse_pydantic_model(value, annotation, param_name)

        # Handle primitive types
        elif annotation in (int, float, str, bool, bytes):
            return self._parse_primitive_type(value, annotation, param_name)

        # Return as-is for other types
        return value

    def _extract_param_metadata(
        self, param: inspect.Parameter
    ) -> tuple[str, Any, Any, bool]:
        """Extract parameter metadata for processing."""
        param_name = param.name
        annotation = (
            param.annotation if param.annotation != inspect.Parameter.empty else str
        )
        default = param.default if param.default != inspect.Parameter.empty else None
        is_required = param.default == inspect.Parameter.empty
        return param_name, annotation, default, is_required

    async def _handle_special_types(self, base_type: type) -> Any:
        """Handle special request-related types."""
        if base_type == Request:
            return self.request
        elif base_type == FormData:
            return await self.request.form()
        elif base_type == Headers:
            return self.request.headers
        elif base_type == QueryParams:
            return self.request.query_params
        return None

    async def _handle_function_dependency(
        self, annotation: Any, default: Any
    ) -> Any:
        """Handle function dependencies in parameter annotations."""
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

    def _infer_source_for_basemodel(
        self, source: str, base_type: type
    ) -> str:
        """Infer parameter source for BaseModel based on HTTP method."""
        if (
            source == ParameterSource.INFER
            and isinstance(base_type, type)
            and issubclass(base_type, BaseModel)
        ):
            method = getattr(self.request, 'method', 'GET')
            if method in ('GET', 'DELETE', 'HEAD'):
                return ParameterSource.QUERY
            else:
                return ParameterSource.BODY
        return source

    async def _get_parameter_value(
        self, source: str, param_name: str
    ) -> Any:
        """Get parameter value based on source."""
        if source == ParameterSource.PATH:
            return self.request.path_params.get(param_name)
        elif source == ParameterSource.DEPENDENCY:
            return None  # Should have been handled earlier
        else:
            data = await self.get_data(source)
            if source == ParameterSource.BODY:
                # For body parameters, the data IS the value
                return data
            else:
                return self.get_param_value(data, param_name)

    async def _handle_basemodel_query_form(
        self, 
        base_type: type, 
        source: str, 
        param_name: str,
        value: Any, 
        is_required: bool, 
        default: Any
    ) -> BaseModel:
        """Handle BaseModel parsing for query/form parameters."""
        data = await self.get_data(source)

        # Handle single JSON string (common in form uploads)
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
        model_fields = getattr(base_type, 'model_fields', {})
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

    def _handle_file_uploads(self, base_type: type, value: Any) -> Any:
        """Handle file upload parameters."""
        if base_type == UploadFile:
            return value

        # Handle list of file uploads
        if (
            get_origin(base_type) is list
            and get_args(base_type)
            and get_args(base_type)[0] == UploadFile
        ):
            return value if isinstance(value, list) else [value]

        return None

    def _validate_required_parameter(
        self, value: Any, is_required: bool, param_name: str, default: Any
    ) -> Any:
        """Validate required parameters and return default if appropriate."""
        if value is None:
            if is_required:
                raise BadRequestException(
                    details={'message': f'Missing required parameter: {param_name}'}
                )
            return default
        return value

    async def resolve_parameter(self, param: inspect.Parameter) -> Any:
        """Resolve a single parameter using smaller helper methods."""
        param_name, annotation, default, is_required = (
            self._extract_param_metadata(param)
        )

        # Handle special types
        base_type = get_base_type(annotation)
        special_result = await self._handle_special_types(base_type)
        if special_result is not None:
            return special_result

        # Get parameter source and handle inference
        source = get_param_source(param, annotation)

        # Handle function dependencies
        if source == ParameterSource.FUNCTION_DEPENDENCY:
            return await self._handle_function_dependency(annotation, default)

        # Infer source for BaseModel based on HTTP method
        source = self._infer_source_for_basemodel(source, base_type)

        # Get the parameter value
        value = await self._get_parameter_value(source, param_name)

        # Parse the value based on type
        try:
            base_type = get_base_type(annotation)

            # Special handling for BaseModel with query/form parameters
            if (
                isinstance(base_type, type)
                and issubclass(base_type, BaseModel)
                and source in (ParameterSource.QUERY, ParameterSource.FORM)
            ):
                return await self._handle_basemodel_query_form(
                    base_type, source, param_name, value, is_required, default
                )

            # Handle file uploads
            file_result = self._handle_file_uploads(base_type, value)
            if file_result is not None:
                return file_result

            # Validate required parameters
            value = self._validate_required_parameter(
                value, is_required, param_name, default
            )

            # Parse the value using the main parser
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
