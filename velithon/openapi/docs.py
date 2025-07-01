import inspect
from collections.abc import Callable
from enum import Enum
from typing import (
    Annotated,
    Any,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from velithon.datastructures import FormData, Headers, UploadFile
from velithon.di import Provide
from velithon.params.params import Body, File, Form, Header, Path, Query
from velithon.requests import Request
from velithon.responses import PlainTextResponse

from .constants import REF_TEMPLATE


def join_url_paths(*parts) -> str:
    first = parts[0]
    parts = [part.strip('/') for part in parts]
    starts_with_slash = first.startswith('/') if first else False
    joined = '/'.join(part for part in parts if part)
    if starts_with_slash:
        joined = '/' + joined
    return joined


def pydantic_to_swagger(model: type[BaseModel] | dict, schemas: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert a Pydantic model to a Swagger/OpenAPI schema definition.
    
    Args:
        model: The Pydantic model class or dict to convert
        schemas: Dictionary to accumulate all nested schemas
    
    Returns:
        The schema definition for the model
    """
    if schemas is None:
        schemas = {}
    
    if isinstance(model, dict):
        schema = {}
        for name, field_type in model.items():
            schema[name] = SchemaProcessor._process_field(name, field_type, schemas)
        return schema

    schema = {'type': 'object', 'properties': {}, 'required': []}
    for name, field in model.model_fields.items():
        field_schema = SchemaProcessor._process_field(name, field, schemas)
        schema['properties'][name] = field_schema
        if field.is_required():
            schema['required'].append(name)
    
    return schema


class SchemaProcessor:
    @staticmethod
    def process_union(args: tuple, schemas: dict[str, Any]) -> dict[str, Any]:
        if type(None) in args:
            inner_type = next(arg for arg in args if arg is not type(None))
            schema = SchemaProcessor._process_field('', inner_type, schemas)
            schema['nullable'] = True
            return schema
        return {
            'oneOf': [SchemaProcessor._process_field('', arg, schemas) for arg in args]
        }

    @staticmethod
    def process_enum(annotation: type[Enum]) -> dict[str, Any]:
        return {
            'type': 'string',
            'enum': [e.value for e in annotation.__members__.values()],
        }

    @staticmethod
    def process_primitive(annotation: type) -> dict[str, str]:
        type_mapping = {int: 'integer', float: 'number', str: 'string', bool: 'boolean'}
        return {'type': type_mapping.get(annotation, 'object')}

    @staticmethod
    def process_list(annotation: type, schemas: dict[str, Any]) -> dict[str, Any]:
        schema = {'type': 'array'}
        args = get_args(annotation)
        if args:
            item_type = args[0]
            schema['items'] = SchemaProcessor._process_field('item', item_type, schemas)
        else:
            schema['items'] = {}
        return schema

    @staticmethod
    def process_dict(annotation: type, schemas: dict[str, Any]) -> dict[str, Any]:
        schema = {'type': 'object'}
        args = get_args(annotation)
        if args:
            key_type, value_type = args
            if isinstance(key_type, type) and issubclass(key_type, str):
                schema['additionalProperties'] = SchemaProcessor._process_field(
                    'value', value_type, schemas
                )
        return schema

    @staticmethod
    def process_file(annotation: type, schemas: dict[str, Any]) -> dict[str, Any]:
        if annotation is UploadFile:
            return {'type': 'string', 'format': 'binary'}
        return {'type': 'object'}  # Fallback for unsupported file types

    @staticmethod
    def process_form_data(annotation: type, schemas: dict[str, Any]) -> dict[str, Any]:
        if annotation is FormData:
            return {'type': 'object', 'additionalProperties': True}
        return SchemaProcessor._process_field('', annotation, schemas)

    @staticmethod
    def process_headers(annotation: type, schemas: dict[str, Any]) -> dict[str, Any]:
        if annotation is Headers:
            return {'type': 'object', 'additionalProperties': {'type': 'string'}}
        return {'type': 'object'}

    @classmethod
    def _process_field(
        cls, name: str, field: Any, schemas: dict[str, Any]
    ) -> dict[str, Any]:
        if isinstance(field, FieldInfo):
            annotation = field.annotation
            schema = cls._process_annotation(annotation, schemas)
            
            # Add field description
            if field.description:
                schema['description'] = field.description
            
            # Add default value
            if field.default is not None and field.default is not PydanticUndefined:
                schema['default'] = field.default
            
            # Handle Pydantic v2 metadata constraints
            if hasattr(field, 'metadata') and field.metadata:
                for constraint in field.metadata:
                    constraint_type = type(constraint).__name__
                    if constraint_type == 'MinLen' and hasattr(constraint, 'min_length'):
                        schema['minLength'] = constraint.min_length
                    elif constraint_type == 'MaxLen' and hasattr(constraint, 'max_length'):
                        schema['maxLength'] = constraint.max_length
                    elif constraint_type == 'Ge' and hasattr(constraint, 'ge'):
                        schema['minimum'] = constraint.ge
                    elif constraint_type == 'Le' and hasattr(constraint, 'le'):
                        schema['maximum'] = constraint.le
                    elif constraint_type == 'Gt' and hasattr(constraint, 'gt'):
                        schema['exclusiveMinimum'] = constraint.gt
                    elif constraint_type == 'Lt' and hasattr(constraint, 'lt'):
                        schema['exclusiveMaximum'] = constraint.lt
                    elif constraint_type == 'Pattern' and hasattr(constraint, 'pattern'):
                        schema['pattern'] = constraint.pattern
            
            # Legacy constraint handling (in case some attributes are directly on field)
            if hasattr(field, 'ge') and field.ge is not None:
                schema['minimum'] = field.ge
            if hasattr(field, 'le') and field.le is not None:
                schema['maximum'] = field.le
            if hasattr(field, 'gt') and field.gt is not None:
                schema['exclusiveMinimum'] = field.gt
            if hasattr(field, 'lt') and field.lt is not None:
                schema['exclusiveMaximum'] = field.lt
            if hasattr(field, 'min_length') and field.min_length is not None:
                schema['minLength'] = field.min_length
            if hasattr(field, 'max_length') and field.max_length is not None:
                schema['maxLength'] = field.max_length
            if hasattr(field, 'pattern') and field.pattern is not None:
                schema['pattern'] = field.pattern
            
            return schema
        return cls._process_annotation(field, schemas)

    @classmethod
    def _process_annotation(
        cls, annotation: Any, schemas: dict[str, Any]
    ) -> dict[str, Any]:
        origin = get_origin(annotation)
        
        if origin is Annotated:
            base_type, *metadata = get_args(annotation)
            schema = cls._process_annotation(base_type, schemas)
            for meta in metadata:
                if isinstance(meta, Query | Body | Form | Path | File | Header):
                    if meta.description:
                        schema['description'] = meta.description
                    if (
                        meta.default is not None
                        and meta.default is not PydanticUndefined
                    ):
                        schema['default'] = meta.default
            return schema

        # Handle both typing.Union and new X | Y syntax
        if origin is Union or str(type(annotation)) == "<class 'types.UnionType'>":
            return cls.process_union(get_args(annotation), schemas)

        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return cls.process_enum(annotation)

        if annotation in {int, float, str, bool}:
            return cls.process_primitive(annotation)

        if isinstance(annotation, list) or origin is list:
            return cls.process_list(annotation, schemas)

        if isinstance(annotation, dict) or origin is dict:
            return cls.process_dict(annotation, schemas)

        if annotation is UploadFile:
            return cls.process_file(annotation, schemas)

        if annotation is FormData:
            return cls.process_form_data(annotation, schemas)

        if annotation is Headers:
            return cls.process_headers(annotation, schemas)

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            # Only add the schema if it's not already there to avoid duplicates
            if annotation.__name__ not in schemas:
                schemas[annotation.__name__] = pydantic_to_swagger(annotation, schemas)
            return {'$ref': REF_TEMPLATE.format(model=annotation.__name__)}

        if isinstance(annotation, type) and issubclass(annotation, PlainTextResponse):
            return {'type': 'string'}

        return {'type': 'object'}


def process_model_params(
    param: inspect.Parameter,
    docs: dict,
    path: str,
    request_method: str,
    schemas: dict[str, Any],
) -> str:
    name = param.name
    annotation = param.annotation
    default = param.default

    # Skip special types
    SPECIAL_TYPES = (Request, dict, Callable, Provide)
    if isinstance(annotation, type) and issubclass(annotation, SPECIAL_TYPES):
        return path

    # Handle Annotated types
    if get_origin(annotation) is Annotated:
        base_type, *metadata = get_args(annotation)
        param_metadata = next(
            (
                m
                for m in metadata
                if isinstance(m, (Query, Path, Body, Form, File, Header))
            ),
            None,
        )
        if param_metadata:
            schema = SchemaProcessor._process_field(name, base_type, schemas)
            if param_metadata.description:
                schema['description'] = param_metadata.description
            if (
                param_metadata.default is not None
                and param_metadata.default is not PydanticUndefined
            ):
                schema['default'] = param_metadata.default

            param_type = type(param_metadata)
            if param_type is Path:
                docs.setdefault('parameters', []).append(
                    {'name': name, 'in': 'path', 'required': True, 'schema': schema}
                )
                if f'{{{name}}}' not in path:
                    path = path.rstrip('/') + f'/{{{name}}}'
            elif param_type is Query:
                docs.setdefault('parameters', []).append(
                    {
                        'name': name,
                        'in': 'query',
                        'required': param_metadata.default is PydanticUndefined,
                        'schema': schema,
                    }
                )
            elif param_type is Header:
                docs.setdefault('parameters', []).append(
                    {
                        'name': name,
                        'in': 'header',
                        'required': param_metadata.default is PydanticUndefined,
                        'schema': schema,
                    }
                )
            elif param_type is Body:
                media_type = param_metadata.media_type or 'application/json'
                docs['requestBody'] = {
                    'content': {media_type: {'schema': schema}},
                    'required': param_metadata.default is PydanticUndefined,
                }
            elif param_type is Form:
                media_type = param_metadata.media_type or 'multipart/form-data'
                docs['requestBody'] = {
                    'content': {media_type: {'schema': schema}},
                    'required': param_metadata.default is PydanticUndefined,
                }
            elif param_type is File:
                media_type = param_metadata.media_type or 'multipart/form-data'
                schema = SchemaProcessor.process_file(base_type, schemas)
                docs['requestBody'] = {
                    'content': {media_type: {'schema': schema}},
                    'required': param_metadata.default is PydanticUndefined,
                }
            return path
        annotation = base_type

    # Handle default metadata
    if isinstance(default, (Query, Path, Body, Form, File, Header)):
        schema = SchemaProcessor._process_field(name, annotation, schemas)
        if default.description:
            schema['description'] = default.description
        if default.default is not None and default.default is not PydanticUndefined:
            schema['default'] = default.default

        if isinstance(default, Path):
            docs.setdefault('parameters', []).append(
                {'name': name, 'in': 'path', 'required': True, 'schema': schema}
            )
            if f'{{{name}}}' not in path:
                path = path.rstrip('/') + f'/{{{name}}}'
        elif isinstance(default, Query):
            docs.setdefault('parameters', []).append(
                {
                    'name': name,
                    'in': 'query',
                    'required': default.default is PydanticUndefined,
                    'schema': schema,
                }
            )
        elif isinstance(default, Header):
            docs.setdefault('parameters', []).append(
                {
                    'name': name,
                    'in': 'header',
                    'required': default.default is PydanticUndefined,
                    'schema': schema,
                }
            )
        elif isinstance(default, Body):
            media_type = default.media_type or 'application/json'
            docs['requestBody'] = {
                'content': {media_type: {'schema': schema}},
                'required': default.default is PydanticUndefined,
            }
        elif isinstance(default, Form):
            media_type = default.media_type or 'multipart/form-data'
            docs['requestBody'] = {
                'content': {media_type: {'schema': schema}},
                'required': default.default is PydanticUndefined,
            }
        elif isinstance(default, File):
            media_type = default.media_type or 'multipart/form-data'
            schema = SchemaProcessor.process_file(annotation, schemas)
            docs['requestBody'] = {
                'content': {media_type: {'schema': schema}},
                'required': default.default is PydanticUndefined,
            }
        return path

    # Handle Pydantic models
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if request_method.lower() == 'get':
            for field_name, field in annotation.model_fields.items():
                schema = SchemaProcessor._process_field(field_name, field, schemas)
                docs.setdefault('parameters', []).append(
                    {
                        'name': field_name,
                        'in': 'query',
                        'required': field.is_required(),
                        'schema': schema,
                    }
                )
        else:
            docs['requestBody'] = {
                'content': {
                    'application/json': {
                        'schema': SchemaProcessor._process_field(
                            name, annotation, schemas
                        )
                    }
                },
                'required': default is inspect.Parameter.empty
                or default is PydanticUndefined,
            }
        return path

    # Handle UploadFile explicitly
    if annotation is UploadFile:
        schema = SchemaProcessor.process_file(annotation, schemas)
        docs['requestBody'] = {
            'content': {'multipart/form-data': {'schema': schema}},
            'required': default is inspect.Parameter.empty
            or default is PydanticUndefined,
        }
        return path

    # Handle FormData explicitly
    if annotation is FormData:
        schema = SchemaProcessor.process_form_data(annotation, schemas)
        docs['requestBody'] = {
            'content': {'multipart/form-data': {'schema': schema}},
            'required': default is inspect.Parameter.empty
            or default is PydanticUndefined,
        }
        return path

    # Handle Headers explicitly
    if annotation is Headers:
        schema = SchemaProcessor.process_headers(annotation, schemas)
        docs.setdefault('parameters', []).append(
            {
                'name': name,
                'in': 'header',
                'required': default is inspect.Parameter.empty
                or default is PydanticUndefined,
                'schema': schema,
            }
        )
        return path

    # Handle primitive types as path parameters if they're in the path
    if annotation in (int, float, str, bool) and f'{{{name}}}' in path:
        schema = SchemaProcessor._process_field(name, annotation, schemas)
        docs.setdefault('parameters', []).append(
            {
                'name': name,
                'in': 'path',
                'required': True,  # Path parameters are always required
                'schema': schema,
            }
        )
        return path

    # Handle primitive types as query parameters (only if not a path parameter)
    if annotation in (int, float, str, bool) and f'{{{name}}}' not in path:
        schema = SchemaProcessor._process_field(name, annotation, schemas)
        docs.setdefault('parameters', []).append(
            {
                'name': name,
                'in': 'query',
                'required': default is inspect.Parameter.empty
                or default is PydanticUndefined,
                'schema': schema,
            }
        )
    return path


def process_response(response_type: type, docs: dict, schemas: dict[str, Any]) -> None:
    """Process response type and add to docs."""
    if isinstance(response_type, type) and issubclass(response_type, PlainTextResponse):
        docs['responses'] = {
            '200': {
                'description': 'Successful response',
                'content': {'text/plain': {'schema': {'type': 'string'}}},
            }
        }
    else:
        schema = SchemaProcessor._process_field('response', response_type, schemas)
        docs['responses'] = {
            '200': {
                'description': 'Successful response',
                'content': {'application/json': {'schema': schema}},
            }
        }


def detect_security_requirements(func: callable) -> list[dict[str, list[str]]]:
    """Detect security requirements from function dependencies."""
    security_requirements = []
    signature = inspect.signature(func)
    
    for param in signature.parameters.values():
        annotation = param.annotation
        
        # Check for Annotated types that might contain security dependencies
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            for metadata in args[1:]:  # Skip the base type
                
                # Check if this is a security dependency
                if hasattr(metadata, '__class__'):
                    class_name = metadata.__class__.__name__
                    module_name = getattr(metadata.__class__, '__module__', '')
                    
                    # Check for OAuth2, Bearer, or other security schemes
                    if 'velithon.security' in module_name or 'security' in class_name.lower():
                        if 'oauth2' in class_name.lower() or 'bearer' in class_name.lower():
                            security_requirements.append({"bearerAuth": []})
                        elif 'apikey' in class_name.lower():
                            security_requirements.append({"apiKeyAuth": []})
                        elif 'basic' in class_name.lower():
                            security_requirements.append({"basicAuth": []})
                
                # Check if metadata is a callable (function dependency)
                if callable(metadata):
                    func_name = getattr(metadata, '__name__', '').lower()
                    
                    # Check function name patterns for authentication
                    if any(keyword in func_name for keyword in ['auth', 'user', 'token', 'jwt']):
                        # Try to determine auth type from function name
                        if 'jwt' in func_name or 'bearer' in func_name:
                            security_requirements.append({"bearerAuth": []})
                        elif 'basic' in func_name:
                            security_requirements.append({"basicAuth": []})
                        elif 'api_key' in func_name or 'apikey' in func_name:
                            security_requirements.append({"apiKeyAuth": []})
                        elif 'oauth2' in func_name:
                            security_requirements.append({"oauth2": []})
                        else:
                            # Default to bearer auth for generic auth functions
                            security_requirements.append({"bearerAuth": []})
                    
                    # Check for permission dependencies
                    elif 'permission' in func_name or 'require' in func_name:
                        # Permission requirements typically need authentication first
                        security_requirements.append({"bearerAuth": []})
    
    return security_requirements


def get_security_schemes() -> dict[str, Any]:
    """Get OpenAPI security scheme definitions."""
    return {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        },
        "basicAuth": {
            "type": "http",
            "scheme": "basic"
        },
        "oauth2": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/token",
                    "scopes": {
                        "read": "Read access",
                        "write": "Write access",
                        "admin": "Admin access"
                    }
                }
            }
        }
    }


def swagger_generate(
    func: callable,
    request_method: str,
    endpoint_path: str = '/',
    response_model: type | None = None
) -> tuple[dict, dict[str, Any]]:
    """Generate OpenAPI documentation for a function endpoint.
    
    Args:
        func: The endpoint function
        request_method: HTTP method (GET, POST, etc.)
        endpoint_path: URL path for the endpoint
        response_model: Optional Pydantic model for response schema
    
    Returns:
        Tuple of (path_docs, schemas) where path_docs contains the OpenAPI path
        documentation and schemas contains all referenced model schemas.
    """
    signature = inspect.signature(func)
    schemas: dict[str, Any] = {}
    docs = {
        request_method.lower(): {
            'summary': func.__name__.replace('_', ' ').title(),
            'operationId': func.__name__,
            'parameters': [],
            'responses': {},
        }
    }

    # Detect security requirements
    security_requirements = detect_security_requirements(func)
    if security_requirements:
        docs[request_method.lower()]['security'] = security_requirements

    updated_path = endpoint_path
    for param in signature.parameters.values():
        updated_path = process_model_params(
            param, docs[request_method.lower()], updated_path, request_method, schemas
        )

    # Use response_model if provided, otherwise use return annotation
    response_type = response_model if response_model else signature.return_annotation
    process_response(response_type, docs[request_method.lower()], schemas)

    return {updated_path: docs}, schemas
