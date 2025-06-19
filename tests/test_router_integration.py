"""
Integration test for Router path parameter functionality.
Tests router matching logic directly.
"""

from velithon import Velithon
from velithon.responses import JSONResponse
from velithon.routing import Router


def test_router_path_integration():
    """Test that router path functionality works correctly."""

    # Create handlers
    def get_orders():
        return JSONResponse({'message': 'orders endpoint'})

    def get_users():
        return JSONResponse({'message': 'users endpoint'})

    def get_products():
        return JSONResponse({'message': 'products endpoint'})

    # Create routers
    orders_router = Router(path='/orders')
    orders_router.add_api_route('/', get_orders, methods=['GET'])

    users_router = Router()
    users_router.add_api_route('/', get_users, methods=['GET'])

    shop_router = Router(path='/shop')
    products_router = Router(path='/products')
    products_router.add_api_route('/', get_products, methods=['GET'])
    shop_router.add_router(products_router)

    # Create application
    app = Velithon()
    app.add_router(orders_router)
    app.include_router(users_router, prefix='/users')
    app.add_router(shop_router)

    print('🧪 Testing Router Path Integration')
    print('=' * 40)

    # Test that routes were created correctly
    all_routes = []
    for route in app.router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods or []:
                if method != 'HEAD':  # Skip HEAD for cleaner output
                    all_routes.append(f'{method} {route.path}')

    expected_routes = ['GET /orders/', 'GET /users/', 'GET /shop/products/']

    print('Expected routes:')
    for route in expected_routes:
        print(f'  {route}')

    print()
    print('Actual routes (filtered):')
    filtered_routes = [
        r
        for r in all_routes
        if any(exp in r for exp in ['/orders/', '/users/', '/shop/products/'])
    ]
    for route in filtered_routes:
        print(f'  {route}')

    print()
    print('Route verification:')
    for expected in expected_routes:
        if expected in all_routes:
            print(f'✅ {expected:<20} -> Found')
        else:
            print(f'❌ {expected:<20} -> Missing')

    # Test specific router functionality
    print()
    print('Router path parameter tests:')

    # Test 1: Router with path parameter
    test_router = Router(path='/test')
    if test_router.path == '/test':
        print('✅ Router path parameter -> Works')
    else:
        print(f"❌ Router path parameter -> Expected '/test', got '{test_router.path}'")

    # Test 2: Path normalization
    test_router2 = Router(path='/test/')
    if test_router2.path == '/test':
        print('✅ Path normalization -> Works')
    else:
        print(f"❌ Path normalization -> Expected '/test', got '{test_router2.path}'")

    # Test 3: Full path generation
    full_path = test_router._get_full_path('/endpoint')
    if full_path == '/test/endpoint':
        print('✅ Full path generation -> Works')
    else:
        print(
            f"❌ Full path generation -> Expected '/test/endpoint', got '{full_path}'"
        )

    print()
    print('✅ Integration test completed!')


if __name__ == '__main__':
    test_router_path_integration()
