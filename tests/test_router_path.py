"""
Test for Router path parameter functionality.
"""

from velithon import Velithon
from velithon.responses import JSONResponse
from velithon.routing import Route, Router


def test_router_with_path_parameter():
    """Test that Router with path parameter correctly prefixes routes."""

    def get_orders():
        return JSONResponse({'orders': []})

    def get_order(order_id: int):
        return JSONResponse({'order_id': order_id})

    # Create router with path prefix
    router = Router(path='/orders')
    router.add_api_route('/', get_orders, methods=['GET'])
    router.add_api_route('/{order_id}', get_order, methods=['GET'])

    # Check that routes have the correct paths
    assert len(router.routes) == 2
    assert router.routes[0].path == '/orders/'
    assert router.routes[1].path == '/orders/{order_id}'


def test_router_path_normalization():
    """Test that router path normalization works correctly."""

    router = Router(path='/api/v1')

    # Test _get_full_path method
    assert router._get_full_path('/users') == '/api/v1/users'
    assert router._get_full_path('users') == '/api/v1/users'
    assert router._get_full_path('/') == '/api/v1/'

    # Test with trailing slash in router path
    router2 = Router(path='/api/v1/')
    assert router2._get_full_path('/users') == '/api/v1/users'
    assert router2.path == '/api/v1'  # Should be normalized


def test_application_add_router():
    """Test that application can add routers correctly."""

    def get_orders():
        return JSONResponse({'orders': []})

    def get_users():
        return JSONResponse({'users': []})

    # Create routers
    order_router = Router(path='/orders')
    order_router.add_api_route('/', get_orders, methods=['GET'])

    user_router = Router()
    user_router.add_api_route('/', get_users, methods=['GET'])

    # Create application and add routers
    app = Velithon()
    app.add_router(order_router)
    app.include_router(user_router, prefix='/users')

    # Check that routes were added correctly
    routes = app.router.routes
    print(f'Total routes: {len(routes)}')
    for i, route in enumerate(routes):
        print(f'Route {i}: {route.path}')

    order_routes = [r for r in routes if r.path.startswith('/orders')]
    user_routes = [r for r in routes if r.path.startswith('/users')]

    print(f'Order routes: {len(order_routes)}')
    print(f'User routes: {len(user_routes)}')

    assert len(order_routes) == 1
    assert len(user_routes) == 1
    assert order_routes[0].path == '/orders/'
    assert user_routes[0].path == '/users/'


def test_router_with_no_path():
    """Test router without path parameter behaves normally."""

    def get_items():
        return JSONResponse({'items': []})

    router = Router()
    router.add_api_route('/items', get_items, methods=['GET'])

    assert len(router.routes) == 1
    assert router.routes[0].path == '/items'
    assert router.path == ''


def test_nested_router_paths():
    """Test nested router paths work correctly."""

    def handler():
        return JSONResponse({'status': 'ok'})

    # Create nested routers
    sub_router = Router(path='/sub')
    sub_router.add_api_route('/endpoint', handler, methods=['GET'])

    main_router = Router(path='/api')
    main_router.add_router(sub_router, prefix='/v1')

    # Check the final path
    routes = main_router.routes
    assert len(routes) == 1
    assert routes[0].path == '/api/v1/sub/endpoint'


def test_router_init_with_routes_and_path():
    """Test that Router __init__ applies path prefix to existing routes."""

    def get_profile():
        return JSONResponse({'message': 'profile'})

    def get_settings():
        return JSONResponse({'message': 'settings'})

    # Create routes manually
    profile_route = Route('/profile', get_profile, methods=['GET'])
    settings_route = Route('/settings', get_settings, methods=['GET'])

    # Create router with path prefix and existing routes
    router = Router(path='/user', routes=[profile_route, settings_route])

    # Check that path prefix was applied to existing routes
    assert len(router.routes) == 2
    assert router.routes[0].path == '/user/profile'
    assert router.routes[1].path == '/user/settings'

    # Check that the routes still have correct methods and endpoints
    assert router.routes[0].methods == {'GET', 'HEAD'}
    assert router.routes[1].methods == {'GET', 'HEAD'}
    assert router.routes[0].endpoint == get_profile
    assert router.routes[1].endpoint == get_settings


if __name__ == '__main__':
    # Run basic tests
    test_router_with_path_parameter()
    test_router_path_normalization()
    test_application_add_router()
    test_router_with_no_path()
    test_nested_router_paths()
    test_router_init_with_routes_and_path()
    print('All tests passed!')
