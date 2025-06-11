"""
Tests for advanced routing functionality and path parameter handling.
"""
from unittest.mock import MagicMock

import pytest

from velithon.responses import JSONResponse
from velithon.routing import Route, Router


class TestRouterEdgeCases:
    """Test router edge cases and error conditions."""

    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope for testing."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.path = "/"
        return scope

    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol for testing."""
        return MagicMock()

    def test_empty_router(self):
        """Test router with no routes."""
        router = Router()
        assert len(router.routes) == 0

    async def test_router_nonexistent_route(self, mock_scope, mock_protocol):
        """Test router behavior with nonexistent route."""
        router = Router()
        mock_scope.path = "/nonexistent"

        await router.app(mock_scope, mock_protocol)

        # Should call default handler (404)
        mock_protocol.response_bytes.assert_called_once()
        args = mock_protocol.response_bytes.call_args[0]
        assert args[0] == 404


class TestAdvancedRouting:
    """Test advanced routing functionality."""

    @pytest.fixture
    def mock_scope(self):
        """Create a mock scope."""
        scope = MagicMock()
        scope.proto = "http"
        scope.method = "GET"
        scope.path = "/test"
        scope.headers = {}
        scope.query_string = b""
        return scope

    @pytest.fixture
    def mock_protocol(self):
        """Create a mock protocol."""
        protocol = MagicMock()
        protocol.response_bytes = MagicMock()
        return protocol

    def test_route_with_complex_path_parameters(self):
        """Test routes with complex path parameters."""
        async def handler(user_id: int, category: str, item_id: int):
            return JSONResponse({
                "user_id": user_id,
                "category": category,
                "item_id": item_id
            })

        route = Route("/users/{user_id}/categories/{category}/items/{item_id}", handler)
        
        assert route.path == "/users/{user_id}/categories/{category}/items/{item_id}"

    def test_route_name_assignment(self):
        """Test route name assignment and retrieval."""
        async def handler(request):
            return JSONResponse({"message": "test"})

        route = Route("/test", handler, name="test_route")
        assert route.name == "test_route"

    def test_duplicate_route_handling(self):
        """Test handling of duplicate route registrations."""
        router = Router()

        async def handler1(request):
            return JSONResponse({"handler": "1"})

        async def handler2(request):
            return JSONResponse({"handler": "2"})

        router.add_route("/test", handler1)
        router.add_route("/test", handler2)

        # Should have routes registered
        assert len(router.routes) >= 1
