from typing import Any, Dict, Type, get_args, get_origin, Union
from enum import Enum
from pydantic import BaseModel, FieldInfo


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


def pydantic_to_swagger(model: type[BaseModel] | dict):
    if isinstance(model, dict):
        # Handle the case when a dict is passed instead of a Pydantic model
        schema = {}
        for name, field_type in model.items():
            schema[name] = _process_field(name, field_type)
        return schema

    schema = {
        model.__name__: {
            "type": "object",
            "properties": {},
        }
    }

    for name, field in model.model_fields.items():
        schema[model.__name__]["properties"][name] = _process_field(name, field)

    return schema


class SchemaProcessor:
    @staticmethod
    def process_union(args: tuple) -> Dict[str, Any]:
        """Process Union types"""
        if type(None) in args:
            inner_type = next(arg for arg in args if arg is not type(None))
            schema = SchemaProcessor._process_field("", inner_type)
            schema["nullable"] = True
            return schema
        return {"oneOf": [SchemaProcessor._process_field("", arg) for arg in args]}

    @staticmethod
    def process_enum(annotation: Type[Enum]) -> Dict[str, Any]:
        """Process Enum types"""
        return {"type": "string", "enum": [e.value for e in annotation.__members__.values()]}

    @staticmethod
    def process_primitive(annotation: type) -> Dict[str, str]:
        """Process primitive types"""
        type_mapping = {int: "integer", float: "number", str: "string", bool: "boolean"}
        return {"type": type_mapping.get(annotation, "object")}

    @staticmethod
    def process_list(annotation: type) -> Dict[str, Any]:
        """Process list types"""
        schema = {"type": "array"}

        args = get_args(annotation)
        if args:
            item_type = args[0]
            schema["items"] = SchemaProcessor._process_field("item", item_type)
        else:
            schema["items"] = {}
        return schema

    @staticmethod
    def process_dict(annotation: type) -> Dict[str, Any]:
        """Process dict types"""
        schema = {"type": "object"}

        args = get_args(annotation)
        if args:
            key_type, value_type = args
            if key_type == str:  # noqa: E721
                schema["additionalProperties"] = SchemaProcessor._process_field("value", value_type)
        return schema

    @classmethod
    def _process_field(cls, name: str, field: Any) -> Dict[str, Any]:
        """Process a single field"""
        if isinstance(field, FieldInfo):
            annotation = field.annotation
        else:
            annotation = field

        # Process Union types
        origin = get_origin(annotation)
        if origin is Union:
            return cls.process_union(get_args(annotation))

        # Process Enum types
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return cls.process_enum(annotation)

        # Process primitive types
        if annotation in {int, float, str, bool}:
            return cls.process_primitive(annotation)

        # Process list types
        if annotation == list or origin is list:  # noqa: E721
            return cls.process_list(annotation)

        # Process dict types
        if annotation == dict or origin is dict:  # noqa: E721
            return cls.process_dict(annotation)

        # Process Pydantic models
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return pydantic_to_swagger(annotation)

        # Fallback for complex types
        return {"type": "object"}


def _process_field(name: str, field: Any) -> Dict[str, Any]:
    """
    Process a field and return its schema representation

    Args:
        name: Field name
        field: Field type or FieldInfo object

    Returns:
        Dictionary representing the JSON schema for the field
    """
    return SchemaProcessor._process_field(name, field)
