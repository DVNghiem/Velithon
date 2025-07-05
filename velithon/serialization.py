"""Automatic serialization detection and handling for response objects.

This module provides utilities to detect and convert objects that can be serialized
to JSON automatically, supporting Pydantic models, dataclasses, regular dicts, lists,
and other JSON-serializable types.
"""

from __future__ import annotations

import dataclasses
import typing
from typing import Any

from velithon.responses import JSONResponse, OptimizedJSONResponse

# Try to import pydantic
try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    BaseModel = None
    HAS_PYDANTIC = False

# Try to import msgpack
try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


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
            isinstance(k, str) and is_json_serializable(v)
            for k, v in obj.items()
        )

    # Exclude functions and methods
    if callable(obj) and not hasattr(obj, '__dict__'):
        return False

    # Exclude built-in functions and types
    if hasattr(obj, '__module__') and obj.__module__ == 'builtins':
        return False

    # Pydantic models
    if HAS_PYDANTIC and isinstance(obj, BaseModel):
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
    if (hasattr(obj, '__dict__') and
        not callable(obj) and
        not isinstance(obj, type)):
        return True

    return False


def is_msgpack_serializable(obj: Any) -> bool:
    """Check if an object can be serialized to MessagePack.

    Args:
        obj: The object to check

    Returns:
        True if the object can be serialized to MessagePack, False otherwise

    """
    if not HAS_MSGPACK:
        return False

    # MessagePack supports JSON-serializable types plus binary data
    if is_json_serializable(obj):
        return True

    # Additional MessagePack-specific types
    if isinstance(obj, bytes | bytearray):
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
    if HAS_PYDANTIC and isinstance(obj, BaseModel):
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


def should_use_optimized_json(obj: Any) -> bool:
    """Determine if we should use OptimizedJSONResponse based on object complexity.

    Args:
        obj: The object to check

    Returns:
        True if OptimizedJSONResponse should be used, False for regular JSONResponse

    """
    def _estimate_complexity(obj: Any, depth: int = 0) -> int:
        """Estimate complexity of an object by counting elements."""
        if depth > 5:  # Prevent infinite recursion
            return 1

        if isinstance(obj, list | tuple):
            return len(obj) + sum(_estimate_complexity(item, depth + 1)
                                 for item in obj[:10])  # Sample first 10
        elif isinstance(obj, dict):
            return len(obj) + sum(_estimate_complexity(v, depth + 1)
                                 for v in list(obj.values())[:10])  # Sample first 10
        else:
            return 1

    complexity = _estimate_complexity(obj)

    # Use optimized JSON for complex objects or large collections
    if isinstance(obj, list | tuple) and len(obj) > 100:
        return True

    if isinstance(obj, dict) and (len(obj) > 50 or complexity > 200):
        return True

    # Use optimized JSON for Pydantic models (they can be complex)
    if HAS_PYDANTIC and isinstance(obj, BaseModel):
        return True

    # Use optimized JSON for dataclasses
    if dataclasses.is_dataclass(obj):
        return True

    # Use optimized JSON for custom objects
    if hasattr(obj, '__dict__') and len(obj.__dict__) > 10:
        return True

    return False


def create_json_response(obj: Any, status_code: int = 200) -> JSONResponse:
    """Create an appropriate JSON response for the given object.

    Args:
        obj: The object to serialize
        status_code: HTTP status code

    Returns:
        JSONResponse or OptimizedJSONResponse based on object complexity

    """
    # Convert object to serializable format
    serialized_obj = serialize_to_dict(obj)

    # Choose the appropriate response type
    if should_use_optimized_json(obj):
        return OptimizedJSONResponse(serialized_obj, status_code=status_code)
    else:
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
        JSONResponse or OptimizedJSONResponse

    Raises:
        TypeError: If the object cannot be serialized

    """
    # Don't serialize if it's already a response
    if is_response_like(obj):
        return obj

    # Check if object is serializable
    if not is_json_serializable(obj):
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return create_json_response(obj, status_code)
