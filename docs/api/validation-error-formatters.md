# Validation Error Formatters API Reference

The validation error formatter system allows you to customize how validation errors are presented in API responses.

## Base Class: ValidationErrorFormatter

```python
from velithon.exceptions import ValidationErrorFormatter
from pydantic import ValidationError
from typing import Any
```

### Abstract Methods

#### format_validation_error()

```python
def format_validation_error(
    self, 
    error: ValidationError, 
    field_name: str | None = None
) -> dict[str, Any]
```

Format a single validation error.

**Parameters:**
- `error`: The Pydantic ValidationError to format
- `field_name`: Optional field name context

**Returns:**
Dictionary containing the formatted error response.

#### format_validation_errors()

```python
def format_validation_errors(
    self, 
    errors: list[dict[str, Any]]
) -> dict[str, Any]
```

Format multiple validation errors.

**Parameters:**
- `errors`: List of error dictionaries to format

**Returns:**
Dictionary containing the formatted error response.

## Built-in Formatters

### DefaultValidationErrorFormatter

The default formatter maintains Velithon's standard error format.

```python
from velithon.exceptions import DefaultValidationErrorFormatter

formatter = DefaultValidationErrorFormatter()
```

**Example Output:**
```json
{
    "error": {
        "type": "validation_error",
        "details": [
            {
                "field": "age",
                "message": "Input should be greater than or equal to 0",
                "type": "greater_than_equal",
                "input": -1
            }
        ]
    }
}
```

### SimpleValidationErrorFormatter

A minimal formatter with concise error messages.

```python
from velithon.exceptions import SimpleValidationErrorFormatter

formatter = SimpleValidationErrorFormatter()
```

**Example Output:**
```json
{
    "error": "Validation failed",
    "messages": [
        "age: Input should be greater than or equal to 0",
        "email: Input should be a valid email address"
    ]
}
```

### DetailedValidationErrorFormatter

A comprehensive formatter with additional context and help information.

```python
from velithon.exceptions import DetailedValidationErrorFormatter

formatter = DetailedValidationErrorFormatter()
```

**Example Output:**
```json
{
    "status": "error",
    "error_type": "validation_error",
    "message": "Request validation failed",
    "validation_errors": [
        {
            "field": "age",
            "message": "Input should be greater than or equal to 0",
            "type": "greater_than_equal",
            "input": -1,
            "context": {"ge": 0},
            "url": null,
            "help": "must be greater than: 0"
        }
    ],
    "error_count": 1,
    "timestamp": "2025-07-07T12:00:00.000Z"
}
```

### JSONSchemaValidationErrorFormatter

JSON Schema compatible error format.

```python
from velithon.exceptions import JSONSchemaValidationErrorFormatter

formatter = JSONSchemaValidationErrorFormatter()
```

**Example Output:**
```json
{
    "valid": false,
    "errors": [
        {
            "instancePath": "/age",
            "schemaPath": "#/properties/age",
            "keyword": "greater_than_equal",
            "params": {"ge": 0},
            "message": "Input should be greater than or equal to 0",
            "data": -1
        }
    ]
}
```

## Custom Formatter Implementation

### Creating a Custom Formatter

```python
from velithon.exceptions import ValidationErrorFormatter
from pydantic import ValidationError
from typing import Any

class CustomAPIFormatter(ValidationErrorFormatter):
    """Custom formatter for API responses."""
    
    def format_validation_error(
        self, error: ValidationError, field_name: str | None = None
    ) -> dict[str, Any]:
        """Format a single validation error."""
        errors = []
        for err in error.errors():
            field = '.'.join(str(x) for x in err['loc']) if err.get('loc') else field_name
            errors.append({
                "parameter": field,
                "issue": err['msg'],
                "received": err.get('input'),
                "error_code": err['type']
            })
        
        return {
            "success": False,
            "validation_failed": True,
            "issues": errors,
            "help_url": "https://docs.myapi.com/validation-errors"
        }
    
    def format_validation_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        """Format multiple validation errors."""
        all_issues = []
        for error_dict in errors:
            if 'issues' in error_dict:
                all_issues.extend(error_dict['issues'])
        
        return {
            "success": False,
            "validation_failed": True,
            "total_issues": len(all_issues),
            "issues": all_issues,
            "help_url": "https://docs.myapi.com/validation-errors"
        }
```

### Environment-Specific Formatters

```python
import os
from velithon.exceptions import (
    SimpleValidationErrorFormatter,
    DetailedValidationErrorFormatter,
    DefaultValidationErrorFormatter
)

def get_validation_formatter():
    """Get the appropriate formatter based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        # Use simple formatter in production to avoid exposing details
        return SimpleValidationErrorFormatter()
    elif env == "development":
        # Use detailed formatter in development for debugging
        return DetailedValidationErrorFormatter()
    else:
        # Use default formatter for other environments
        return DefaultValidationErrorFormatter()

# Usage
from velithon import Velithon

app = Velithon(validation_error_formatter=get_validation_formatter())
```

## Usage Examples

### Application-Level Formatter

```python
from velithon import Velithon
from velithon.exceptions import DetailedValidationErrorFormatter

app = Velithon(validation_error_formatter=DetailedValidationErrorFormatter())

@app.post("/users")
async def create_user(user: UserModel):
    # All validation errors will use DetailedValidationErrorFormatter
    return {"user": user.dict()}
```

### Router-Level Formatter

```python
from velithon.routing import Router
from velithon.exceptions import SimpleValidationErrorFormatter

router = Router(validation_error_formatter=SimpleValidationErrorFormatter())

@router.post("/items")
async def create_item(item: ItemModel):
    # Uses SimpleValidationErrorFormatter for this router
    return {"item": item.dict()}
```

### Route-Level Formatter

```python
from velithon.exceptions import CustomAPIFormatter

@app.post("/special-endpoint", 
          validation_error_formatter=CustomAPIFormatter())
async def special_endpoint(data: SpecialModel):
    # Uses CustomAPIFormatter for this specific route
    return {"data": data.dict()}
```

### Formatter Hierarchy

The validation error formatter system follows this hierarchy (highest to lowest priority):

1. **Route-level formatter** - specified in route decorators
2. **Router-level formatter** - specified in Router constructor
3. **Application-level formatter** - specified in Velithon constructor
4. **Default formatter** - used when no custom formatter is specified

```python
from velithon import Velithon
from velithon.routing import Router
from velithon.exceptions import (
    DefaultValidationErrorFormatter,
    SimpleValidationErrorFormatter,
    DetailedValidationErrorFormatter
)

# Application-level (fallback)
app = Velithon(validation_error_formatter=DefaultValidationErrorFormatter())

# Router-level (overrides app-level)
router = Router(validation_error_formatter=SimpleValidationErrorFormatter())

@router.post("/users")
async def create_user(user: UserModel):
    # Uses SimpleValidationErrorFormatter from router
    return {"user": user.dict()}

# Route-level (overrides router-level)
@router.get("/users/{user_id}", 
            validation_error_formatter=DetailedValidationErrorFormatter())
async def get_user(user_id: int):
    # Uses DetailedValidationErrorFormatter for this route
    return {"user_id": user_id}

app.include_router(router, prefix="/api")
```

## Testing Custom Formatters

### Unit Testing

```python
import pytest
from pydantic import ValidationError, BaseModel, Field
from your_app.formatters import CustomAPIFormatter

class TestModel(BaseModel):
    name: str = Field(min_length=2)
    age: int = Field(ge=0)

def test_custom_formatter():
    formatter = CustomAPIFormatter()
    
    # Create a validation error
    try:
        TestModel(name="x", age=-1)
    except ValidationError as e:
        result = formatter.format_validation_error(e)
        
        assert result["success"] is False
        assert result["validation_failed"] is True
        assert len(result["issues"]) == 2
        assert result["issues"][0]["parameter"] == "name"
        assert "help_url" in result
```

### Integration Testing

```python
import pytest
import httpx
from your_app import app

@pytest.mark.asyncio
async def test_validation_error_formatting():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Test invalid data
        response = await client.post("/users", json={"name": "", "age": -1})
        
        assert response.status_code == 422
        error_data = response.json()
        
        # Test custom formatter output
        assert "validation_failed" in error_data
        assert "issues" in error_data
        assert len(error_data["issues"]) > 0
```

## Best Practices

### Production Considerations

1. **Use Simple Formatters in Production**
   ```python
   # Don't expose detailed error information in production
   if os.getenv("ENV") == "production":
       formatter = SimpleValidationErrorFormatter()
   else:
       formatter = DetailedValidationErrorFormatter()
   ```

2. **Consistent Error Structure**
   ```python
   class ProductionFormatter(ValidationErrorFormatter):
       def format_validation_error(self, error, field_name=None):
           return {
               "success": False,
               "error_type": "validation_error",
               "message": "Request validation failed",
               "request_id": get_request_id()  # For debugging
           }
   ```

3. **Localization Support**
   ```python
   class LocalizedFormatter(ValidationErrorFormatter):
       def __init__(self, locale="en"):
           self.locale = locale
       
       def format_validation_error(self, error, field_name=None):
           return {
               "error": translate_error(error, self.locale),
               "locale": self.locale
           }
   ```

### Error Monitoring

```python
class MonitoringFormatter(ValidationErrorFormatter):
    def format_validation_error(self, error, field_name=None):
        # Log validation errors for monitoring
        logger.warning(f"Validation error: {error}", extra={
            "field_name": field_name,
            "error_count": len(error.errors())
        })
        
        return {
            "error": "Validation failed",
            "details": [str(e) for e in error.errors()]
        }
```
