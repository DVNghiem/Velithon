"""Test validation error formatter functionality."""
from typing import Any

import pytest
from pydantic import BaseModel, Field, ValidationError

from velithon.application import Velithon
from velithon.exceptions import (
    DefaultValidationErrorFormatter,
    DetailedValidationErrorFormatter,
    SimpleValidationErrorFormatter,
    ValidationErrorFormatter,
)
from velithon.params import Body, Query
from velithon.responses import JSONResponse
from velithon.routing import Router

# Module-level constants to avoid function calls in defaults
BODY_PARAM = Body()
QUERY_AGE_PARAM = Query(ge=0, le=120)


class CustomValidationFormatter(ValidationErrorFormatter):
    """Custom validation formatter for testing."""
    
    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format a validation error with custom structure."""
        return {
            "validation_failed": True,
            "error_info": {
                "field": field_name or "unknown",
                "details": str(error),
                "custom_field": "custom_value",
            },
        }
    
    def format_validation_errors(self, errors: list[dict]) -> dict:
        """Format validation errors with custom structure."""
        return {
            "validation_failed": True,
            "error_count": len(errors),
            "issues": [
                {
                    "parameter": error["field"],
                    "problem": error["msg"],
                    "custom_field": "custom_value",
                }
                for error in errors
            ],
        }


class UserModel(BaseModel):
    """Test model for validation."""
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=120)
    email: str = Field(pattern=r'^[^@]+@[^@]+\.[^@]+$')


class TestValidationErrorFormatter:
    """Test custom validation error formatters."""
    
    def test_default_formatter_used_when_none_specified(self):
        """Test that default formatter is used when none specified."""
        app = Velithon()
        
        @app.post("/test")
        async def test_endpoint(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # The app should use the default formatter
        assert app.validation_error_formatter is None
        # Router should also have None (inherits from app)
        assert app.router.validation_error_formatter is None
    
    def test_app_level_formatter(self):
        """Test that app-level formatter is used."""
        formatter = CustomValidationFormatter()
        app = Velithon(validation_error_formatter=formatter)
        
        @app.post("/test")
        async def test_endpoint(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # App should have the custom formatter
        assert app.validation_error_formatter is formatter
        # Router should inherit the formatter from app
        assert app.router.validation_error_formatter is formatter
    
    def test_router_level_formatter(self):
        """Test that router-level formatter is used."""
        router_formatter = CustomValidationFormatter()
        router = Router(validation_error_formatter=router_formatter)
        
        @router.post("/test")
        async def test_endpoint(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # Router should have the custom formatter
        assert router.validation_error_formatter is router_formatter
        # Routes should inherit the formatter from router
        assert router.routes[0].validation_error_formatter is router_formatter
    
    def test_route_level_formatter_overrides_router(self):
        """Test that route-level formatter overrides router formatter."""
        router_formatter = SimpleValidationErrorFormatter()
        route_formatter = CustomValidationFormatter()
        
        app = Velithon(validation_error_formatter=router_formatter)
        
        @app.post("/test", validation_error_formatter=route_formatter)
        async def test_endpoint(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # App should have the router formatter
        assert app.validation_error_formatter is router_formatter
        # But the route should have the route-specific formatter
        # Find the test route (not the OpenAPI route)
        test_route = None
        for route in app.router.routes:
            if hasattr(route, 'path') and route.path == "/test":
                test_route = route
                break
        
        assert test_route is not None
        assert test_route.validation_error_formatter is route_formatter
    
    def test_built_in_formatters_work(self):
        """Test that all built-in formatters work."""
        # Create a mock ValidationError
        try:
            UserModel(name="x", age=-1, email="invalid")
        except ValidationError as e:
            validation_error = e
        
        # Test DefaultValidationErrorFormatter
        default_formatter = DefaultValidationErrorFormatter()
        result = default_formatter.format_validation_error(validation_error)
        assert "error" in result
        assert "details" in result["error"]
        assert len(result["error"]["details"]) >= 2
        
        # Test SimpleValidationErrorFormatter
        simple_formatter = SimpleValidationErrorFormatter()
        result = simple_formatter.format_validation_error(validation_error)
        assert "error" in result
        assert "messages" in result
        assert len(result["messages"]) >= 2
        
        # Test DetailedValidationErrorFormatter
        detailed_formatter = DetailedValidationErrorFormatter()
        result = detailed_formatter.format_validation_error(validation_error)
        assert "validation_errors" in result
        assert "error_count" in result
        assert result["error_count"] >= 2
    
    def test_custom_formatter_implementation(self):
        """Test custom formatter implementation."""
        formatter = CustomValidationFormatter()
        error_data = [
            {"field": "name", "msg": "String too short"},
            {"field": "age", "msg": "Value must be greater than 0"},
        ]
        
        result = formatter.format_validation_errors(error_data)
        
        assert result["validation_failed"] is True
        assert result["error_count"] == 2
        assert len(result["issues"]) == 2
        assert result["issues"][0]["parameter"] == "name"
        assert result["issues"][0]["problem"] == "String too short"
        assert result["issues"][0]["custom_field"] == "custom_value"
    
    def test_formatter_inheritance_hierarchy(self):
        """Test that formatters are inherited properly in the hierarchy."""
        # App level formatter
        app_formatter = DefaultValidationErrorFormatter()
        app = Velithon(validation_error_formatter=app_formatter)
        
        # Router level formatter (should override app)
        router_formatter = SimpleValidationErrorFormatter()
        custom_router = Router(validation_error_formatter=router_formatter)
        
        # Route level formatter (should override router)
        route_formatter = CustomValidationFormatter()
        
        @custom_router.post("/test", validation_error_formatter=route_formatter)
        async def test_endpoint(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # Add the router to the app
        app.include_router(custom_router, prefix="/api")
        
        # Check that the route has the route-specific formatter
        # The route should be in the app's router now
        added_route = None
        for route in app.router.routes:
            if hasattr(route, 'path') and route.path == "/api/test":
                added_route = route
                break
        
        assert added_route is not None
        # The route should preserve its custom formatter
        assert added_route.validation_error_formatter is route_formatter
    
    def test_query_parameter_validation_with_custom_formatter(self):
        """Test that custom formatter works with query parameter validation."""
        formatter = CustomValidationFormatter()
        app = Velithon(validation_error_formatter=formatter)
        
        @app.get("/test")
        async def test_endpoint(age: int = QUERY_AGE_PARAM):
            return JSONResponse({"age": age})
        
        # The route should have the custom formatter
        route = app.router.routes[0]
        assert route.validation_error_formatter is formatter
    
    def test_multiple_routers_with_different_formatters(self):
        """Test multiple routers with different formatters."""
        app = Velithon()
        
        # Router 1 with SimpleValidationErrorFormatter
        router1 = Router(validation_error_formatter=SimpleValidationErrorFormatter())
        
        @router1.post("/test1")
        async def test1(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # Router 2 with CustomValidationFormatter
        router2 = Router(validation_error_formatter=CustomValidationFormatter())
        
        @router2.post("/test2")
        async def test2(user: UserModel = BODY_PARAM):
            return JSONResponse({"user": user.dict()})
        
        # Add both routers
        app.include_router(router1, prefix="/api1")
        app.include_router(router2, prefix="/api2")
        
        # Find the routes and check their formatters
        route1 = None
        route2 = None
        for route in app.router.routes:
            if hasattr(route, 'path'):
                if route.path == "/api1/test1":
                    route1 = route
                elif route.path == "/api2/test2":
                    route2 = route
        
        assert route1 is not None
        assert route2 is not None
        assert isinstance(route1.validation_error_formatter, SimpleValidationErrorFormatter)
        assert isinstance(route2.validation_error_formatter, CustomValidationFormatter)


if __name__ == "__main__":
    pytest.main([__file__])
