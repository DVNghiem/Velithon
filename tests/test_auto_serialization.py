"""Tests for automatic response serialization feature."""

import dataclasses
from typing import Any

import pytest

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True

    class UserModel(BaseModel):
        id: int
        name: str
        email: str
        active: bool = True

    class ProductModel(BaseModel):
        id: int
        title: str
        price: float
        tags: list[str] = []

except ImportError:
    HAS_PYDANTIC = False
    UserModel = None
    ProductModel = None

from velithon.responses import JSONResponse, OptimizedJSONResponse
from velithon.serialization import (
    auto_serialize_response,
    create_json_response,
    is_json_serializable,
    is_response_like,
    serialize_to_dict,
    should_use_optimized_json,
)


@dataclasses.dataclass
class UserDataclass:
    """Test dataclass for serialization."""
    id: int
    name: str
    email: str
    active: bool = True


class CustomSerializable:
    """Custom class with serialization methods."""

    def __init__(self, data: dict[str, Any]):
        self.data = data

    def __json__(self):
        return self.data


class TestJsonSerializationDetection:
    """Test JSON serialization detection."""

    def test_basic_types_are_serializable(self):
        """Test that basic JSON types are detected as serializable."""
        assert is_json_serializable(None)
        assert is_json_serializable("string")
        assert is_json_serializable(42)
        assert is_json_serializable(3.14)
        assert is_json_serializable(True)
        assert is_json_serializable(False)

    def test_collections_are_serializable(self):
        """Test that collections are detected as serializable."""
        assert is_json_serializable([1, 2, 3])
        assert is_json_serializable((1, 2, 3))
        assert is_json_serializable({"key": "value"})
        assert is_json_serializable({"nested": {"data": [1, 2, 3]}})

    def test_dataclass_is_serializable(self):
        """Test that dataclasses are detected as serializable."""
        user = UserDataclass(1, "John", "john@example.com")
        assert is_json_serializable(user)

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_model_is_serializable(self):
        """Test that Pydantic models are detected as serializable."""
        user = UserModel(id=1, name="John", email="john@example.com")
        assert is_json_serializable(user)

    def test_custom_serializable_is_detected(self):
        """Test that objects with custom serialization are detected."""
        obj = CustomSerializable({"key": "value"})
        assert is_json_serializable(obj)

    def test_complex_object_is_serializable(self):
        """Test that objects with __dict__ are detected as serializable."""
        class SimpleObject:
            def __init__(self):
                self.name = "test"
                self.value = 42

        obj = SimpleObject()
        assert is_json_serializable(obj)

    def test_non_serializable_objects(self):
        """Test that non-serializable objects are detected correctly."""
        # Functions are not serializable
        def test_func(x):
            return x
        assert not is_json_serializable(test_func)

        # Lambda functions are not serializable
        assert not is_json_serializable(lambda x: x)

        # Built-in functions are not serializable
        assert not is_json_serializable(len)

        # Classes/types are not serializable
        assert not is_json_serializable(str)
        assert not is_json_serializable(dict)


class TestObjectSerialization:
    """Test object to dict conversion."""

    def test_basic_types_serialization(self):
        """Test serialization of basic types."""
        assert serialize_to_dict(None) is None
        assert serialize_to_dict("test") == "test"
        assert serialize_to_dict(42) == 42
        assert serialize_to_dict(True) is True

    def test_collections_serialization(self):
        """Test serialization of collections."""
        assert serialize_to_dict([1, 2, 3]) == [1, 2, 3]
        assert serialize_to_dict((1, 2, 3)) == [1, 2, 3]
        assert serialize_to_dict({"key": "value"}) == {"key": "value"}

    def test_nested_serialization(self):
        """Test serialization of nested structures."""
        data = {
            "users": [
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"}
            ],
            "meta": {"total": 2}
        }
        result = serialize_to_dict(data)
        assert result == data

    def test_dataclass_serialization(self):
        """Test serialization of dataclasses."""
        user = UserDataclass(1, "John", "john@example.com")
        result = serialize_to_dict(user)
        expected = {
            "id": 1,
            "name": "John",
            "email": "john@example.com",
            "active": True
        }
        assert result == expected

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_serialization(self):
        """Test serialization of Pydantic models."""
        user = UserModel(id=1, name="John", email="john@example.com")
        result = serialize_to_dict(user)
        expected = {
            "id": 1,
            "name": "John",
            "email": "john@example.com",
            "active": True
        }
        assert result == expected

    def test_custom_serialization(self):
        """Test serialization of objects with custom methods."""
        obj = CustomSerializable({"custom": "data"})
        result = serialize_to_dict(obj)
        assert result == {"custom": "data"}

    def test_object_with_dict_serialization(self):
        """Test serialization of objects with __dict__."""
        class SimpleObject:
            def __init__(self):
                self.name = "test"
                self.value = 42

        obj = SimpleObject()
        result = serialize_to_dict(obj)
        assert result == {"name": "test", "value": 42}


class TestOptimizedJsonDetection:
    """Test detection of when to use optimized JSON."""

    def test_small_objects_use_regular_json(self):
        """Test that small objects use regular JSON."""
        assert not should_use_optimized_json({"small": "object"})
        assert not should_use_optimized_json([1, 2, 3])
        assert not should_use_optimized_json("simple string")

    def test_large_collections_use_optimized_json(self):
        """Test that large collections use optimized JSON."""
        large_list = list(range(200))
        large_dict = {f"key_{i}": i for i in range(100)}

        assert should_use_optimized_json(large_list)
        assert should_use_optimized_json(large_dict)

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_models_use_optimized_json(self):
        """Test that Pydantic models use optimized JSON."""
        user = UserModel(id=1, name="John", email="john@example.com")
        assert should_use_optimized_json(user)

    def test_dataclasses_use_optimized_json(self):
        """Test that dataclasses use optimized JSON."""
        user = UserDataclass(1, "John", "john@example.com")
        assert should_use_optimized_json(user)

    def test_complex_objects_use_optimized_json(self):
        """Test that complex objects use optimized JSON."""
        class ComplexObject:
            def __init__(self):
                for i in range(15):  # More than 10 attributes
                    setattr(self, f"attr_{i}", f"value_{i}")

        obj = ComplexObject()
        assert should_use_optimized_json(obj)


class TestResponseCreation:
    """Test automatic response creation."""

    def test_simple_object_creates_json_response(self):
        """Test that simple objects create JSONResponse."""
        data = {"message": "hello"}
        response = create_json_response(data)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

    def test_complex_object_creates_optimized_response(self):
        """Test that complex objects create OptimizedJSONResponse."""
        data = {f"key_{i}": f"value_{i}" for i in range(100)}
        response = create_json_response(data)

        assert isinstance(response, OptimizedJSONResponse)
        assert response.status_code == 200

    def test_custom_status_code(self):
        """Test response creation with custom status code."""
        data = {"message": "created"}
        response = create_json_response(data, status_code=201)

        assert response.status_code == 201

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_model_response(self):
        """Test response creation from Pydantic model."""
        user = UserModel(id=1, name="John", email="john@example.com")
        response = create_json_response(user)

        assert isinstance(response, OptimizedJSONResponse)
        assert response.status_code == 200


class TestResponseLikeDetection:
    """Test detection of response-like objects."""

    def test_response_objects_detected(self):
        """Test that Response objects are detected."""
        response = JSONResponse({"test": "data"})
        assert is_response_like(response)

    def test_objects_with_response_attributes_detected(self):
        """Test that objects with response-like attributes are detected."""
        class ResponseLike:
            def __init__(self):
                self.status_code = 200
                self.headers = {}

        obj = ResponseLike()
        assert is_response_like(obj)

    def test_regular_objects_not_detected(self):
        """Test that regular objects are not detected as response-like."""
        assert not is_response_like({"data": "value"})
        assert not is_response_like([1, 2, 3])
        assert not is_response_like("string")


class TestAutoSerializeResponse:
    """Test the main auto serialization function."""

    def test_response_objects_returned_unchanged(self):
        """Test that existing Response objects are returned unchanged."""
        original_response = JSONResponse({"test": "data"})
        result = auto_serialize_response(original_response)

        assert result is original_response

    def test_simple_dict_serialization(self):
        """Test automatic serialization of simple dictionaries."""
        data = {"message": "hello", "status": "ok"}
        response = auto_serialize_response(data)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

    def test_large_dict_uses_optimized_response(self):
        """Test that large dictionaries use OptimizedJSONResponse."""
        data = {f"item_{i}": f"value_{i}" for i in range(100)}
        response = auto_serialize_response(data)

        assert isinstance(response, OptimizedJSONResponse)

    @pytest.mark.skipif(not HAS_PYDANTIC, reason="Pydantic not available")
    def test_pydantic_model_serialization(self):
        """Test automatic serialization of Pydantic models."""
        user = UserModel(id=1, name="John", email="john@example.com")
        response = auto_serialize_response(user)

        assert isinstance(response, OptimizedJSONResponse)
        # Check that the response body contains the serialized data
        import orjson
        body_data = orjson.loads(response.body)
        assert body_data["id"] == 1
        assert body_data["name"] == "John"
        assert body_data["email"] == "john@example.com"
        assert body_data["active"] is True

    def test_dataclass_serialization(self):
        """Test automatic serialization of dataclasses."""
        user = UserDataclass(1, "John", "john@example.com")
        response = auto_serialize_response(user)

        assert isinstance(response, OptimizedJSONResponse)
        # Check that the response body contains the serialized data
        import orjson
        body_data = orjson.loads(response.body)
        assert body_data["id"] == 1
        assert body_data["name"] == "John"
        assert body_data["email"] == "john@example.com"
        assert body_data["active"] is True

    def test_custom_status_code_preserved(self):
        """Test that custom status codes are preserved."""
        data = {"error": "not found"}
        response = auto_serialize_response(data, status_code=404)

        assert response.status_code == 404

    def test_non_serializable_raises_error(self):
        """Test that non-serializable objects raise TypeError."""
        # Create a function that's truly not serializable
        def non_serializable(x):
            return x

        with pytest.raises(TypeError, match="is not JSON serializable"):
            auto_serialize_response(non_serializable)

        # Test with built-in function
        with pytest.raises(TypeError, match="is not JSON serializable"):
            auto_serialize_response(len)

        # Test with lambda
        with pytest.raises(TypeError, match="is not JSON serializable"):
            auto_serialize_response(lambda x: x)


if __name__ == "__main__":
    pytest.main([__file__])
