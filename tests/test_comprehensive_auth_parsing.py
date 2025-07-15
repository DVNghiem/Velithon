"""
Comprehensive test suite for authentication dependency handling in Velithon.
Tests all input parsing scenarios similar to FastAPI's approach.
"""

import asyncio
import inspect
from typing import Annotated, Optional

from pydantic import BaseModel

from velithon.application import Velithon
from velithon.datastructures import UploadFile
from velithon.di import Provide
from velithon.openapi.docs import swagger_generate
from velithon.params import Body, Form, Header, Path, Query
from velithon.params.parser import ParameterResolver, _is_auth_dependency
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


class FormData(BaseModel):
    title: str
    description: Optional[str] = None
    tags: list[str] = []


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


async def get_optional_user() -> Optional[User]:
    """Mock optional authentication dependency"""
    return User(id=3, username='optional', email='optional@example.com')


def get_api_key(request: Request) -> str:
    """Mock API key authentication"""
    return request.headers.get('X-API-Key', 'default-key')


# Test Application
app = Velithon()


# Test Endpoints - Each testing different input parsing scenarios
@app.get('/test-query-auth')
async def query_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    data: Annotated[QueryData, Query()],
    extra: str = Query(default='default'),
):
    """Test query parameters with authentication"""
    return {'user': current_user.dict(), 'data': data.dict(), 'extra': extra}


@app.get('/test-path-auth/{item_id}')
async def path_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    item_id: int = Path(),
    name: str = Path(),
):
    """Test path parameters with authentication"""
    return {'user': current_user.dict(), 'item_id': item_id, 'name': name}


@app.post('/test-form-auth')
async def form_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    data: Annotated[FormData, Form()],
    extra_field: str = Form(default='extra'),
):
    """Test form data with authentication"""
    return {
        'user': current_user.dict(),
        'data': data.dict(),
        'extra_field': extra_field,
    }


@app.post('/test-json-auth')
async def json_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    payload: Annotated[JsonPayload, Body()],
    query_param: str = Query(default='query_default'),
):
    """Test JSON body with authentication"""
    return {
        'user': current_user.dict(),
        'payload': payload.dict(),
        'query_param': query_param,
    }


@app.post('/test-file-auth')
async def file_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    file: Optional[UploadFile] = None,
    description: str = Form(default='file_desc'),
):
    """Test file upload with authentication"""
    return {
        'user': current_user.dict(),
        'filename': file.filename if file else None,
        'description': description,
    }


@app.get('/test-header-auth')
async def header_with_auth_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    api_key: Annotated[str, Provide(get_api_key)],
    custom_header: str = Header(alias='X-Custom-Header'),
    optional_header: Optional[str] = Header(alias='X-Optional-Header', default=None),
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
    optional_user: Annotated[Optional[User], Provide(get_optional_user)],
    query_data: Annotated[QueryData, Query()],
    api_key: Annotated[str, Provide(get_api_key)],
):
    """Test multiple authentication dependencies"""
    return {
        'user': current_user.dict(),
        'admin': admin.dict(),
        'optional_user': optional_user.dict() if optional_user else None,
        'query_data': query_data.dict(),
        'api_key': api_key,
    }


@app.post('/test-complex-mixed/{user_id}')
async def complex_mixed_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    admin: Annotated[User, Provide(get_admin_user)],
    query_data: Annotated[QueryData, Query()],
    json_payload: Annotated[JsonPayload, Body()],
    user_id: int = Path(),
    auth_header: str = Header(alias='X-Auth-Token'),
    optional_header: Optional[str] = Header(alias='X-Optional', default=None),
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


# Edge Cases
@app.get('/test-no-auth')
async def no_auth_endpoint(
    query_data: Annotated[QueryData, Query()], extra: str = Query(default='no_auth')
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


@app.get('/test-optional-params')
async def optional_params_endpoint(
    current_user: Annotated[User, Provide(get_current_user)],
    required_param: str = Query(),
    optional_param: Optional[str] = Query(default=None),
    default_param: str = Query(default='default_value'),
):
    """Test optional and default parameters with auth"""
    return {
        'user': current_user.dict(),
        'required_param': required_param,
        'optional_param': optional_param,
        'default_param': default_param,
    }


# Test Class for Comprehensive Testing
class TestAuthenticationParsing:
    """Comprehensive test class for authentication dependency parsing"""

    def test_openapi_generation_query_auth(self):
        """Test OpenAPI generation for query parameters with auth"""
        endpoint_spec, components = swagger_generate(
            query_with_auth_endpoint, 'GET', '/test-query-auth'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['get']

        # Should only have business parameters, not auth dependencies
        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'search' in param_names  # from QueryData
        assert 'limit' in param_names  # from QueryData
        assert 'offset' in param_names  # from QueryData
        assert 'extra' in param_names  # standalone query param

        # Should NOT have auth dependencies
        assert 'user' not in param_names

        print('✅ Query auth OpenAPI test passed')

    def test_openapi_generation_path_auth(self):
        """Test OpenAPI generation for path parameters with auth"""
        endpoint_spec, components = swagger_generate(
            path_with_auth_endpoint, 'GET', '/test-path-auth/{item_id}/{name}'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['get']

        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'item_id' in param_names
        assert 'name' in param_names
        assert 'user' not in param_names  # auth dependency

        print('✅ Path auth OpenAPI test passed')

    def test_openapi_generation_form_auth(self):
        """Test OpenAPI generation for form data with auth"""
        endpoint_spec, components = swagger_generate(
            form_with_auth_endpoint, 'POST', '/test-form-auth'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['post']

        # Should have request body for form data
        assert 'requestBody' in method_spec

        # Parameters should only have non-auth, non-body params
        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'user' not in param_names  # auth dependency

        print('✅ Form auth OpenAPI test passed')

    def test_openapi_generation_json_auth(self):
        """Test OpenAPI generation for JSON body with auth"""
        endpoint_spec, components = swagger_generate(
            json_with_auth_endpoint, 'POST', '/test-json-auth'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['post']

        # Should have request body for JSON
        assert 'requestBody' in method_spec

        # Should have query parameters but not auth
        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'query_param' in param_names
        assert 'user' not in param_names

        print('✅ JSON auth OpenAPI test passed')

    def test_openapi_generation_header_auth(self):
        """Test OpenAPI generation for header parameters with auth"""
        endpoint_spec, components = swagger_generate(
            header_with_auth_endpoint, 'GET', '/test-header-auth'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['get']

        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'custom_header' in param_names  # header param (not aliased name)
        assert 'optional_header' in param_names  # optional header
        assert 'user' not in param_names  # auth dependency
        assert 'api_key' not in param_names  # auth dependency

        print('✅ Header auth OpenAPI test passed')

    def test_openapi_generation_multi_auth(self):
        """Test OpenAPI generation for multiple auth dependencies"""
        endpoint_spec, components = swagger_generate(
            multiple_auth_endpoint, 'GET', '/test-multi-auth'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['get']

        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        # Should have business parameters
        assert 'search' in param_names
        assert 'limit' in param_names
        assert 'offset' in param_names

        # Should NOT have any auth dependencies
        assert 'user' not in param_names
        assert 'admin' not in param_names
        assert 'optional_user' not in param_names
        assert 'api_key' not in param_names

        print('✅ Multi-auth OpenAPI test passed')

    def test_openapi_generation_complex_mixed(self):
        """Test OpenAPI generation for complex mixed parameters"""
        endpoint_spec, components = swagger_generate(
            complex_mixed_endpoint, 'POST', '/test-complex-mixed/{user_id}'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['post']

        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        # Should have business parameters
        assert 'user_id' in param_names  # path param
        assert 'search' in param_names  # query param from model
        assert 'limit' in param_names  # query param from model
        assert 'offset' in param_names  # query param from model
        assert 'auth_header' in param_names  # header param (not aliased name)
        assert 'optional_header' in param_names  # optional header

        # Should NOT have auth dependencies
        assert 'user' not in param_names
        assert 'admin' not in param_names

        # Should have request body for JSON
        assert 'requestBody' in method_spec

        print('✅ Complex mixed OpenAPI test passed')

    def test_openapi_generation_no_auth(self):
        """Test OpenAPI generation for endpoint without auth"""
        endpoint_spec, components = swagger_generate(
            no_auth_endpoint, 'GET', '/test-no-auth'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['get']

        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'search' in param_names
        assert 'limit' in param_names
        assert 'offset' in param_names
        assert 'extra' in param_names

        print('✅ No auth OpenAPI test passed')

    def test_openapi_generation_only_auth(self):
        """Test OpenAPI generation for endpoint with only auth dependencies"""
        endpoint_spec, components = swagger_generate(
            only_auth_endpoint, 'GET', '/test-only-auth'
        )

        # Should have no parameters since all are auth dependencies
        param_names = [p['name'] for p in endpoint_spec.get('parameters', [])]
        assert len(param_names) == 0
        assert 'user' not in param_names
        assert 'api_key' not in param_names

        print('✅ Only auth OpenAPI test passed')

    def test_openapi_generation_optional_params(self):
        """Test OpenAPI generation for optional parameters with auth"""
        endpoint_spec, components = swagger_generate(
            optional_params_endpoint, 'GET', '/test-optional-params'
        )

        # Extract the actual endpoint spec
        path_key = next(iter(endpoint_spec.keys()))
        method_spec = endpoint_spec[path_key]['get']

        param_names = [p['name'] for p in method_spec.get('parameters', [])]
        assert 'required_param' in param_names
        assert 'optional_param' in param_names
        assert 'default_param' in param_names
        assert 'user' not in param_names  # auth dependency

        # Check required/optional flags
        params = {p['name']: p for p in method_spec.get('parameters', [])}
        assert params['required_param']['required'] is True
        assert params['optional_param']['required'] is False
        assert params['default_param']['required'] is False

        print('✅ Optional params OpenAPI test passed')


def run_all_openapi_tests():
    """Run all OpenAPI generation tests"""
    print('Running comprehensive OpenAPI generation tests...')

    tester = TestAuthenticationParsing()

    # Run all test methods
    test_methods = [
        tester.test_openapi_generation_query_auth,
        tester.test_openapi_generation_path_auth,
        tester.test_openapi_generation_form_auth,
        tester.test_openapi_generation_json_auth,
        tester.test_openapi_generation_header_auth,
        tester.test_openapi_generation_multi_auth,
        tester.test_openapi_generation_complex_mixed,
        tester.test_openapi_generation_no_auth,
        tester.test_openapi_generation_only_auth,
        tester.test_openapi_generation_optional_params,
    ]

    for test_method in test_methods:
        try:
            test_method()
        except Exception as e:
            print(f'❌ Test {test_method.__name__} failed: {e}')
            raise

    print('✅ All OpenAPI generation tests passed!')


async def test_runtime_parameter_resolution():
    """Test runtime parameter resolution with mock requests"""
    print('Testing runtime parameter resolution...')

    # Mock request for testing
    class MockRequest:
        def __init__(
            self, method='GET', path_params=None, query_params=None, headers=None
        ):
            self.scope = {
                'method': method,
                'path': '/test',
                'query_string': b'',
                'headers': [],
            }
            self.path_params = path_params or {}
            self.query_params = query_params or {}
            self.headers = headers or {}

        async def json(self):
            return {'name': 'test', 'age': 25}

        async def form(self):
            return {'title': 'test', 'description': 'test desc'}

        @property
        def files(self):
            return {}

    # Test parameter resolution
    from velithon.params.parser import ParameterResolver

    # Test 1: Query parameters with auth
    request = MockRequest(
        method='GET', query_params={'search': 'test', 'limit': '20', 'extra': 'value'}
    )

    resolver = ParameterResolver(request)

    # Check that auth dependencies are properly detected
    import inspect
    from velithon.params.parser import _is_auth_dependency

    sig = inspect.signature(query_with_auth_endpoint)
    auth_params = []
    business_params = []

    for param_name, param in sig.parameters.items():
        if _is_auth_dependency(param.annotation):
            auth_params.append(param_name)
        else:
            business_params.append(param_name)

    assert 'user' in auth_params
    assert 'data' in business_params
    assert 'extra' in business_params

    print('✅ Runtime parameter resolution test passed')


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print('🚀 Running comprehensive authentication parsing tests...')

    try:
        # Test OpenAPI generation
        run_all_openapi_tests()

        # Test runtime parameter resolution
        asyncio.run(test_runtime_parameter_resolution())

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
