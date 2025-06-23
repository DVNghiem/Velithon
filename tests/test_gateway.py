"""Tests for the Gateway functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from velithon import Gateway, Velithon, gateway_route
from velithon._velithon import Match
from velithon.gateway import GatewayRoute, forward_to
from velithon.requests import Request
from velithon.responses import JSONResponse, Response


class MockScope:
    """Mock scope object for testing."""

    def __init__(
        self, proto='http', method='GET', path='/', headers=None, query_string=''
    ):
        self.proto = proto
        self.method = method
        self.path = path
        self.query_string = query_string
        self.headers = headers or {}
        self._path_params = {}
        self._di_context = {}
        self._request_id = 'test-request-id'
        self._session = None


class TestGatewayRoute:
    """Test the GatewayRoute class functionality."""

    def test_gateway_route_creation_single_target(self):
        """Test creating a gateway route with a single target."""
        route = GatewayRoute(
            path='/api/v1/users/{user_id}',
            targets='http://user-service:8080',
            methods=['GET', 'POST'],
            timeout_ms=15000,
            max_retries=2,
        )

        assert route.path == '/api/v1/users/{user_id}'
        assert route.methods == ['GET', 'POST']
        assert route.timeout_ms == 15000
        assert route.max_retries == 2
        assert route.proxy_client is not None
        assert route.load_balancer is None

    def test_gateway_route_creation_multiple_targets(self):
        """Test creating a gateway route with multiple targets."""
        targets = [
            'http://service-1:8080',
            'http://service-2:8080',
            'http://service-3:8080',
        ]

        route = GatewayRoute(
            path='/api/v1/products/{path:path}',
            targets=targets,
            load_balancing_strategy='round_robin',
            health_check_path='/health',
        )

        assert route.path == '/api/v1/products/{path:path}'
        assert route.proxy_client is None
        assert route.load_balancer is not None

    def test_gateway_route_weighted_load_balancing(self):
        """Test creating a gateway route with weighted load balancing."""
        targets = ['http://legacy:8080', 'http://new:8080']
        weights = [70, 30]

        route = GatewayRoute(
            path='/api/orders/{path:path}',
            targets=targets,
            load_balancing_strategy='weighted',
            weights=weights,
        )

        assert route.load_balancer is not None

    @pytest.mark.asyncio
    async def test_gateway_route_matches_path(self):
        """Test that gateway route correctly matches paths."""
        route = GatewayRoute(
            path='/api/v1/users/{user_id}', targets='http://user-service:8080'
        )

        # Mock scope for HTTP request
        scope = MockScope(proto='http', method='GET', path='/api/v1/users/123')

        match, child_scope = route.matches(scope)

        # Should match and extract path parameters
        assert match == Match.FULL
        assert hasattr(child_scope, '_path_params')
        assert child_scope._path_params['user_id'] == '123'

    @pytest.mark.asyncio
    async def test_gateway_route_no_match_wrong_method(self):
        """Test that gateway route doesn't match wrong methods."""
        route = GatewayRoute(
            path='/api/v1/users/{user_id}',
            targets='http://user-service:8080',
            methods=['GET', 'POST'],
        )

        scope = MockScope(proto='http', method='DELETE', path='/api/v1/users/123')

        match, child_scope = route.matches(scope)

        assert match == Match.NONE  # Should not match

    @pytest.mark.asyncio
    async def test_gateway_route_no_match_wrong_path(self):
        """Test that gateway route doesn't match wrong paths."""
        route = GatewayRoute(
            path='/api/v1/users/{user_id}', targets='http://user-service:8080'
        )

        scope = MockScope(proto='http', method='GET', path='/api/v1/products/123')

        match, child_scope = route.matches(scope)

        assert match == Match.NONE

    def test_gateway_route_headers_configuration(self):
        """Test header manipulation configuration."""
        route = GatewayRoute(
            path='/api/v1/test',
            targets='http://test-service:8080',
            headers_to_add={'X-Gateway': 'Velithon', 'X-Service': 'test'},
            headers_to_remove=['X-Internal', 'X-Debug'],
            preserve_host=True,
        )

        assert route.headers_to_add == {'X-Gateway': 'Velithon', 'X-Service': 'test'}
        assert route.headers_to_remove == ['X-Internal', 'X-Debug']
        assert route.preserve_host is True


class TestGateway:
    """Test the Gateway class functionality."""

    def test_gateway_initialization(self):
        """Test Gateway class initialization."""
        gateway = Gateway()

        assert isinstance(gateway.routes, list)
        assert len(gateway.routes) == 0
        assert isinstance(gateway.load_balancers, dict)
        assert len(gateway.load_balancers) == 0

    def test_gateway_add_route(self):
        """Test adding routes to the gateway."""
        gateway = Gateway()

        route = gateway.add_route(
            path='/api/test', targets='http://test:8080', methods=['GET', 'POST']
        )

        assert len(gateway.routes) == 1
        assert gateway.routes[0] == route
        assert isinstance(route, GatewayRoute)

    def test_gateway_forward_to_decorator(self):
        """Test the forward_to decorator."""
        gateway = Gateway()

        @gateway.forward_to(
            targets='http://test:8080', path='/api/test', timeout_ms=10000
        )
        def test_service():
            """Test service endpoint."""
            pass

        assert len(gateway.routes) == 1
        route = gateway.routes[0]
        assert route.name == 'test_service'
        assert route.timeout_ms == 10000

    def test_gateway_get_routes(self):
        """Test getting routes from gateway."""
        gateway = Gateway()

        gateway.add_route('/api/test1', 'http://test1:8080')
        gateway.add_route('/api/test2', 'http://test2:8080')

        routes = gateway.get_routes()

        assert len(routes) == 2
        assert isinstance(routes, list)
        # Should return a copy, not the original list
        assert routes is not gateway.routes


class TestGatewayIntegration:
    """Test gateway integration with Velithon application."""

    def test_gateway_route_in_velithon_app(self):
        """Test adding gateway routes to a Velithon application."""
        app = Velithon()

        # Create a gateway route
        route = gateway_route(
            path='/api/v1/test/{test_id}',
            targets='http://test-service:8080',
            methods=['GET', 'POST'],
        )

        # Add to application
        app.router.routes.append(route)

        # Check that it was added (account for default OpenAPI routes)
        gateway_routes = [r for r in app.router.routes if isinstance(r, GatewayRoute)]
        assert len(gateway_routes) == 1
        assert gateway_routes[0] == route

    @pytest.mark.asyncio
    async def test_forward_to_function(self):
        """Test the forward_to convenience function."""
        with patch('velithon.gateway.ProxyClient') as mock_proxy_client:
            # Mock the proxy client
            mock_client = AsyncMock()
            mock_proxy_client.return_value = mock_client
            mock_client.forward_request = AsyncMock(
                return_value=(
                    200,
                    b'test response',
                    {'Content-Type': 'application/json'},
                )
            )

            # Create forward function
            forward_func = forward_to(
                path='/api/test', target='http://test:8080', timeout_ms=5000
            )

            # Mock request
            mock_request = MagicMock(spec=Request)
            mock_request.method = 'GET'
            mock_request.url.path = '/api/test'
            mock_request.headers = {'Authorization': 'Bearer token'}
            mock_request.body = AsyncMock(return_value=b'')
            mock_request.query_params = {}

            # Call the forward function
            response = await forward_func(mock_request)

            # Verify response
            assert isinstance(response, Response)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_forward_to_function_error_handling(self):
        """Test error handling in forward_to function."""
        with patch('velithon._velithon.ProxyClient') as mock_proxy_client:
            # Mock the proxy client to raise an exception
            mock_client = AsyncMock()
            mock_proxy_client.return_value = mock_client
            mock_client.forward_request.side_effect = Exception('Connection failed')

            # Create forward function
            forward_func = forward_to(path='/api/test', target='http://test:8080')

            # Mock request
            mock_request = MagicMock(spec=Request)
            mock_request.method = 'GET'
            mock_request.url.path = '/api/test'
            mock_request.headers = {}
            mock_request.body.return_value = b''
            mock_request.query_params = {}

            # Call the forward function
            response = await forward_func(mock_request)

            # Verify error response
            assert isinstance(response, JSONResponse)
            assert response.status_code == 502


class TestGatewayUtilities:
    """Test gateway utility functions."""

    def test_gateway_route_convenience_function(self):
        """Test the gateway_route convenience function."""
        route = gateway_route(
            path='/api/convenience',
            targets=['http://service1:8080', 'http://service2:8080'],
            load_balancing_strategy='random',
            timeout_ms=8000,
        )

        assert isinstance(route, GatewayRoute)
        assert route.path == '/api/convenience'
        assert route.timeout_ms == 8000
        assert route.load_balancer is not None

    def test_gateway_route_strip_path_functionality(self):
        """Test path stripping configuration."""
        route = GatewayRoute(
            path='/api/v1/service/{path:path}',
            targets='http://backend:8080',
            strip_path=True,
        )

        assert route.strip_path is True

    def test_gateway_route_path_rewrite_functionality(self):
        """Test path rewriting configuration."""
        route = GatewayRoute(
            path='/v2/api/{path:path}',
            targets='http://backend:8080',
            path_rewrite='/v1/api/{path}',
        )

        assert route.path_rewrite == '/v1/api/{path}'


# Performance and stress testing
class TestGatewayPerformance:
    """Test gateway performance characteristics."""

    @pytest.mark.asyncio
    async def test_gateway_concurrent_requests(self):
        """Test gateway handling multiple concurrent requests."""
        with patch('velithon.gateway.ProxyClient') as mock_proxy_client:
            # Mock successful responses
            mock_client = AsyncMock()
            mock_proxy_client.return_value = mock_client
            mock_client.forward_request = AsyncMock(return_value=(200, b'OK', {}))

            # Create multiple mock requests
            async def make_request():
                mock_request = MagicMock(spec=Request)
                mock_request.method = 'GET'
                mock_request.url.path = '/api/test'
                mock_request.headers = {}
                mock_request.body = AsyncMock(return_value=b'')
                mock_request.query_params = {}

                forward_func = forward_to('/api/test', 'http://test:8080')
                return await forward_func(mock_request)

            # Run concurrent requests
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)

            # Verify all requests succeeded
            assert len(responses) == 10
            for response in responses:
                assert response.status_code == 200

    def test_gateway_route_memory_efficiency(self):
        """Test that gateway routes don't consume excessive memory."""
        routes = []

        # Create many gateway routes
        for i in range(1000):
            route = GatewayRoute(
                path=f'/api/service{i}', targets=f'http://service{i}:8080'
            )
            routes.append(route)

        # Verify they were created successfully
        assert len(routes) == 1000

        # Basic memory check - routes should be lightweight
        import sys

        total_size = sum(sys.getsizeof(route) for route in routes)
        # Should be reasonable size (less than 1MB for 1000 routes)
        assert total_size < 1024 * 1024


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])
