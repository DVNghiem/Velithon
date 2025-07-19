#!/usr/bin/env python3
"""
Comprehensive test suite for authentication dependency handling in Velithon.
Tests all input parsing scenarios similar to FastAPI's approach.
"""

import asyncio
import inspect
from typing import Annotated, Optional

from pydantic import BaseModel

from velithon.application import Velithon
from velithon.di import Provide
from velithon.openapi.docs import swagger_generate
from velithon.params import Body, Header, Query
from velithon.requests import Request


# Test Models
class User(BaseModel):
    id: int
    username: str
    email: str


class QueryData(BaseModel):
    search: str
    limit: int = 10
    offset: int = 0


class JsonPayload(BaseModel):
    name: str
    age: int
    active: bool = True


# Authentication Dependencies
async def get_current_user() -> User:
    """Mock authentication dependency"""
    return User(id=1, username='testuser', email='test@example.com')


async def get_admin_user() -> User:
    """Mock admin authentication dependency"""
    return User(id=2, username='admin', email='admin@example.com')


def get_api_key(request: Request) -> str:
    """Mock API key authentication"""
    return request.headers.get('X-API-Key', 'default-key')


# Test Application
app = Velithon()


# Test Endpoints
@app.get('/test-query-auth')
async def query_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    data: Annotated[QueryData, Query()],
    extra: str = 'default',
):
    """Test query parameters with authentication"""
    return {'user': current_user.dict(), 'data': data.dict(), 'extra': extra}


@app.get('/test-path-auth/{item_id}/{name}')
async def path_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)], item_id: int, name: str
):
    """Test path parameters with authentication"""
    return {'user': current_user.dict(), 'item_id': item_id, 'name': name}


@app.post('/test-json-auth')
async def json_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    payload: Annotated[JsonPayload, Body()],
    query_param: str = 'query_default',
):
    """Test JSON body with authentication"""
    return {
        'user': current_user.dict(),
        'payload': payload.dict(),
        'query_param': query_param,
    }


@app.get('/test-header-auth')
async def header_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    api_key: Annotated[str, Provide(get_api_key)],
    custom_header: Annotated[str, Header(alias='X-Custom-Header')],
    optional_header: Annotated[
        Optional[str], Header(alias='X-Optional-Header', default=None)
    ],
):
    """Test header parameters with authentication"""
    return {
        'user': current_user.dict(),
        'api_key': api_key,
        'custom_header': custom_header,
        'optional_header': optional_header,
    }


@app.get('/test-multi-auth')
async def multiple_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    admin: Annotated[User, Provide(get_admin_user)],
    query_data: Annotated[QueryData, Query()],
    api_key: Annotated[str, Provide(get_api_key)],
):
    """Test multiple authentication dependencies"""
    return {
        'user': current_user.dict(),
        'admin': admin.dict(),
        'query_data': query_data.dict(),
        'api_key': api_key,
    }


@app.post('/test-complex-mixed/{user_id}')
async def complex_mixed_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    admin: Annotated[User, Provide(get_admin_user)],
    query_data: Annotated[QueryData, Query()],
    json_payload: Annotated[JsonPayload, Body()],
    user_id: int,
    auth_header: Annotated[str, Header(alias='X-Auth-Token')],
    optional_header: Annotated[Optional[str], Header(alias='X-Optional', default=None)],
):
    """Test complex mixed parameters with multiple auth dependencies"""
    return {
        'user': current_user.dict(),
        'admin': admin.dict(),
        'user_id': user_id,
        'query_data': query_data.dict(),
        'json_payload': json_payload.dict(),
        'auth_header': auth_header,
        'optional_header': optional_header,
    }


@app.get('/test-no-auth')
async def no_auth_endpoint(
    query_data: Annotated[QueryData, Query()], extra: str = 'no_auth'
):
    """Test endpoint without authentication"""
    return {'query_data': query_data.dict(), 'extra': extra}


@app.get('/test-only-auth')
async def only_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    api_key: Annotated[str, Provide(get_api_key)],
):
    """Test endpoint with only authentication dependencies"""
    return {'user': current_user.dict(), 'api_key': api_key}


def test_openapi_generation():
    """Test OpenAPI generation for all endpoints"""
    print('Testing OpenAPI generation...')

    test_cases = [
        (
            query_with_auth_endpoint,
            'GET',
            '/test-query-auth',
            ['search', 'limit', 'offset', 'extra'],
        ),
        (
            path_with_auth_endpoint,
            'GET',
            '/test-path-auth/{item_id}/{name}',
            ['item_id', 'name'],
        ),
        (json_with_auth_endpoint, 'POST', '/test-json-auth', ['query_param']),
        (
            header_with_auth_endpoint,
            'GET',
            '/test-header-auth',
            ['custom_header', 'optional_header'],
        ),
        (
            multiple_auth_endpoint,
            'GET',
            '/test-multi-auth',
            ['search', 'limit', 'offset'],
        ),
        (
            complex_mixed_endpoint,
            'POST',
            '/test-complex-mixed/{user_id}',
            ['user_id', 'search', 'limit', 'offset', 'X-Auth-Token', 'X-Optional'],
        ),
        (
            no_auth_endpoint,
            'GET',
            '/test-no-auth',
            ['search', 'limit', 'offset', 'extra'],
        ),
        (only_auth_endpoint, 'GET', '/test-only-auth', []),
    ]

    for func, method, path, expected_params in test_cases:
        endpoint_spec, components = swagger_generate(func, method, path)

        # Extract parameters from the correct path
        path_key = next(iter(endpoint_spec.keys()))
        method_key = method.lower()
        param_names = [
            p['name'] for p in endpoint_spec[path_key][method_key].get('parameters', [])
        ]

        # Check that expected business parameters are present
        for param in expected_params:
            if param not in param_names:
                print(f"❌ Missing parameter '{param}' in {func.__name__}")
                return False

        # Check that auth dependencies are NOT present
        auth_params = ['user', 'admin', 'api_key']
        for auth_param in auth_params:
            if auth_param in param_names:
                print(f"❌ Auth parameter '{auth_param}' found in {func.__name__}")
                return False

        print(f'✅ {func.__name__} - Parameters: {param_names}')

    print('✅ All OpenAPI generation tests passed!')
    return True


async def test_runtime_parameter_resolution():
    """Test runtime parameter resolution"""
    print('Testing runtime parameter resolution...')

    # Import here to avoid circular imports
    from velithon.params.parser import _is_auth_dependency

    # Mock request
    class MockRequest:
        def __init__(self):
            self.scope = {'method': 'GET', 'path': '/test'}
            self.path_params = {}
            self.query_params = {'search': 'test', 'limit': '20'}
            self.headers = {}

        async def json(self):
            return {'name': 'test', 'age': 25}

    MockRequest()

    # Test authentication dependency detection
    sig = inspect.signature(query_with_auth_endpoint)
    auth_params = []
    business_params = []

    for param_name, param in sig.parameters.items():
        if _is_auth_dependency(param.annotation):
            auth_params.append(param_name)
        else:
            business_params.append(param_name)

    # Verify auth detection
    if 'user' not in auth_params:
        print("❌ Failed to detect 'user' as auth dependency")
        return False

    if 'data' not in business_params:
        print("❌ Failed to detect 'data' as business parameter")
        return False

    print(f'✅ Auth parameters: {auth_params}')
    print(f'✅ Business parameters: {business_params}')
    print('✅ Runtime parameter resolution test passed!')
    return True


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print('🚀 Running comprehensive authentication parsing tests...')

    try:
        # Test OpenAPI generation
        if not test_openapi_generation():
            return False

        # Test runtime parameter resolution
        if not asyncio.run(test_runtime_parameter_resolution()):
            return False

        print('🎉 All comprehensive tests passed!')
        return True

    except Exception as e:
        print(f'❌ Comprehensive tests failed: {e}')
        import traceback

        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_comprehensive_tests()
    exit(0 if success else 1)
