
from typing import Any, Dict, Type, get_args, get_origin, Union, Annotated, Tuple, Sequence, List
from enum import Enum
from pydantic import BaseModel
from pydantic.fields import FieldInfo
import inspect
from velithon.params.params import Depends, Query, Path, Body, Form
from velithon.routing import BaseRoute
from .constants import REF_TEMPLATE

def get_field_type(field):
    return field.outer_type_


def join_url_paths(*parts):
    first = parts[0]
    parts = [part.strip("/") for part in parts]
    starts_with_slash = first.startswith("/") if first else False
    joined = "/".join(part for part in parts if part)
    if starts_with_slash:
        joined = "/" + joined
    return joined


def pydantic_to_swagger(model: type[BaseModel] | dict) -> Dict[str, Any]:
    if isinstance(model, dict):
        schema = {}
        for name, field_type in model.items():
            schema[name] = _process_field(name, field_type, {})
        return schema

    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    for name, field in model.model_fields.items():
        schema["properties"][name] = _process_field(name, field, {})
        if field.is_required():
            schema["required"].append(name)

    return schema


class SchemaProcessor:
    @staticmethod
    def process_union(args: tuple, schemas: Dict[str, Any]) -> Dict[str, Any]:
        if type(None) in args:
            inner_type = next(arg for arg in args if arg is not type(None))
            schema = SchemaProcessor._process_field("", inner_type, schemas)
            schema["nullable"] = True
            return schema
        return {"oneOf": [SchemaProcessor._process_field("", arg, schemas) for arg in args]}

    @staticmethod
    def process_enum(annotation: Type[Enum]) -> Dict[str, Any]:
        return {"type": "string", "enum": [e.value for e in annotation.__members__.values()]}

    @staticmethod
    def process_primitive(annotation: type) -> Dict[str, str]:
        type_mapping = {int: "integer", float: "number", str: "string", bool: "boolean"}
        return {"type": type_mapping.get(annotation, "object")}

    @staticmethod
    def process_list(annotation: type, schemas: Dict[str, Any]) -> Dict[str, Any]:
        schema = {"type": "array"}
        args = get_args(annotation)
        if args:
            item_type = args[0]
            schema["items"] = SchemaProcessor._process_field("item", item_type, schemas)
        else:
            schema["items"] = {}
        return schema

    @staticmethod
    def process_dict(annotation: type, schemas: Dict[str, Any]) -> Dict[str, Any]:
        schema = {"type": "object"}
        args = get_args(annotation)
        if args:
            key_type, value_type = args
            if isinstance(key_type, type) and issubclass(key_type, str):
                schema["additionalProperties"] = SchemaProcessor._process_field("value", value_type, schemas)
        return schema

    @classmethod
    def _process_field(cls, name: str, field: Any, schemas: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(field, FieldInfo):
            annotation = field.annotation
            schema = cls._process_annotation(annotation, schemas)
            if field.description:
                schema["description"] = field.description
            if field.default is not None and field.default is not ...:
                schema["default"] = field.default
            return schema
        return cls._process_annotation(field, schemas)

    @classmethod
    def _process_annotation(cls, annotation: Any, schemas: Dict[str, Any]) -> Dict[str, Any]:
        origin = get_origin(annotation)
        if origin is Annotated:
            base_type, *metadata = get_args(annotation)
            schema = cls._process_annotation(base_type, schemas)
            for meta in metadata:
                if isinstance(meta, (Query, Body, Form)):
                    if meta.description:
                        schema["description"] = meta.description
                    if meta.default is not None and meta.default is not ...:
                        schema["default"] = meta.default
            return schema

        if origin is Union:
            return cls.process_union(get_args(annotation), schemas)

        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return cls.process_enum(annotation)

        if annotation in {int, float, str, bool}:
            return cls.process_primitive(annotation)

        if isinstance(annotation, list) or origin is list:
            return cls.process_list(annotation, schemas)

        if isinstance(annotation, dict) or origin is dict:
            return cls.process_dict(annotation, schemas)

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            schemas[annotation.__name__] = pydantic_to_swagger(annotation)
            return {"$ref": REF_TEMPLATE.format(name=annotation.__name__)}

        return {"type": "object"}


def _process_field(name: str, field: Any, schemas: Dict[str, Any]) -> Dict[str, Any]:
    return SchemaProcessor._process_field(name, field, schemas)


def process_model_params(
    param: inspect.Parameter, 
    docs: Dict, 
    path: str, 
    request_method: str, 
    schemas: Dict[str, Any]
) -> str:
    name = param.name
    annotation = param.annotation
    default = param.default

    # Handle Annotated types
    if get_origin(annotation) is Annotated:
        base_type, *metadata = get_args(annotation)
        schema = _process_field(name, base_type, schemas)
        is_query = False
        is_body = False
        is_form = False
        for meta in metadata:
            if isinstance(meta, Query):
                is_query = True
                docs.setdefault("parameters", []).append({
                    "name": name,
                    "in": "query",
                    "required": meta.default is ...,
                    "schema": schema
                })
                break
            elif isinstance(meta, Body):
                is_body = True
                media_type = meta.media_type if meta.media_type else "application/json"
                docs["requestBody"] = {
                    "content": {
                        media_type: {
                            "schema": schema
                        }
                    },
                    "required": meta.default is ...
                }
                break
            elif isinstance(meta, Form):
                is_form = True
                media_type = meta.media_type if meta.media_type else "multipart/form-data"
                docs["requestBody"] = {
                    "content": {
                        media_type: {
                            "schema": schema
                        }
                    },
                    "required": meta.default is ...
                }
                break
        if is_query or is_body or is_form:
            return path
        annotation = base_type

    if isinstance(default, (Query, Path, Body, Form)):
        schema = _process_field(name, annotation, schemas)
        if default.description:
            schema["description"] = default.description
        if default.default is not None and default.default is not ...:
            schema["default"] = default.default

        if isinstance(default, Path):
            docs.setdefault("parameters", []).append({
                "name": name,
                "in": "path",
                "required": True,
                "schema": schema
            })
            path = path.replace(name, f"{{{name}}}")
        elif isinstance(default, Query):
            docs.setdefault("parameters", []).append({
                "name": name,
                "in": "query",
                "required": default.default is ...,
                "schema": schema
            })
        elif isinstance(default, Body):
            media_type = default.media_type if default.media_type else "application/json"
            docs["requestBody"] = {
                "content": {
                    media_type: {
                        "schema": schema
                    }
                },
                "required": default.default is ...
            }
        elif isinstance(default, Form):
            media_type = default.media_type if default.media_type else "multipart/form-data"
            docs["requestBody"] = {
                "content": {
                    media_type: {
                        "schema": schema
                    }
                 },
                "required": default.default is ...
            }
    elif isinstance(default, Depends):
        return path
    elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if request_method.lower() == "get":
            for field_name, field in annotation.model_fields.items():
                schema = _process_field(field_name, field, schemas)
                docs.setdefault("parameters", []).append({
                    "name": field_name,
                    "in": "query",
                    "required": field.is_required(),
                    "schema": schema
                })
        else:
            docs["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": _process_field(name, annotation, schemas)
                    }
                },
                "required": default is inspect.Parameter.empty
            }
    else:
        schema = _process_field(name, annotation, schemas)
        docs.setdefault("parameters", []).append({
            "name": name,
            "in": "query",
            "required": default is inspect.Parameter.empty,
            "schema": schema
        })

    return path


def process_response(response_type: type, docs: Dict, schemas: Dict[str, Any]) -> None:
    schema = _process_field("response", response_type, schemas)
    docs["responses"] = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": schema
                }
            }
        }
    }


def swagger_generate(func: callable, request_method: str, endpoint_path: str = "/") -> Tuple[Dict, Dict[str, Any]]:
    """
    Generate OpenAPI documentation and schemas for a FastAPI-like API function.

    Args:
        func: The API handler function (e.g., FastAPI endpoint).
        request_method: HTTP method (e.g., "get", "post").
        endpoint_path: The endpoint path (e.g., "/items").

    Returns:
        A tuple of (docs, schemas) where:
        - docs: OpenAPI path specification.
        - schemas: Dictionary of schema definitions for Pydantic models.
    """
    signature = inspect.signature(func)
    schemas: Dict[str, Any] = {}
    docs = {
        request_method.lower(): {
            "summary": func.__name__.replace("_", " ").title(),
            "operationId": func.__name__,
            "parameters": [],
            "responses": {}
        }
    }

    for param in signature.parameters.values():
        endpoint_path = process_model_params(param, docs[request_method.lower()], endpoint_path, request_method, schemas)

    process_response(signature.return_annotation, docs[request_method.lower()], schemas)

    return {endpoint_path: docs}, schemas


def get_openapi(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.1.0",
    summary: str | None = None,
    description: str | None = None,
    routes: Sequence[BaseRoute],
    tags: List[Dict[str, Any]] | None = None,
    servers: List[Dict[str, Union[str, Any]]] | None = None,
    terms_of_service: str | None = None,
    contact: Dict[str, Union[str, Any]] | None= None,
    license_info: Dict[str, Union[str, Any]] | None = None,
) -> Dict[str, Any]:
    main_docs = {
        "openapi": openapi_version,
        "info": {},
        "paths": {},
        "components": {"schemas": {}}
    }
    info: Dict[str, Any] = {"title": title, "version": version}
    if summary:
        info["summary"] = summary
    if description:
        info["description"] = description
    if terms_of_service:
        info["termsOfService"] = terms_of_service
    if contact:
        info["contact"] = contact
    if license_info:
        info["license"] = license_info
    if servers:
        main_docs["servers"] = servers
    for route in routes or []:
        path, schema = route.openapi()
        main_docs["paths"].update(path)
        main_docs["components"]["schemas"].update(schema)
    if tags:
        main_docs["tags"] = tags
    return main_docs
