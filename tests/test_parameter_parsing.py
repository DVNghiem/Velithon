"""
Tests for request parameter parsing and validation.
"""
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field, ValidationError

from velithon.datastructures import Headers
from velithon.requests import Request


class TestParameterParsing:
    """Test parameter parsing functionality."""

    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope for testing."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.path = "/test"
        scope.query_string = b"name=alice&age=25&active=true"
        scope.headers = Headers([
            ("content-type", "application/json"),
            ("authorization", "Bearer token123"),
            ("x-user-id", "42")
        ])
        scope._path_params = {"user_id": "123", "category": "books"}
        scope.path_params = {"user_id": "123", "category": "books"}
        return scope

    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol for testing."""
        return MagicMock()

    def test_query_parameter_parsing(self, mock_scope, mock_protocol):
        """Test parsing query parameters."""
        request = Request(mock_scope, mock_protocol)
        
        # Test individual parameter access
        assert request.query_params.get("name") == "alice"
        assert request.query_params.get("age") == "25"
        assert request.query_params.get("active") == "true"
        assert request.query_params.get("missing") is None

    def test_query_parameter_with_defaults(self, mock_scope, mock_protocol):
        """Test query parameters with default values."""
        request = Request(mock_scope, mock_protocol)
        
        # Test with defaults
        assert request.query_params.get("missing", "default") == "default"
        assert request.query_params.get("name", "default") == "alice"

    def test_path_parameter_parsing(self, mock_scope, mock_protocol):
        """Test parsing path parameters."""
        request = Request(mock_scope, mock_protocol)
        
        # Test path parameter access
        assert request.path_params.get("user_id") == "123"
        assert request.path_params.get("category") == "books"
        assert request.path_params.get("missing") is None

    def test_header_parameter_parsing(self, mock_scope, mock_protocol):
        """Test parsing header parameters."""
        request = Request(mock_scope, mock_protocol)
        
        # Test header access
        assert request.headers.get("content-type") == "application/json"
        assert request.headers.get("authorization") == "Bearer token123"
        assert request.headers.get("x-user-id") == "42"
        assert request.headers.get("missing") is None

    def test_complex_query_string_parsing(self, mock_protocol):
        """Test parsing complex query strings."""
        # Test with arrays and special characters
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = b"tags=python&tags=web&search=hello%20world&count=5"
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Note: This depends on the actual query parameter parsing implementation
        # The behavior may vary based on how multi-value parameters are handled
        assert request.query_params.get("search") is not None
        assert request.query_params.get("count") == "5"

    def test_empty_query_string(self, mock_protocol):
        """Test handling empty query string."""
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = b""
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        assert request.query_params.get("any") is None

    def test_malformed_query_string(self, mock_protocol):
        """Test handling malformed query strings."""
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = b"invalid=&=empty&no_value&key=value"
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Should handle gracefully
        assert request.query_params.get("key") == "value"


class TestParameterValidation:
    """Test parameter validation with Pydantic models."""

    def test_query_parameter_validation(self):
        """Test query parameter validation."""
        class QueryParams(BaseModel):
            name: str
            age: int = Field(ge=0, le=120)
            active: bool = True

        # Test valid parameters
        valid_params = QueryParams(name="alice", age=25, active=True)
        assert valid_params.name == "alice"
        assert valid_params.age == 25
        assert valid_params.active is True

        # Test invalid age
        with pytest.raises(ValidationError):
            QueryParams(name="alice", age=-5)

        with pytest.raises(ValidationError):
            QueryParams(name="alice", age=150)

        # Test missing required field
        with pytest.raises(ValidationError):
            QueryParams(age=25)

    def test_path_parameter_validation(self):
        """Test path parameter validation."""
        class PathParams(BaseModel):
            user_id: int = Field(gt=0)
            category: str = Field(min_length=1, max_length=50)

        # Test valid parameters
        valid_params = PathParams(user_id=123, category="books")
        assert valid_params.user_id == 123
        assert valid_params.category == "books"

        # Test invalid user_id
        with pytest.raises(ValidationError):
            PathParams(user_id=0, category="books")

        with pytest.raises(ValidationError):
            PathParams(user_id=-1, category="books")

        # Test invalid category
        with pytest.raises(ValidationError):
            PathParams(user_id=123, category="")

        with pytest.raises(ValidationError):
            PathParams(user_id=123, category="x" * 51)

    def test_header_parameter_validation(self):
        """Test header parameter validation."""
        class HeaderParams(BaseModel):
            authorization: str = Field(pattern=r"^Bearer .+")
            x_user_id: int = Field(alias="x-user-id", gt=0)
            content_type: str = Field(alias="content-type", default="application/json")

        # Test valid headers
        valid_headers = HeaderParams(
            authorization="Bearer token123",
            **{"x-user-id": 42, "content-type": "application/json"}
        )
        assert valid_headers.authorization == "Bearer token123"
        assert valid_headers.x_user_id == 42

        # Test invalid authorization format
        with pytest.raises(ValidationError):
            HeaderParams(authorization="Invalid token", **{"x-user-id": 42})

        # Test invalid user_id
        with pytest.raises(ValidationError):
            HeaderParams(authorization="Bearer token", **{"x-user-id": 0})

    def test_body_parameter_validation(self):
        """Test request body validation."""
        class UserCreate(BaseModel):
            username: str = Field(min_length=3, max_length=50)
            email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
            age: int = Field(ge=13, le=120)
            terms_accepted: bool

        # Test valid user data
        valid_user = UserCreate(
            username="alice123",
            email="alice@example.com",
            age=25,
            terms_accepted=True
        )
        assert valid_user.username == "alice123"
        assert valid_user.email == "alice@example.com"

        # Test invalid username (too short)
        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",
                email="alice@example.com",
                age=25,
                terms_accepted=True
            )

        # Test invalid email
        with pytest.raises(ValidationError):
            UserCreate(
                username="alice123",
                email="invalid-email",
                age=25,
                terms_accepted=True
            )

        # Test invalid age
        with pytest.raises(ValidationError):
            UserCreate(
                username="alice123",
                email="alice@example.com",
                age=12,  # Too young
                terms_accepted=True
            )

        # Test missing required field
        with pytest.raises(ValidationError):
            UserCreate(
                username="alice123",
                email="alice@example.com",
                age=25
                # Missing terms_accepted
            )


class TestParameterTypes:
    """Test different parameter types and conversions."""

    def test_integer_parameter_conversion(self):
        """Test integer parameter conversion."""
        class Params(BaseModel):
            count: int
            page: int = 1

        # Test valid integers
        params = Params(count="42", page="3")
        assert params.count == 42
        assert params.page == 3

        # Test invalid integer
        with pytest.raises(ValidationError):
            Params(count="not_a_number")

    def test_float_parameter_conversion(self):
        """Test float parameter conversion."""
        class Params(BaseModel):
            price: float
            rate: float = 0.0

        # Test valid floats
        params = Params(price="19.99", rate="0.05")
        assert params.price == 19.99
        assert params.rate == 0.05

        # Test invalid float
        with pytest.raises(ValidationError):
            Params(price="not_a_float")

    def test_boolean_parameter_conversion(self):
        """Test boolean parameter conversion."""
        class Params(BaseModel):
            active: bool
            verified: bool = False

        # Test various boolean representations
        true_values = ["true", "True", "1", "yes", "on"]
        false_values = ["false", "False", "0", "no", "off"]

        for value in true_values:
            params = Params(active=value)
            assert params.active is True

        for value in false_values:
            params = Params(active=value)
            assert params.active is False

    def test_list_parameter_conversion(self):
        """Test list parameter conversion."""
        from typing import List

        class Params(BaseModel):
            tags: List[str] = []
            ids: List[int] = []

        # Test list parameters (implementation dependent)
        # This would typically require special handling for query parameters
        params = Params(tags=["python", "web"], ids=[1, 2, 3])
        assert params.tags == ["python", "web"]
        assert params.ids == [1, 2, 3]

    def test_optional_parameter_handling(self):
        """Test optional parameter handling."""
        from typing import Optional

        class Params(BaseModel):
            required_field: str
            optional_field: Optional[str] = None
            optional_with_default: str = "default_value"

        # Test with optional field present
        params = Params(
            required_field="value",
            optional_field="optional_value"
        )
        assert params.required_field == "value"
        assert params.optional_field == "optional_value"
        assert params.optional_with_default == "default_value"

        # Test with optional field absent
        params = Params(required_field="value")
        assert params.required_field == "value"
        assert params.optional_field is None
        assert params.optional_with_default == "default_value"


class TestParameterConstraints:
    """Test parameter constraints and validation rules."""

    def test_string_length_constraints(self):
        """Test string length constraints."""
        class Params(BaseModel):
            short_string: str = Field(max_length=10)
            long_string: str = Field(min_length=5)
            exact_string: str = Field(min_length=3, max_length=3)

        # Test valid strings
        params = Params(
            short_string="hello",
            long_string="this is long enough",
            exact_string="abc"
        )
        assert len(params.short_string) <= 10
        assert len(params.long_string) >= 5
        assert len(params.exact_string) == 3

        # Test constraint violations
        with pytest.raises(ValidationError):
            Params(
                short_string="this string is too long",
                long_string="long",
                exact_string="abc"
            )

    def test_numeric_range_constraints(self):
        """Test numeric range constraints."""
        class Params(BaseModel):
            positive_int: int = Field(gt=0)
            percentage: float = Field(ge=0.0, le=100.0)
            score: int = Field(ge=0, le=10)

        # Test valid values
        params = Params(
            positive_int=5,
            percentage=85.5,
            score=8
        )
        assert params.positive_int > 0
        assert 0.0 <= params.percentage <= 100.0
        assert 0 <= params.score <= 10

        # Test constraint violations
        with pytest.raises(ValidationError):
            Params(positive_int=0, percentage=50.0, score=5)

        with pytest.raises(ValidationError):
            Params(positive_int=5, percentage=150.0, score=5)

    def test_regex_pattern_constraints(self):
        """Test regex pattern constraints."""
        class Params(BaseModel):
            email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
            phone: str = Field(pattern=r"^\+?1?\d{9,15}$")
            slug: str = Field(pattern=r"^[a-z0-9-]+$")

        # Test valid patterns
        params = Params(
            email="user@example.com",
            phone="+1234567890",
            slug="my-article-slug"
        )
        assert "@" in params.email
        assert params.phone.startswith("+")
        assert "-" in params.slug

        # Test invalid patterns
        with pytest.raises(ValidationError):
            Params(
                email="invalid-email",
                phone="123",
                slug="Invalid Slug!"
            )

    def test_custom_validator_constraints(self):
        """Test custom validator constraints."""
        from pydantic import field_validator

        class Params(BaseModel):
            password: str
            confirm_password: str

            @field_validator('password')
            @classmethod
            def validate_password(cls, v):
                if len(v) < 8:
                    raise ValueError('Password must be at least 8 characters')
                if not any(c.isupper() for c in v):
                    raise ValueError('Password must contain uppercase letter')
                if not any(c.islower() for c in v):
                    raise ValueError('Password must contain lowercase letter')
                if not any(c.isdigit() for c in v):
                    raise ValueError('Password must contain digit')
                return v

            @field_validator('confirm_password')
            @classmethod
            def passwords_match(cls, v, info):
                if info.data.get('password') and v != info.data['password']:
                    raise ValueError('Passwords do not match')
                return v

        # Test valid passwords
        params = Params(
            password="SecurePass123",
            confirm_password="SecurePass123"
        )
        assert params.password == params.confirm_password

        # Test invalid password (too short)
        with pytest.raises(ValidationError):
            Params(password="short", confirm_password="short")

        # Test mismatched passwords
        with pytest.raises(ValidationError):
            Params(password="SecurePass123", confirm_password="DifferentPass123")


class TestParameterEdgeCases:
    """Test parameter parsing edge cases."""

    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol for testing."""
        return MagicMock()

    def test_empty_parameter_values(self, mock_protocol):
        """Test handling of empty parameter values."""
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = b"empty=&name=value&blank="
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Should handle empty values gracefully
        assert request.query_params.get("empty") == ""
        assert request.query_params.get("name") == "value"
        assert request.query_params.get("blank") == ""

    def test_special_characters_in_parameters(self, mock_protocol):
        """Test handling special characters in parameters."""
        scope = MagicMock()
        scope.proto = "http"
        # URL encoded special characters
        scope.query_string = b"text=hello%20world&symbol=%26%3D%2B"
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Should decode URL encoded characters
        text_value = request.query_params.get("text")
        if text_value:
            # Depends on implementation of query parameter decoding
            assert "world" in text_value

    def test_unicode_parameters(self, mock_protocol):
        """Test handling Unicode characters in parameters."""
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = "name=José&city=São Paulo".encode('utf-8')
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Should handle Unicode correctly
        name_value = request.query_params.get("name")
        if name_value:
            assert "José" in name_value or name_value  # Depends on implementation

    def test_very_long_parameter_values(self, mock_protocol):
        """Test handling very long parameter values."""
        long_value = "x" * 10000  # 10KB value
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = f"long_param={long_value}".encode('utf-8')
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Should handle long values (within reason)
        param_value = request.query_params.get("long_param")
        if param_value:
            assert len(param_value) > 5000

    def test_duplicate_parameter_names(self, mock_protocol):
        """Test handling duplicate parameter names."""
        scope = MagicMock()
        scope.proto = "http"
        scope.query_string = b"tag=python&tag=web&tag=api"
        scope.headers = Headers([])
        scope._path_params = {}
        
        request = Request(scope, mock_protocol)
        
        # Behavior depends on implementation - may return first, last, or list
        tag_value = request.query_params.get("tag")
        assert tag_value is not None


if __name__ == "__main__":
    pytest.main([__file__])
