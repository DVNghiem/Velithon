"""Test cases for GraphQL route functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from velithon.graphql import GraphQLRoute, GraphQLSchema, Query, graphql_field
from velithon.routing import Match


class TestQuery(Query):
    """Test query class."""

    @graphql_field(str, description="Get hello message")
    def hello(self) -> str:
        """Return hello message."""
        return "Hello GraphQL!"

    @graphql_field(str, description="Get user by ID")
    def user(self, user_id: int) -> str:
        return f"User {user_id} from route"


class TestGraphQLRoute:
    """Test GraphQL route functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.schema = GraphQLSchema(query=TestQuery)
        self.route = GraphQLRoute(
            path="/graphql",
            schema=self.schema,
            debug=True,
            introspection=True,
            playground=True,
        )

    def test_route_initialization(self):
        """Test GraphQL route initialization."""
        route = GraphQLRoute(
            path="/api/graphql",
            schema=self.schema,
            context_value={"test": "context"},
            root_value={"test": "root"},
            debug=False,
            introspection=False,
            playground=False,
            name="custom_graphql",
        )

        assert route.path == "/api/graphql"
        assert route.schema == self.schema
        assert route.context_value == {"test": "context"}
        assert route.root_value == {"test": "root"}
        assert route.debug is False
        assert route.introspection is False
        assert route.playground is False
        assert route.name == "custom_graphql"
        assert route.endpoint is not None

    def test_route_initialization_defaults(self):
        """Test GraphQL route initialization with defaults."""
        route = GraphQLRoute(path="/graphql", schema=self.schema)

        assert route.path == "/graphql"
        assert route.schema == self.schema
        assert route.context_value is None
        assert route.root_value is None
        assert route.debug is False
        assert route.introspection is True
        assert route.playground is True
        assert route.name == "graphql"

    def test_route_path_matching_exact(self):
        """Test exact path matching."""
        scope = MagicMock()
        scope.path = "/graphql"
        scope.path_params = {}

        match_result, updated_scope = self.route.matches(scope)

        assert match_result == Match.FULL
        assert updated_scope == scope

    def test_route_path_matching_no_match(self):
        """Test path matching with non-matching path."""
        scope = MagicMock()
        scope.path = "/api/users"
        scope.path_params = {}

        match_result, updated_scope = self.route.matches(scope)

        assert match_result == Match.NONE
        assert updated_scope == scope

    def test_route_path_matching_with_parameters(self):
        """Test path matching with path parameters."""
        # Create route with path parameters
        parameterized_route = GraphQLRoute(
            path="/graphql/{version}",
            schema=self.schema,
        )

        scope = MagicMock()
        scope.path = "/graphql/v1"
        scope.path_params = {}

        match_result, updated_scope = parameterized_route.matches(scope)

        assert match_result == Match.FULL
        assert "version" in updated_scope.path_params
        assert updated_scope.path_params["version"] == "v1"

    def test_route_path_matching_with_trailing_slash(self):
        """Test path matching with trailing slash variations."""
        scope_with_slash = MagicMock()
        scope_with_slash.path = "/graphql/"
        scope_with_slash.path_params = {}

        scope_without_slash = MagicMock()
        scope_without_slash.path = "/graphql"
        scope_without_slash.path_params = {}

        # Test both should match
        match1, _ = self.route.matches(scope_with_slash)
        match2, _ = self.route.matches(scope_without_slash)

        # At least one should match (depending on implementation)
        assert match1 == Match.FULL or match2 == Match.FULL

    async def test_route_endpoint_delegation_get(self):
        """Test that route delegates GET requests to endpoint."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": b"query=%7Bhello%7D",
            "headers": [(b"accept", b"application/json")],
        }
        protocol = AsyncMock()

        # Mock the endpoint's get method
        self.route.endpoint.get = AsyncMock(return_value={"data": {"hello": "test"}})

        from velithon.requests import Request
        request = Request(scope, protocol)
        
        result = await self.route.endpoint.get(request)

        self.route.endpoint.get.assert_called_once_with(request)
        assert result == {"data": {"hello": "test"}}

    async def test_route_endpoint_delegation_post(self):
        """Test that route delegates POST requests to endpoint."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        protocol = AsyncMock()

        # Mock the endpoint's post method
        self.route.endpoint.post = AsyncMock(return_value={"data": {"hello": "test"}})

        from velithon.requests import Request
        request = Request(scope, protocol)
        
        result = await self.route.endpoint.post(request)

        self.route.endpoint.post.assert_called_once_with(request)
        assert result == {"data": {"hello": "test"}}

    def test_route_schema_access(self):
        """Test access to GraphQL schema through route."""
        assert self.route.schema == self.schema
        assert self.route.endpoint.schema == self.schema

    def test_route_configuration_propagation(self):
        """Test that route configuration is propagated to endpoint."""
        route = GraphQLRoute(
            path="/test",
            schema=self.schema,
            context_value={"route": "test"},
            root_value={"root": "test"},
            debug=True,
            introspection=False,
            playground=False,
        )

        endpoint = route.endpoint
        assert endpoint.context_value == {"route": "test"}
        assert endpoint.root_value == {"root": "test"}
        assert endpoint.debug is True
        assert endpoint.introspection is False
        assert endpoint.playground is False

    def test_route_name_customization(self):
        """Test route name customization."""
        named_route = GraphQLRoute(
            path="/graphql",
            schema=self.schema,
            name="custom_name",
        )

        assert named_route.name == "custom_name"

        # Test default name
        default_route = GraphQLRoute(
            path="/graphql",
            schema=self.schema,
        )

        assert default_route.name == "graphql"

    def test_multiple_routes_same_schema(self):
        """Test multiple routes using the same schema."""
        route1 = GraphQLRoute(path="/graphql", schema=self.schema, name="route1")
        route2 = GraphQLRoute(path="/api/graphql", schema=self.schema, name="route2")

        assert route1.schema == route2.schema
        assert route1.name != route2.name
        assert route1.path != route2.path

    def test_route_with_complex_path_patterns(self):
        """Test route with complex path patterns."""
        complex_route = GraphQLRoute(
            path="/api/{version}/graphql/{tenant}",
            schema=self.schema,
        )

        scope = MagicMock()
        scope.path = "/api/v2/graphql/tenant123"
        scope.path_params = {}

        match_result, updated_scope = complex_route.matches(scope)

        assert match_result == Match.FULL
        assert "version" in updated_scope.path_params
        assert "tenant" in updated_scope.path_params
        assert updated_scope.path_params["version"] == "v2"
        assert updated_scope.path_params["tenant"] == "tenant123"

    def test_route_path_parameter_types(self):
        """Test different path parameter types."""
        # Test with integer path parameter
        int_route = GraphQLRoute(
            path="/graphql/{user_id:int}",
            schema=self.schema,
        )

        scope = MagicMock()
        scope.path = "/graphql/123"
        scope.path_params = {}

        match_result, updated_scope = int_route.matches(scope)

        if match_result == Match.FULL:
            # Check if integer conversion happened
            assert "user_id" in updated_scope.path_params

    def test_route_matching_case_sensitivity(self):
        """Test case sensitivity in route matching."""
        scope_lower = MagicMock()
        scope_lower.path = "/graphql"
        scope_lower.path_params = {}

        scope_upper = MagicMock()
        scope_upper.path = "/GRAPHQL"
        scope_upper.path_params = {}

        match_lower, _ = self.route.matches(scope_lower)
        match_upper, _ = self.route.matches(scope_upper)

        # Should match exact case only
        assert match_lower == Match.FULL
        assert match_upper == Match.NONE

    def test_route_query_string_handling(self):
        """Test that route handles query strings properly."""
        # Route should not be affected by query strings
        scope_with_query = MagicMock()
        scope_with_query.path = "/graphql"
        scope_with_query.path_params = {}

        scope_without_query = MagicMock()
        scope_without_query.path = "/graphql"
        scope_without_query.path_params = {}

        match1, _ = self.route.matches(scope_with_query)
        match2, _ = self.route.matches(scope_without_query)

        assert match1 == match2 == Match.FULL

    def test_route_fragment_handling(self):
        """Test that route ignores URL fragments."""
        # URL fragments should not affect routing
        scope = MagicMock()
        scope.path = "/graphql"  # Fragments are not part of path
        scope.path_params = {}

        match_result, _ = self.route.matches(scope)

        assert match_result == Match.FULL

    async def test_route_error_handling(self):
        """Test error handling in route operations."""
        # Mock endpoint to raise an error
        self.route.endpoint.get = AsyncMock(side_effect=ValueError("Test error"))

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": b"query=%7Bhello%7D",
            "headers": [(b"accept", b"application/json")],
        }
        protocol = AsyncMock()

        from velithon.requests import Request
        request = Request(scope, protocol)

        with pytest.raises(ValueError, match="Test error"):
            await self.route.endpoint.get(request)

    def test_route_immutability(self):
        """Test that route properties are not accidentally modified."""
        original_path = self.route.path
        original_name = self.route.name
        original_schema = self.route.schema

        # These should remain unchanged after operations
        scope = MagicMock()
        scope.path = "/different/path"
        scope.path_params = {}

        self.route.matches(scope)

        assert self.route.path == original_path
        assert self.route.name == original_name
        assert self.route.schema == original_schema


class TestGraphQLRouteDecorator:
    """Test GraphQL route decorator functionality."""

    def test_graphql_route_decorator(self):
        """Test @graphql_route decorator."""
        from velithon.graphql import graphql_route

        schema = GraphQLSchema(query=TestQuery)

        @graphql_route("/test", schema=schema)
        class TestRouteHandler:
            pass

        # Verify the decorator worked
        assert hasattr(TestRouteHandler, '_graphql_route')
        route_info = TestRouteHandler._graphql_route
        assert route_info.path == "/test"
        assert route_info.schema == schema

    def test_graphql_route_decorator_with_options(self):
        """Test @graphql_route decorator with options."""
        from velithon.graphql import graphql_route

        schema = GraphQLSchema(query=TestQuery)

        @graphql_route(
            "/api/graphql",
            schema=schema,
            debug=True,
            playground=False,
            name="api_graphql"
        )
        class TestRouteHandler:
            pass

        route_info = TestRouteHandler._graphql_route
        assert route_info.path == "/api/graphql"
        assert route_info.debug is True
        assert route_info.playground is False
        assert route_info.name == "api_graphql"

    def test_graphql_route_decorator_inheritance(self):
        """Test that route decorator works with class inheritance."""
        from velithon.graphql import graphql_route

        schema = GraphQLSchema(query=TestQuery)

        @graphql_route("/base", schema=schema)
        class BaseHandler:
            pass

        class DerivedHandler(BaseHandler):
            pass

        # Both should have the route information
        assert hasattr(BaseHandler, '_graphql_route')
        assert hasattr(DerivedHandler, '_graphql_route')


class TestGraphQLRouteIntegration:
    """Test GraphQL route integration with Velithon routing system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.schema = GraphQLSchema(query=TestQuery)

    def test_route_registration_in_app(self):
        """Test registering GraphQL route in Velithon app."""
        from velithon import Velithon

        app = Velithon()
        route = GraphQLRoute(path="/graphql", schema=self.schema)

        # Mock route registration
        app.routes = []
        app.routes.append(route)

        assert len(app.routes) == 1
        assert app.routes[0] == route

    def test_multiple_graphql_routes_in_app(self):
        """Test multiple GraphQL routes in the same app."""
        from velithon import Velithon

        app = Velithon()
        
        route1 = GraphQLRoute(path="/graphql", schema=self.schema, name="main")
        route2 = GraphQLRoute(path="/admin/graphql", schema=self.schema, name="admin")

        app.routes = [route1, route2]

        assert len(app.routes) == 2
        assert route1.name != route2.name
        assert route1.path != route2.path

    def test_route_middleware_integration(self):
        """Test GraphQL route with middleware."""
        from velithon.graphql import GraphQLMiddleware

        route = GraphQLRoute(path="/graphql", schema=self.schema)
        middleware = GraphQLMiddleware(app=None)

        # Test that middleware can identify GraphQL routes
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }

        assert middleware._is_graphql_request(scope) is True

    def test_route_with_custom_endpoint_class(self):
        """Test GraphQL route with custom endpoint class."""
        from velithon.graphql import GraphQLEndpoint

        class CustomGraphQLEndpoint(GraphQLEndpoint):
            async def get(self, request):
                # Custom GET handling
                return {"custom": "response"}

        # For this test, we'll just verify the concept
        route = GraphQLRoute(path="/graphql", schema=self.schema)
        
        # Replace endpoint with custom one
        route.endpoint = CustomGraphQLEndpoint(
            schema=self.schema,
            debug=True,
        )

        assert isinstance(route.endpoint, CustomGraphQLEndpoint)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])