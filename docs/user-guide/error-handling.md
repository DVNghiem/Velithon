# Error Handling

Velithon provides a comprehensive error handling system with structured exceptions, custom formatters, middleware-based error processing, and production-ready error responses.

## Overview

Velithon's error handling features:
- **Structured HTTP Exceptions** with standardized error formats
- **Custom Error Formatters** for different response styles
- **Middleware-based Processing** for global error handling
- **Built-in Security** with safe error messages
- **Type Safety** with full typing support
- **Production Ready** with configurable error levels

## HTTP Exceptions

### Basic Exception Usage

```python
from velithon import Velithon
from velithon.exceptions import HTTPException
from velithon.responses import JSONResponse

app = Velithon()

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Basic validation
    if user_id < 1:
        raise HTTPException(
            status_code=400, 
            detail="Invalid user ID"
        )
    
    # Simulate user lookup
    user = find_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="User not found"
        )
    
    return JSONResponse({"user": user})
```

### Using Predefined Exceptions

```python
from velithon.exceptions import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    InternalServerException
)

@app.get("/protected/{resource_id}")
async def get_protected_resource(resource_id: int, user_id: int = None):
    # Authentication check
    if not user_id:
        raise UnauthorizedException(
            details={"message": "Authentication required"}
        )
    
    # Resource validation
    if resource_id < 1:
        raise BadRequestException(
            details={"message": "Invalid resource ID", "field": "resource_id"}
        )
    
    # Resource lookup
    resource = find_resource(resource_id)
    if not resource:
        raise NotFoundException(
            details={"message": f"Resource {resource_id} not found"}
        )
    
    # Permission check
    if not user_has_access(user_id, resource_id):
        raise ForbiddenException(
            details={"message": "Access denied to this resource"}
        )
    
    return JSONResponse({"resource": resource})
```

### Validation Errors

```python
from velithon.params import Query
from pydantic import BaseModel, validator

class UserCreateRequest(BaseModel):
    name: str
    email: str
    age: int
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

@app.post("/users")
async def create_user(user_data: UserCreateRequest):
    try:
        # Process user creation
        user = create_user_in_db(user_data)
        return JSONResponse({"user": user, "status": "created"})
        
    except ValueError as e:
        raise ValidationException(
            details={
                "message": "Validation failed",
                "errors": [str(e)]
            }
        )
    except Exception as e:
        raise InternalServerException(
            details={"message": "Failed to create user"}
        )
```

## Custom Exception Classes

### Creating Custom Exceptions

```python
from velithon.exceptions import HTTPException, ErrorDefinitions

class CustomBusinessException(HTTPException):
    """Custom exception for business logic errors"""
    
    def __init__(self, message: str, error_code: str = "BUSINESS_ERROR"):
        super().__init__(
            status_code=422,
            error=ErrorDefinitions.VALIDATION_ERROR,
            details={
                "message": message,
                "error_code": error_code,
                "error_type": "business_logic"
            }
        )

class ResourceConflictException(HTTPException):
    """Exception for resource conflicts"""
    
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            status_code=409,
            error=ErrorDefinitions.CONFLICT,
            details={
                "message": f"{resource_type} with identifier '{identifier}' already exists",
                "resource_type": resource_type,
                "identifier": identifier
            }
        )

# Usage examples
@app.post("/products")
async def create_product(product_data: dict):
    # Business logic validation
    if product_data.get("price", 0) <= 0:
        raise CustomBusinessException(
            "Product price must be greater than zero",
            "INVALID_PRICE"
        )
    
    # Check for existing product
    existing = find_product_by_sku(product_data.get("sku"))
    if existing:
        raise ResourceConflictException("Product", product_data["sku"])
    
    # Create product
    product = create_product_in_db(product_data)
    return JSONResponse({"product": product})
```

### Exception with Custom Formatting

```python
from velithon.exceptions import ResponseFormatter

class APIErrorFormatter(ResponseFormatter):
    """Custom error formatter for API responses"""
    
    def format_error(self, exception: HTTPException) -> dict:
        return {
            "success": False,
            "error": {
                "code": exception.error.code if exception.error else "UNKNOWN",
                "message": exception.error.message if exception.error else "Unknown error",
                "status_code": exception.status_code,
                "details": exception.details or {},
                "timestamp": datetime.now().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        }

class DetailedAPIException(HTTPException):
    """Exception with detailed API formatting"""
    
    def __init__(self, status_code: int, message: str, **details):
        super().__init__(
            status_code=status_code,
            error=ErrorDefinitions.VALIDATION_ERROR,
            details={"message": message, **details},
            formatter=APIErrorFormatter()
        )

@app.get("/api/detailed-error")
async def detailed_error_example():
    raise DetailedAPIException(
        status_code=400,
        message="Detailed validation error",
        field="email",
        expected_format="user@domain.com",
        received_value="invalid-email"
    )
```

## Error Middleware

### Global Error Handling Middleware

```python
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.datastructures import Scope, Protocol
from velithon.responses import JSONResponse
import traceback
import logging

logger = logging.getLogger(__name__)

class GlobalErrorMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    def __init__(self, app, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def process_http_request(self, scope: Scope, protocol: Protocol):
        try:
            await self.app(scope, protocol)
            
        except HTTPException as e:
            # Handle HTTP exceptions
            error_response = JSONResponse(
                content=e.to_dict(),
                status_code=e.status_code,
                headers=e.headers
            )
            await error_response(scope, protocol)
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            error_response = JSONResponse(
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": e.errors()
                    }
                },
                status_code=422
            )
            await error_response(scope, protocol)
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            
            if self.debug:
                # Include traceback in debug mode
                error_content = {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": str(e),
                        "traceback": traceback.format_exc().split('\n')
                    }
                }
            else:
                # Generic error message in production
                error_content = {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal server error occurred"
                    }
                }
            
            error_response = JSONResponse(
                content=error_content,
                status_code=500
            )
            await error_response(scope, protocol)

# Add to application
from velithon.middleware import Middleware

app = Velithon(
    middleware=[
        Middleware(GlobalErrorMiddleware, debug=True)  # Set debug=False in production
    ]
)
```

### Authentication Error Middleware

```python
from velithon.middleware.auth import AuthenticationMiddleware
from velithon.security.exceptions import AuthenticationError, AuthorizationError

class CustomAuthMiddleware(BaseHTTPMiddleware):
    """Custom authentication error handling"""
    
    async def process_http_request(self, scope: Scope, protocol: Protocol):
        try:
            await self.app(scope, protocol)
            
        except AuthenticationError as e:
            error_response = JSONResponse(
                content={
                    "error": "Authentication Failed",
                    "detail": str(e),
                    "type": "authentication_error",
                    "help": "Please provide valid authentication credentials"
                },
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"}
            )
            await error_response(scope, protocol)
            
        except AuthorizationError as e:
            error_response = JSONResponse(
                content={
                    "error": "Authorization Failed",
                    "detail": str(e),
                    "type": "authorization_error",
                    "help": "You don't have permission to access this resource"
                },
                status_code=403
            )
            await error_response(scope, protocol)

app = Velithon(
    middleware=[
        Middleware(CustomAuthMiddleware),
        Middleware(GlobalErrorMiddleware)
    ]
)
```

## Error Formatters

### Built-in Formatters

```python
from velithon.exceptions import (
    SimpleFormatter,
    DetailedFormatter,
    LocalizedFormatter
)

# Simple formatter - minimal error info
HTTPException.set_formatter(SimpleFormatter())

# Detailed formatter - comprehensive error details
HTTPException.set_formatter(DetailedFormatter())

# Localized formatter - translated error messages
HTTPException.set_formatter(LocalizedFormatter(language="en"))
```

### Custom Formatter Examples

```python
class ProductionErrorFormatter(ResponseFormatter):
    """Production-safe error formatter"""
    
    def format_error(self, exception: HTTPException) -> dict:
        # Never expose internal details in production
        safe_codes = [400, 401, 403, 404, 422, 429]
        
        if exception.status_code in safe_codes:
            return {
                "error": {
                    "code": exception.error.code if exception.error else "CLIENT_ERROR",
                    "message": exception.error.message if exception.error else "Client error",
                    "status": exception.status_code
                }
            }
        else:
            # Generic message for server errors
            return {
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred processing your request",
                    "status": exception.status_code
                }
            }

class DevelopmentErrorFormatter(ResponseFormatter):
    """Development-friendly error formatter with full details"""
    
    def format_error(self, exception: HTTPException) -> dict:
        return {
            "error": {
                "code": exception.error.code if exception.error else "UNKNOWN",
                "message": exception.error.message if exception.error else str(exception),
                "status": exception.status_code,
                "details": exception.details or {},
                "headers": exception.headers,
                "traceback": traceback.format_exc() if hasattr(exception, '__traceback__') else None
            },
            "debug_info": {
                "exception_type": type(exception).__name__,
                "timestamp": datetime.now().isoformat()
            }
        }

# Set formatter based on environment
import os

if os.getenv("ENV") == "production":
    HTTPException.set_formatter(ProductionErrorFormatter())
else:
    HTTPException.set_formatter(DevelopmentErrorFormatter())
```

## Error Response Examples

### Standardized Error Responses

```python
@app.get("/demo/errors/{error_type}")
async def demonstrate_errors(error_type: str):
    """Demonstrate different error types"""
    
    if error_type == "bad_request":
        raise BadRequestException(
            details={
                "message": "Invalid request parameters",
                "invalid_fields": ["user_id", "category"]
            }
        )
    
    elif error_type == "unauthorized":
        raise UnauthorizedException(
            details={
                "message": "Invalid or expired token",
                "auth_required": True
            }
        )
    
    elif error_type == "forbidden":
        raise ForbiddenException(
            details={
                "message": "Insufficient permissions",
                "required_role": "admin"
            }
        )
    
    elif error_type == "not_found":
        raise NotFoundException(
            details={
                "message": "Resource not found",
                "resource_type": "user",
                "searched_id": 12345
            }
        )
    
    elif error_type == "validation":
        raise ValidationException(
            details={
                "message": "Data validation failed",
                "errors": [
                    {"field": "email", "error": "Invalid email format"},
                    {"field": "age", "error": "Must be between 0 and 150"}
                ]
            }
        )
    
    elif error_type == "rate_limit":
        from velithon.exceptions import RateLimitException
        raise RateLimitException(
            retry_after=60,
            details={
                "message": "Rate limit exceeded",
                "limit": 100,
                "window": "1 hour"
            }
        )
    
    elif error_type == "server_error":
        raise InternalServerException(
            details={
                "message": "Internal processing error",
                "error_id": str(uuid.uuid4())
            }
        )
    
    else:
        return JSONResponse({"available_errors": [
            "bad_request", "unauthorized", "forbidden", "not_found",
            "validation", "rate_limit", "server_error"
        ]})
```

### Structured Validation Errors

```python
from pydantic import BaseModel, ValidationError
from typing import List

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str
    age: int
    terms_accepted: bool

@app.post("/register")
async def register_user(request: Request):
    try:
        # Parse request body
        raw_data = await request.json()
        user_data = UserRegistration(**raw_data)
        
        # Additional business validation
        if await username_exists(user_data.username):
            raise ValidationException(
                details={
                    "message": "Username already exists",
                    "field": "username",
                    "code": "DUPLICATE_USERNAME"
                }
            )
        
        # Process registration
        user = await create_user(user_data)
        return JSONResponse({"user": user, "status": "created"})
        
    except ValidationError as e:
        # Format Pydantic validation errors
        formatted_errors = []
        for error in e.errors():
            formatted_errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        raise ValidationException(
            details={
                "message": "Registration data validation failed",
                "errors": formatted_errors
            }
        )
```

## Error Logging and Monitoring

### Comprehensive Error Logging

```python
import logging
import json
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class ErrorLogger:
    """Centralized error logging"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_error(self, error: Exception, request_info: dict = None, user_id: str = None):
        """Log error with context"""
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "user_id": user_id,
            "request_info": request_info or {}
        }
        
        if isinstance(error, HTTPException):
            error_data.update({
                "status_code": error.status_code,
                "error_code": error.error.code if error.error else None,
                "error_details": error.details
            })
        
        # Log at appropriate level
        if isinstance(error, HTTPException) and error.status_code < 500:
            self.logger.warning(f"Client error: {json.dumps(error_data)}")
        else:
            self.logger.error(f"Server error: {json.dumps(error_data)}", exc_info=True)

error_logger = ErrorLogger()

class LoggingErrorMiddleware(BaseHTTPMiddleware):
    """Error middleware with comprehensive logging"""
    
    async def process_http_request(self, scope: Scope, protocol: Protocol):
        request_info = {
            "method": scope.method,
            "path": scope.path,
            "client_ip": scope.client,
            "user_agent": scope.headers.get("user-agent"),
            "request_id": scope.get("request_id")
        }
        
        try:
            await self.app(scope, protocol)
            
        except Exception as e:
            # Extract user ID if available
            user_id = scope.get("user_id")
            
            # Log the error
            error_logger.log_error(e, request_info, user_id)
            
            # Re-raise for further handling
            raise
```

### Error Metrics and Alerting

```python
from collections import defaultdict
import time

class ErrorMetrics:
    """Track error metrics for monitoring"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_rates = defaultdict(list)
        self.last_reset = time.time()
    
    def record_error(self, error_type: str, status_code: int):
        """Record an error occurrence"""
        current_time = time.time()
        
        # Reset counters every hour
        if current_time - self.last_reset > 3600:
            self.error_counts.clear()
            self.error_rates.clear()
            self.last_reset = current_time
        
        # Record error
        self.error_counts[f"{status_code}_{error_type}"] += 1
        self.error_rates[error_type].append(current_time)
        
        # Alert on high error rates
        if self._should_alert(error_type):
            self._send_alert(error_type, status_code)
    
    def _should_alert(self, error_type: str) -> bool:
        """Check if error rate warrants an alert"""
        recent_errors = [
            timestamp for timestamp in self.error_rates[error_type]
            if time.time() - timestamp < 300  # Last 5 minutes
        ]
        return len(recent_errors) > 10  # More than 10 errors in 5 minutes
    
    def _send_alert(self, error_type: str, status_code: int):
        """Send alert (implement with your alerting system)"""
        print(f"ALERT: High error rate for {error_type} (HTTP {status_code})")

error_metrics = ErrorMetrics()

@app.get("/metrics/errors")
async def get_error_metrics():
    """Endpoint to retrieve error metrics"""
    return JSONResponse({
        "error_counts": dict(error_metrics.error_counts),
        "total_errors": sum(error_metrics.error_counts.values()),
        "last_reset": error_metrics.last_reset
    })
```

## Testing Error Handling

### Unit Testing Exceptions

```python
import pytest
from velithon.testing import TestClient

def test_http_exceptions():
    client = TestClient(app)
    
    # Test 400 Bad Request
    response = client.get("/demo/errors/bad_request")
    assert response.status_code == 400
    assert "Invalid request parameters" in response.json()["error"]["message"]
    
    # Test 404 Not Found
    response = client.get("/demo/errors/not_found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    
    # Test 500 Internal Server Error
    response = client.get("/demo/errors/server_error")
    assert response.status_code == 500

def test_validation_errors():
    client = TestClient(app)
    
    # Test invalid registration data
    invalid_data = {
        "username": "",
        "email": "invalid-email",
        "password": "123",
        "age": -5
    }
    
    response = client.post("/register", json=invalid_data)
    assert response.status_code == 422
    
    errors = response.json()["error"]["details"]["errors"]
    assert len(errors) > 0
    assert any(error["field"] == "email" for error in errors)
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_error_middleware():
    """Test that error middleware properly handles exceptions"""
    
    async with TestClient(app) as client:
        # Test that unhandled exceptions are caught
        response = await client.get("/endpoint-that-raises-exception")
        assert response.status_code == 500
        
        # Test error response format
        error_data = response.json()
        assert "error" in error_data
        assert "code" in error_data["error"]
        assert "message" in error_data["error"]
```

## Production Best Practices

### Security Considerations

```python
class SecureErrorFormatter(ResponseFormatter):
    """Production error formatter that prevents information leakage"""
    
    def format_error(self, exception: HTTPException) -> dict:
        # Safe error codes that can expose details
        safe_codes = {400, 401, 403, 404, 422, 429}
        
        if exception.status_code in safe_codes:
            return {
                "error": {
                    "code": exception.error.code if exception.error else "CLIENT_ERROR",
                    "message": exception.error.message if exception.error else "Request error"
                }
            }
        else:
            # Generic message for server errors - don't leak internals
            return {
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An error occurred processing your request"
                }
            }

# Use secure formatter in production
if os.getenv("ENV") == "production":
    HTTPException.set_formatter(SecureErrorFormatter())
```

### Configuration Management

```python
from dataclasses import dataclass

@dataclass
class ErrorConfig:
    debug_mode: bool = False
    log_level: str = "INFO"
    include_traceback: bool = False
    alert_threshold: int = 10
    enable_metrics: bool = True

def create_error_config() -> ErrorConfig:
    """Create error configuration based on environment"""
    env = os.getenv("ENV", "development")
    
    if env == "production":
        return ErrorConfig(
            debug_mode=False,
            log_level="WARNING",
            include_traceback=False,
            alert_threshold=5,
            enable_metrics=True
        )
    else:
        return ErrorConfig(
            debug_mode=True,
            log_level="DEBUG",
            include_traceback=True,
            alert_threshold=50,
            enable_metrics=True
        )

# Initialize with environment-specific config
error_config = create_error_config()
```

Velithon's error handling system provides a robust, secure, and flexible foundation for managing errors in production applications. The combination of structured exceptions, custom formatters, and middleware-based processing ensures that errors are handled consistently and safely across your entire application.
