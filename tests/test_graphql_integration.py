"""Integration tests for GraphQL functionality in Velithon framework."""

import json
from unittest.mock import AsyncMock

import pytest

from velithon import Velithon
from velithon.graphql import (
    GraphQLEndpoint,
    GraphQLMiddleware,
    GraphQLRoute,
    GraphQLSchema,
    Mutation,
    ObjectType,
    Query,
    Subscription,
    graphql_field,
    graphql_type,
)
from velithon.requests import Request
from velithon.responses import JSONResponse


# Test Data Models
@graphql_type
class User(ObjectType):
    """User type for testing."""
    
    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email

    @graphql_field(str, description="Get user's full name")
    def full_name(self) -> str:
        return f"Mr/Ms {self.name}"

    @graphql_field(bool, description="Check if user is admin")
    def is_admin(self) -> bool:
        return self.email.endswith("@admin.com")


@graphql_type
class Post(ObjectType):
    """Post type for testing."""
    
    def __init__(self, id: int, title: str, content: str, author_id: int):
        self.id = id
        self.title = title
        self.content = content
        self.author_id = author_id

    @graphql_field(str, description="Get post summary")
    def summary(self) -> str:
        return self.content[:100] + "..." if len(self.content) > 100 else self.content


# Test Database (Mock)
USERS_DB = [
    User(1, "John Doe", "john@example.com"),
    User(2, "Jane Smith", "jane@admin.com"),
    User(3, "Bob Wilson", "bob@example.com"),
]

POSTS_DB = [
    Post(1, "First Post", "This is the content of the first post.", 1),
    Post(2, "Second Post", "This is the content of the second post.", 2),
    Post(
        3, 
        "Third Post", 
        "This is a very long content for the third post that will be truncated in the summary to test the summary functionality.", 
        1
    ),
]


class TestQuery(Query):
    """Test query class with comprehensive functionality."""

    @graphql_field(str, description="Get hello message")
    def hello(self) -> str:
        return "Hello, World!"

    @graphql_field(list[User], description="Get all users")
    def users(self) -> list[User]:
        return USERS_DB

    @graphql_field(User, description="Get user by ID")
    def user(self, user_id: int) -> User | None:
        return next((user for user in USERS_DB if user.id == user_id), None)

    @graphql_field(list[Post], description="Get all posts")
    def posts(self) -> list[Post]:
        return POSTS_DB

    @graphql_field(Post, description="Get post by ID")
    def post(self, post_id: int) -> Post | None:
        return next((post for post in POSTS_DB if post.id == post_id), None)

    @graphql_field(list[Post], description="Get posts by author")
    def posts_by_author(self, author_id: int) -> list[Post]:
        return [post for post in POSTS_DB if post.author_id == author_id]

    @graphql_field(list[User], description="Search users by name")
    def search_users(self, name: str) -> list[User]:
        return [user for user in USERS_DB if name.lower() in user.name.lower()]

    @graphql_field(str, description="Get current context information")
    def context_info(self, info) -> str:
        context = info.context if hasattr(info, 'context') else {}
        return f"Context: {json.dumps(context, default=str)}"


class TestMutation(Mutation):
    """Test mutation class with CRUD operations."""

    @graphql_field(User, description="Create a new user")
    def create_user(self, name: str, email: str) -> User:
        new_id = max(user.id for user in USERS_DB) + 1
        new_user = User(new_id, name, email)
        USERS_DB.append(new_user)
        return new_user

    @graphql_field(User, description="Update user name")
    def update_user_name(self, user_id: int, name: str) -> User | None:
        user = next((user for user in USERS_DB if user.id == user_id), None)
        if user:
            user.name = name
        return user

    @graphql_field(bool, description="Delete user by ID")
    def delete_user(self, user_id: int) -> bool:
        initial_count = len(USERS_DB)
        USERS_DB[:] = [user for user in USERS_DB if user.id != user_id]
        return len(USERS_DB) < initial_count

    @graphql_field(Post, description="Create a new post")
    def create_post(self, title: str, content: str, author_id: int) -> Post:
        new_id = max(post.id for post in POSTS_DB) + 1
        new_post = Post(new_id, title, content, author_id)
        POSTS_DB.append(new_post)
        return new_post


class TestSubscription(Subscription):
    """Test subscription class for real-time updates."""

    @graphql_field(str, description="Subscribe to user updates")
    async def user_updates(self):
        # Simulate real-time updates
        for i in range(3):
            yield f"User update #{i + 1}"

    @graphql_field(str, description="Subscribe to post updates")
    async def post_updates(self):
        # Simulate post notifications
        for post in POSTS_DB:
            yield f"New post: {post.title}"


class TestGraphQLIntegration:
    """Integration tests for complete GraphQL functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.schema = GraphQLSchema(
            query=TestQuery,
            mutation=TestMutation,
            subscription=TestSubscription,
        )
        self.endpoint = GraphQLEndpoint(
            schema=self.schema,
            debug=True,
            introspection=True,
            playground=True,
        )

    async def test_simple_query_execution(self):
        """Test simple query execution."""
        query = '{ hello }'
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": query})

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert response_data["data"]["hello"] == "Hello, World!"

    async def test_complex_query_with_nested_fields(self):
        """Test complex query with nested fields."""
        query = '''
        {
            users {
                id
                name
                fullName
                isAdmin
            }
            posts {
                id
                title
                summary
            }
        }
        '''
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": query})

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert len(response_data["data"]["users"]) == len(USERS_DB)
        assert len(response_data["data"]["posts"]) == len(POSTS_DB)

    async def test_query_with_arguments(self):
        """Test query with arguments."""
        query = '''
        query GetUser($userId: Int!) {
            user(userId: $userId) {
                id
                name
                email
            }
        }
        '''
        variables = {"userId": 1}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={
            "query": query,
            "variables": variables
        })

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert response_data["data"]["user"]["id"] == 1
        assert response_data["data"]["user"]["name"] == "John Doe"

    async def test_mutation_execution(self):
        """Test mutation execution."""
        mutation = '''
        mutation CreateUser($name: String!, $email: String!) {
            createUser(name: $name, email: $email) {
                id
                name
                email
            }
        }
        '''
        variables = {"name": "New User", "email": "newuser@example.com"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={
            "query": mutation,
            "variables": variables
        })

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert response_data["data"]["createUser"]["name"] == "New User"
        assert response_data["data"]["createUser"]["email"] == "newuser@example.com"

    async def test_query_with_search_functionality(self):
        """Test query with search functionality."""
        query = '''
        query SearchUsers($name: String!) {
            searchUsers(name: $name) {
                id
                name
                email
            }
        }
        '''
        variables = {"name": "John"}
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={
            "query": query,
            "variables": variables
        })

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert len(response_data["data"]["searchUsers"]) >= 1
        assert any("John" in user["name"] for user in response_data["data"]["searchUsers"])

    async def test_error_handling_in_queries(self):
        """Test error handling in GraphQL queries."""
        # Query with invalid field
        query = '{ nonExistentField }'
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": query})

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        response_data = json.loads(response.body.decode())
        assert "errors" in response_data

    async def test_introspection_query(self):
        """Test GraphQL introspection."""
        introspection_query = '''
        {
            __schema {
                types {
                    name
                    kind
                }
            }
        }
        '''
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": introspection_query})

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert "__schema" in response_data["data"]
        assert "types" in response_data["data"]["__schema"]

    async def test_multiple_operations_query(self):
        """Test query with multiple operations."""
        query = '''
        query {
            hello
            users {
                id
                name
            }
            posts {
                id
                title
            }
        }
        '''
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": query})

        response = await self.endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        assert "hello" in response_data["data"]
        assert "users" in response_data["data"]
        assert "posts" in response_data["data"]

    async def test_context_value_in_resolvers(self):
        """Test context value access in resolvers."""
        endpoint = GraphQLEndpoint(
            schema=self.schema,
            context_value={"user_id": 123, "role": "admin"},
            debug=True,
        )
        
        query = '{ contextInfo }'
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": query})

        response = await endpoint.post(request)

        assert isinstance(response, JSONResponse)
        response_data = json.loads(response.body.decode())
        assert "data" in response_data
        # Context should be available in the response
        assert "contextInfo" in response_data["data"]


class TestGraphQLAppIntegration:
    """Test GraphQL integration with Velithon application."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = Velithon()
        self.schema = GraphQLSchema(query=TestQuery)
        
        # Add GraphQL route to app
        graphql_route = GraphQLRoute(
            path="/graphql",
            schema=self.schema,
            debug=True,
            playground=True,
        )
        self.app.routes = [graphql_route]

    def test_app_with_graphql_route(self):
        """Test Velithon app with GraphQL route."""
        assert len(self.app.routes) == 1
        assert isinstance(self.app.routes[0], GraphQLRoute)
        assert self.app.routes[0].path == "/graphql"

    def test_multiple_graphql_endpoints(self):
        """Test multiple GraphQL endpoints in the same app."""
        # Add another GraphQL route
        admin_schema = GraphQLSchema(query=TestQuery)
        admin_route = GraphQLRoute(
            path="/admin/graphql",
            schema=admin_schema,
            debug=False,
            playground=False,
            name="admin_graphql",
        )
        
        self.app.routes.append(admin_route)

        assert len(self.app.routes) == 2
        paths = [route.path for route in self.app.routes]
        assert "/graphql" in paths
        assert "/admin/graphql" in paths

    def test_graphql_with_middleware_integration(self):
        """Test GraphQL with middleware integration."""
        # Add GraphQL middleware
        graphql_middleware = GraphQLMiddleware(
            app=None,  # Will be set by app
            log_queries=True,
            auth_required=False,
        )
        
        # Middleware should be configurable
        assert graphql_middleware.log_queries is True
        assert graphql_middleware.auth_required is False

    async def test_end_to_end_graphql_flow(self):
        """Test complete end-to-end GraphQL flow."""
        # This would typically involve making actual HTTP requests
        # For now, we'll test the components work together
        
        route = self.app.routes[0]
        endpoint = route.endpoint
        
        # Test that endpoint is properly configured
        assert endpoint.schema == self.schema
        assert endpoint.debug is True
        assert endpoint.playground is True


class TestGraphQLPerformance:
    """Test GraphQL performance characteristics."""

    def setup_method(self):
        """Set up test fixtures."""
        self.schema = GraphQLSchema(query=TestQuery)
        self.endpoint = GraphQLEndpoint(schema=self.schema)

    async def test_query_execution_performance(self):
        """Test query execution performance."""
        import time
        
        query = '''
        {
            users {
                id
                name
                fullName
                isAdmin
            }
        }
        '''
        
        mock_scope = {
            "type": "http",
            "method": "POST",
            "path": "/graphql",
            "headers": [(b"content-type", b"application/json")],
        }
        mock_protocol = AsyncMock()
        request = Request(mock_scope, mock_protocol)
        request.json = AsyncMock(return_value={"query": query})

        start_time = time.time()
        response = await self.endpoint.post(request)
        execution_time = time.time() - start_time

        assert isinstance(response, JSONResponse)
        # Should execute reasonably quickly
        assert execution_time < 1.0  # Less than 1 second

    async def test_multiple_concurrent_queries(self):
        """Test handling multiple concurrent queries."""
        import asyncio
        
        query = '{ hello }'
        
        async def execute_query():
            mock_scope = {
                "type": "http",
                "method": "POST",
                "path": "/graphql",
                "headers": [(b"content-type", b"application/json")],
            }
            mock_protocol = AsyncMock()
            request = Request(mock_scope, mock_protocol)
            request.json = AsyncMock(return_value={"query": query})
            return await self.endpoint.post(request)

        # Execute multiple queries concurrently
        tasks = [execute_query() for _ in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert len(responses) == 5
        for response in responses:
            assert isinstance(response, JSONResponse)
            response_data = json.loads(response.body.decode())
            assert response_data["data"]["hello"] == "Hello, World!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])