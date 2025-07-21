# Request Singleton Pattern Documentation

## Overview

The Velithon framework now implements a Request singleton pattern to ensure memory efficiency and consistency throughout the request lifecycle. This pattern prevents the creation of multiple Request instances for the same HTTP request, reducing memory usage and ensuring data consistency.

## How it Works

### Context-Based Singleton

The Request singleton pattern is implemented using Velithon's context management system:

1. **RequestContext Creation**: When a new HTTP request arrives, a `RequestContext` is created using the `create_with_singleton_request()` class method, which creates exactly one Request instance.

2. **Request Retrieval**: Throughout the request lifecycle, components can retrieve the singleton Request instance using `get_or_create_request()`.

3. **Context Cleanup**: When the request context exits, the singleton Request instance is properly cleaned up.

### Key Functions

#### `get_or_create_request(scope, protocol)`
```python
from velithon.ctx import get_or_create_request

# Try to get existing request from context first (singleton pattern)
request = get_or_create_request(scope, protocol)
```

This function:
- Returns the existing Request instance if called within a request context (singleton behavior)
- Creates a new Request instance if no request context exists

#### `RequestContext.create_with_singleton_request(app, scope, protocol)`
```python
from velithon.ctx import RequestContext

# Create a request context with a singleton Request object
context = RequestContext.create_with_singleton_request(app, scope, protocol)
async with context:
    # All calls to get_or_create_request() will return the same instance
    pass
```

## Benefits

### Memory Efficiency
- **Reduced Memory Usage**: Only one Request object is created per HTTP request
- **Garbage Collection**: Fewer objects to track and clean up
- **Performance**: Reduced object creation overhead

### Consistency
- **Data Integrity**: All components work with the same Request instance
- **State Management**: Changes to request data are immediately visible across all components
- **Thread Safety**: Context isolation ensures proper request separation

## Updated Components

The following framework components have been updated to use the singleton pattern:

### Core Routing
- `request_response()` function in `velithon/routing.py`
- `HTTPEndpoint.dispatch()` method in `velithon/endpoint.py`

### Middleware
- `ProxyMiddleware` in `velithon/middleware/proxy.py`
- `RequestContextMiddleware` in `velithon/middleware/context.py`

### Gateway
- `GatewayRoute.handle()` method in `velithon/gateway.py`

## Usage Examples

### Basic Usage
```python
from velithon import Velithon
from velithon.ctx import get_or_create_request, RequestContext

app = Velithon()

async def my_handler(scope, protocol):
    # Create request context with singleton
    context = RequestContext.create_with_singleton_request(app, scope, protocol)
    async with context:
        # Get the singleton request instance
        request = get_or_create_request(scope, protocol)
        
        # All subsequent calls return the same instance
        same_request = get_or_create_request(scope, protocol)
        assert request is same_request  # True!
```

### In Middleware
```python
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.ctx import get_or_create_request, has_request_context

class MyMiddleware(BaseHTTPMiddleware):
    async def process_http_request(self, scope, protocol):
        # Use singleton pattern - try to get from context first
        if has_request_context():
            request = get_or_create_request(scope, protocol)
        else:
            # Create new request if no context exists
            from velithon.requests import Request
            request = Request(scope, protocol)
        
        # Process request...
        await self.app(scope, protocol)
```

## Best Practices

1. **Use Context Functions**: Always prefer `get_or_create_request()` over direct `Request()` instantiation
2. **Check Context**: Use `has_request_context()` to determine if you're within a request context
3. **Proper Cleanup**: Let the context manager handle Request cleanup automatically
4. **Thread Safety**: Each request gets its own context, ensuring thread safety

## Backward Compatibility

The singleton pattern is fully backward compatible:
- Existing code that creates `Request(scope, protocol)` directly continues to work
- The new pattern is opt-in and used internally by the framework
- No breaking changes to the public API

## Performance Impact

- **Memory Usage**: Reduced by eliminating duplicate Request objects
- **CPU Usage**: Slight reduction from fewer object allocations
- **Response Time**: Minimal improvement from reduced garbage collection pressure
- **Thread Safety**: No impact on concurrency performance
