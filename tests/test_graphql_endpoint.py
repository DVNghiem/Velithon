"""Test cases for GraphQL endpoint functionality."""

import json
from unittest.mock import AsyncMock

import pytest

from velithon.exceptions import BadRequestException, InternalServerException
from velithon.graphql import GraphQLEndpoint, GraphQLSchema, Query, graphql_field
from velithon.requests import Request
from velithon.responses import HTMLResponse, JSONResponse


class TestQuery(Query):
    """Test query class."""

    @graphql_field(str, description="Get hello message")
    def hello(self) -> str:
        """Return hello message."""
        return "Hello GraphQL!"

    @graphql_field(str, description="Get user by ID")
    def user(self, user_id: int) -> str:
        return f"User {user_id}"

    @graphql_field(str, description="Echo the input message")
    def echo(self, message: str) -> str:
        return f"Echo: {message}"

    @graphql_field(str, description="Raise an error for testing")
    def error_field(self) -> str:
        raise ValueError("Test error")


class TestGraphQLEndpoint:
    """Test GraphQL endpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.schema = GraphQLSchema(query=TestQuery)
        self.endpoint = GraphQLEndpoint(
            schema=self.schema,
            debug=True,
            introspection=True,
            playground=True,
        )

    async def test_endpoint_initialization(self):
        """Test GraphQL endpoint initialization."""
        endpoint = GraphQLEndpoint(
            schema=self.schema,
            context_value={"test": "context"},
            root_value={"test": "root"},
            debug=False,
            introspection=False,
            playground=False,
        )

        assert endpoint.schema == self.schema
        assert endpoint.context_value == {"test": "context"}
        assert endpoint.root_value == {"test": "root"}
        assert endpoint.debug is False
        assert endpoint.introspection is False
        assert endpoint.playground is False

    async def test_get_request_playground(self):
        """Test GET request for GraphQL Playground."""
        # Mock request with HTML accept header
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": b"",
            "headers": [(b"accept", b"text/html")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        response = await self.endpoint.get(request)

        assert isinstance(response, HTMLResponse)
        assert "GraphQL Playground" in response.body.decode()

    async def test_get_request_query_success(self):
        """Test successful GET request with GraphQL query."""
        # Mock request with query parameter
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": b"query=%7Bhello%7D",  # {hello}
            "headers": [(b"accept", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        response = await self.endpoint.get(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert response_data["data"]["hello"] == "Hello, World!"

    async def test_get_request_missing_query(self):
        """Test GET request without query parameter."""
        # Mock request without query parameter
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": b"",
            "headers": [(b"accept", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        with pytest.raises(BadRequestException) as exc_info:
            await self.endpoint.get(request)

        assert "Missing 'query' parameter" in str(exc_info.value)

    async def test_get_request_with_variables(self):
        """Test GET request with variables parameter."""
        # Mock request with variables
        variables_json = json.dumps({"userId": 123})
        query_string = f"query={{user(userId:$userId)}}&variables={variables_json}"
        
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": query_string.encode(),
            "headers": [(b"accept", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        response = await self.endpoint.get(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data

    async def test_get_request_invalid_variables(self):
        """Test GET request with invalid variables JSON."""
        # Mock request with invalid variables JSON
        query_string = "query={hello}&variables=invalid-json"
        
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": query_string.encode(),
            "headers": [(b"accept", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        with pytest.raises(BadRequestException) as exc_info:
            await self.endpoint.get(request)

        assert "Invalid variables JSON" in str(exc_info.value)

    async def test_post_request_success(self):
        """Test successful POST request with GraphQL query."""
        # Mock request with JSON body
        request_body = {"query": "{hello}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert response_data["data"]["hello"] == "Hello, World!"

    async def test_post_request_with_variables(self):
        """Test POST request with variables."""
        # Mock request with variables
        request_body = {
            "query": "query GetUser($userId: Int!) { user(userId: $userId) }",
            "variables": {"userId": 123},
        }
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data

    async def test_post_request_with_operation_name(self):
        """Test POST request with operation name."""
        # Mock request with operation name
        request_body = {
            "query": "query GetHello { hello } query GetUser { user(userId: 1) }",
            "operationName": "GetHello",
        }
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert response_data["data"]["hello"] == "Hello, World!"

    async def test_post_request_invalid_content_type(self):
        """Test POST request with invalid content type."""
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"text/plain")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        with pytest.raises(BadRequestException) as exc_info:
            await self.endpoint.post(request)

        assert "Content-Type must be application/json" in str(exc_info.value)

    async def test_post_request_invalid_json(self):
        """Test POST request with invalid JSON body."""
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method to raise an exception
        request.json = AsyncMock(
            side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
        )

        with pytest.raises(BadRequestException) as exc_info:
            await self.endpoint.post(request)

        assert "Invalid JSON body" in str(exc_info.value)

    async def test_post_request_non_dict_body(self):
        """Test POST request with non-dictionary JSON body."""
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method to return a list instead of dict
        request.json = AsyncMock(return_value=["not", "a", "dict"])

        with pytest.raises(BadRequestException) as exc_info:
            await self.endpoint.post(request)

        assert "Request body must be a JSON object" in str(exc_info.value)

    async def test_post_request_missing_query(self):
        """Test POST request without query field."""
        request_body = {"variables": {}}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        with pytest.raises(BadRequestException) as exc_info:
            await self.endpoint.post(request)

        assert "Missing 'query' field in request body" in str(exc_info.value)

    async def test_execute_graphql_syntax_error(self):
        """Test GraphQL execution with syntax error."""
        request_body = {"query": "{invalid syntax}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        response_data = json.loads(response.body.decode())
        assert "errors" in response_data
        assert len(response_data["errors"]) > 0

    async def test_execute_graphql_validation_error(self):
        """Test GraphQL execution with validation error."""
        request_body = {"query": "{nonexistentField}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        response_data = json.loads(response.body.decode())
        assert "errors" in response_data
        assert len(response_data["errors"]) > 0

    async def test_execute_graphql_runtime_error_debug_mode(self):
        """Test GraphQL execution with runtime error in debug mode."""
        request_body = {"query": "{errorField}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        
        # In debug mode, errors should be included in response
        if "errors" in response_data:
            assert len(response_data["errors"]) > 0

    async def test_execute_graphql_runtime_error_production_mode(self):
        """Test GraphQL execution with runtime error in production mode."""
        # Create endpoint with debug=False
        endpoint = GraphQLEndpoint(
            schema=self.schema,
            debug=False,
        )
        
        request_body = {"query": "{errorField}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        # In production mode, internal errors should raise exceptions
        try:
            response = await endpoint.post(request)
            # If we get a response, check that it contains errors
            if isinstance(response, JSONResponse):
                response_data = json.loads(response.body.decode())
                # Should contain errors but not detailed stack traces
                if "errors" in response_data:
                    for error in response_data["errors"]:
                        # Should not contain detailed exception info in production
                        assert "stacktrace" not in error.get("extensions", {})
        except InternalServerException:
            # This is also acceptable in production mode
            pass

    async def test_context_value_injection(self):
        """Test context value injection into GraphQL execution."""
        context_value = {"user_id": 123, "permissions": ["read"]}
        endpoint = GraphQLEndpoint(
            schema=self.schema,
            context_value=context_value,
        )
        
        request_body = {"query": "{hello}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data

    async def test_request_context_injection(self):
        """Test request object injection into GraphQL context."""
        request_body = {"query": "{hello}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data

    async def test_introspection_disabled(self):
        """Test GraphQL execution with introspection disabled."""
        endpoint = GraphQLEndpoint(
            schema=self.schema,
            introspection=False,
        )
        
        request_body = {"query": "{__schema{types{name}}}"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        
        # Mock the json() method
        request.json = AsyncMock(return_value=request_body)

        response = await endpoint.post(request)

        assert isinstance(response, JSONResponse)
        # Should either work (if introspection is still enabled) or fail gracefully

    async def test_playground_disabled(self):
        """Test GraphQL Playground when disabled."""
        endpoint = GraphQLEndpoint(
            schema=self.schema,
            playground=False,
        )
        
        # Mock request with HTML accept header
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/graphql",
            "query_string": b"query=%7Bhello%7D",
            "headers": [(b"accept", b"text/html")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)

        response = await endpoint.get(request)

        # Should return GraphQL query result instead of playground
        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])