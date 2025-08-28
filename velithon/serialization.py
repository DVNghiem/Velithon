"""Automatic serialization detection and handling for response objects.

This module provides utilities to detect and convert objects that can be serialized
to JSON automatically, supporting Pydantic models, dataclasses, regular dicts, lists,
and other JSON-serializable types.
"""

from __future__ import annotations

import dataclasses
from typing import Any

# Try to import pydantic
from pydantic import BaseModel

from velithon.responses import JSONResponse


def is_json_serializable(obj: Any) -> bool:
    """Check if an object can be serialized to JSON.

    Args:
        obj: The object to check

    Returns:
        True if the object can be serialized to JSON, False otherwise

    """
    # Basic JSON-serializable types
    if obj is None or isinstance(obj, str | int | float | bool):
        return True

    # Collections
    if isinstance(obj, list | tuple):
        return all(is_json_serializable(item) for item in obj)

    if isinstance(obj, dict):
        return all(
            isinstance(k, str) and is_json_serializable(v) for k, v in obj.items()
        )

    # Exclude functions and methods
    if callable(obj) and not hasattr(obj, '__dict__'):
        return False

    # Exclude built-in functions and types
    if hasattr(obj, '__module__') and obj.__module__ == 'builtins':
        return False

    # Pydantic models
    if isinstance(obj, BaseModel):
        return True

    # Dataclasses
    if dataclasses.is_dataclass(obj):
        return True

    # Objects with custom serialization methods
    if hasattr(obj, 'model_dump') or hasattr(obj, 'dict'):
        return True

    if hasattr(obj, '__json__'):
        return True

    # Objects with __dict__ (basic serialization) but exclude functions/classes
    if hasattr(obj, '__dict__') and not callable(obj) and not isinstance(obj, type):
        return True

    return False

def serialize_to_dict(obj: Any) -> dict[str, Any] | list[Any] | Any:
    """Convert an object to a dictionary or list for JSON serialization.

    Args:
        obj: The object to serialize

    Returns:
        A dictionary, list, or basic type that can be JSON serialized

    Raises:
        TypeError: If the object cannot be serialized

    """
    # Handle None and basic types
    if obj is None or isinstance(obj, str | int | float | bool):
        return obj

    # Handle collections
    if isinstance(obj, list | tuple):
        return [serialize_to_dict(item) for item in obj]

    if isinstance(obj, dict):
        return {k: serialize_to_dict(v) for k, v in obj.items()}

    # Handle Pydantic models
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode='json')

    # Handle dataclasses
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)

    # Handle objects with custom serialization methods
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()

    if hasattr(obj, 'dict'):
        return obj.dict()

    if hasattr(obj, '__json__'):
        return obj.__json__()

    # Handle objects with __dict__
    if hasattr(obj, '__dict__'):
        return {k: serialize_to_dict(v) for k, v in obj.__dict__.items()}

    # If we can't serialize it, return as-is and let JSON encoder handle it
    return obj


def create_json_response(obj: Any, status_code: int = 200) -> JSONResponse:
    """Create a JSON response for the given object.

    Note: For new code, prefer using JSONResponse directly for better performance
    and clearer intent. This helper function is maintained for backward compatibility.

    Args:
        obj: The object to serialize
        status_code: HTTP status code

    Returns:
        JSONResponse with serialized content

    Example:
        # Preferred approach - direct JSONResponse usage
        return JSONResponse(data, status_code=201)

        # Legacy approach - using this helper
        return create_json_response(data, status_code=201)

    """
    # Convert object to serializable format
    serialized_obj = serialize_to_dict(obj)

    # Always use the unified JSONResponse - it handles optimization automatically
    return JSONResponse(serialized_obj, status_code=status_code)


def is_response_like(obj: Any) -> bool:
    """Check if an object is already a response-like object.

    Args:
        obj: The object to check

    Returns:
        True if the object is already a response, False otherwise

    """
    from velithon.responses import Response

    # Check if it's already a Response object
    if isinstance(obj, Response):
        return True

    # Check if it has response-like attributes
    if hasattr(obj, 'status_code') and hasattr(obj, 'headers'):
        return True

    return False


def auto_serialize_response(obj: Any, status_code: int = 200) -> JSONResponse:
    """Automatically serialize an object to an appropriate JSON response.

    This is the main entry point for automatic serialization. It handles:
    - Pydantic models
    - Dataclasses
    - Dictionaries and lists
    - Objects with __dict__
    - Objects with custom serialization methods

    Args:
        obj: The object to serialize
        status_code: HTTP status code

    Returns:
        JSONResponse or JSONResponse

    Raises:
        TypeError: If the object cannot be serialized

    """
    # Don't serialize if it's already a response
    if is_response_like(obj):
        return obj

    # Check if object is serializable
    if not is_json_serializable(obj):
        raise TypeError(f'Object of type {type(obj)} is not JSON serializable')

    return create_json_response(obj, status_code)
