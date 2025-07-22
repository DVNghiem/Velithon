#!/usr/bin/env python3
"""Real-world example of custom request ID generation in Velithon.

This example demonstrates:
1. Multiple request ID generation strategies
2. Header-based correlation IDs
3. Context management
4. Middleware integration
5. Production-ready error handling
"""

import re
import time
import uuid

from velithon import Velithon
from velithon.ctx import current_app, g, has_request_context, request
from velithon.middleware import Middleware
from velithon.middleware.base import BaseHTTPMiddleware
from velithon.requests import Request
from velithon.responses import JSONResponse

# Compile regex patterns once for performance
UUID_PATTERN = re.compile(
    r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
)
CORRELATION_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')


def production_request_id_generator(req):
    """Production-ready request ID generator with multiple strategies.

    Priority order:
    1. X-Trace-ID header (distributed tracing)
    2. X-Correlation-ID header (client correlation)
    3. Generate UUID for API endpoints
    4. Custom format for other endpoints
    """
    try:
        # Strategy 1: Use distributed tracing ID
        trace_id = req.headers.get('x-trace-id')
        if trace_id and UUID_PATTERN.match(trace_id):
            return f'trace-{trace_id}'

        # Strategy 2: Use client correlation ID
        correlation_id = req.headers.get('x-correlation-id')
        if (
            correlation_id
            and CORRELATION_PATTERN.match(correlation_id)
            and len(correlation_id) <= 64
        ):
            return f'corr-{correlation_id}'

        # Strategy 3: Generate UUID for API endpoints
        if req.path.startswith('/api/'):
            return f'api-{str(uuid.uuid4())[:8]}'

        # Strategy 4: Custom format for other endpoints
        timestamp = int(time.time() * 1000) % 1000000  # Last 6 digits
        path_hash = abs(hash(req.path)) % 10000
        client_hash = abs(hash(req.client)) % 1000 if hasattr(req, 'client') else 0
        return f'req-{timestamp}-{path_hash}-{client_hash}'

    except Exception:
        # Ultimate fallback: simple timestamp-based ID
        return f'fallback-{int(time.time() * 1000)}'


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to demonstrate context usage and request logging."""

    async def process_http_request(self, scope, protocol):
        """Log request start and end with custom request ID."""
        start_time = time.time()
        request_id = scope._request_id
        method = scope.method
        path = scope.path

        print(f'🚀 [{request_id}] Starting {method} {path}')

        try:
            # Process the request
            await self.app(scope, protocol)

            duration = (time.time() - start_time) * 1000
            print(f'✅ [{request_id}] Completed {method} {path} in {duration:.2f}ms')

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            print(
                f'❌ [{request_id}] Failed {method} {path} after {duration:.2f}ms: {e}'
            )
            raise


# Create application with custom request ID generator
app = Velithon(
    title='Production API with Custom Request IDs',
    description='Demonstrates custom request ID generation and context management',
    version='1.0.0',
    request_id_generator=production_request_id_generator,
    middleware=[Middleware(RequestLoggingMiddleware)],
)


@app.get('/')
async def root():
    """Root endpoint with basic request info."""
    return JSONResponse(
        {
            'message': 'Welcome to Custom Request ID Demo!',
            'request_id': request.request_id if has_request_context() else 'no-context',
            'timestamp': time.time(),
        }
    )


@app.get('/api/users/{user_id}')
async def get_user(req: Request):
    """API endpoint that will get UUID-based request ID."""
    user_id = req.path_params['user_id']

    # Store some data in request context
    if has_request_context():
        g.user_id = user_id
        g.request_start = time.time()

    return JSONResponse(
        {
            'request_id': req.request_id,
            'user_id': user_id,
            'method': req.method,
            'path': req.url.path,
            'headers': {
                'trace-id': req.headers.get('x-trace-id'),
                'correlation-id': req.headers.get('x-correlation-id'),
            },
        }
    )


@app.post('/api/users')
async def create_user(req: Request):
    """Create user endpoint with request body."""
    try:
        body = await req.json()
        user_name = body.get('name', 'Unknown')

        # Simulate some processing time
        time.sleep(0.1)

        # Use request context
        if has_request_context():
            g.created_user = user_name
            g.processing_time = 0.1

        return JSONResponse(
            {
                'request_id': req.request_id,
                'message': f'User {user_name} created successfully',
                'user': body,
                'processing_info': {
                    'request_path': req.url.path,
                    'content_type': req.headers.get('content-type'),
                    'request_size': len(await req.body())
                    if hasattr(req, 'body')
                    else 0,
                },
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                'request_id': req.request_id,
                'error': str(e),
                'message': 'Failed to create user',
            },
            status_code=400,
        )


@app.get('/health')
async def health_check(req: Request):
    """Health check endpoint that shows different request ID for non-API paths."""
    return JSONResponse(
        {
            'status': 'healthy',
            'request_id': req.request_id,
            'timestamp': time.time(),
            'app_info': {
                'title': current_app.title if has_request_context() else 'Unknown',
                'version': current_app.version if has_request_context() else 'Unknown',
            },
        }
    )


@app.get('/demo/trace')
async def demo_trace_id(req: Request):
    """Demo endpoint to show trace ID handling."""
    trace_id = req.headers.get('x-trace-id')
    correlation_id = req.headers.get('x-correlation-id')

    return JSONResponse(
        {
            'request_id': req.request_id,
            'demonstrates': 'Trace ID and Correlation ID handling',
            'trace_id': trace_id,
            'correlation_id': correlation_id,
            'request_id_type': {
                'trace': req.request_id.startswith('trace-') if trace_id else False,
                'correlation': req.request_id.startswith('corr-')
                if correlation_id and not trace_id
                else False,
                'custom': not (trace_id or correlation_id),
            },
            'instructions': {
                'trace_id': 'Send X-Trace-ID header with UUID format',
                'correlation_id': 'Send X-Correlation-ID header with alphanumeric value',
                'custom': 'Send neither header to get custom generated ID',
            },
        }
    )


def demonstrate_request_id_generation():
    """Demonstrate different request ID generation scenarios."""
    print('=' * 80)
    print('VELITHON CUSTOM REQUEST ID GENERATION DEMO')
    print('=' * 80)

    # Test the generator function directly
    from unittest.mock import Mock

    from velithon.datastructures import _TempRequestContext

    print('\n🧪 Testing Request ID Generation Strategies:\n')

    # Test 1: Trace ID
    mock_scope = Mock()
    mock_scope.headers = [('x-trace-id', 'f47ac10b-58cc-4372-a567-0e02b2c3d479')]
    mock_scope.method = 'GET'
    mock_scope.path = '/api/test'
    mock_scope.client = '192.168.1.100'

    temp_request = _TempRequestContext(mock_scope)
    request_id = production_request_id_generator(temp_request)
    print(f'1. With Trace ID: {request_id}')

    # Test 2: Correlation ID
    mock_scope.headers = [('x-correlation-id', 'user-session-12345')]
    temp_request = _TempRequestContext(mock_scope)
    request_id = production_request_id_generator(temp_request)
    print(f'2. With Correlation ID: {request_id}')

    # Test 3: API endpoint (no special headers)
    mock_scope.headers = []
    mock_scope.path = '/api/users/123'
    temp_request = _TempRequestContext(mock_scope)
    request_id = production_request_id_generator(temp_request)
    print(f'3. API endpoint: {request_id}')

    # Test 4: Regular endpoint
    mock_scope.path = '/health'
    temp_request = _TempRequestContext(mock_scope)
    request_id = production_request_id_generator(temp_request)
    print(f'4. Regular endpoint: {request_id}')

    print('\n🌟 To test with real HTTP requests, run:')
    print('velithon run --app real_world_example:app --reload')
    print('\nThen try these curl commands:')
    print('curl http://localhost:8000/')
    print('curl http://localhost:8000/api/users/123')
    print(
        "curl -H 'X-Trace-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479' http://localhost:8000/demo/trace"
    )
    print("curl -H 'X-Correlation-ID: my-session-id' http://localhost:8000/demo/trace")
    print(
        'curl -X POST -H \'Content-Type: application/json\' -d \'{"name":"John"}\' http://localhost:8000/api/users'
    )

    print('\n' + '=' * 80)


if __name__ == '__main__':
    demonstrate_request_id_generation()
