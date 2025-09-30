"""GraphQL route implementation for Velithon framework.

This module provides GraphQL route classes and decorators that integrate
with Velithon's routing system.
"""

from __future__ import annotations

from typing import Any

from velithon.routing import BaseRoute

from .endpoint import GraphQLEndpoint
from .schema import GraphQLSchema


class GraphQLRoute(BaseRoute):
    """GraphQL route that handles GraphQL requests within Velithon's routing system."""

    def __init__(
        self,
        path: str,
        schema: GraphQLSchema,
        context_value: Any = None,
        root_value: Any = None,
        debug: bool = False,
        introspection: bool = True,
        playground: bool = True,
        name: str | None = None,
    ):
        """Initialize GraphQL route.

        Args:
            path: URL path for the GraphQL endpoint
            schema: GraphQL schema instance
            context_value: Context value passed to resolvers
            root_value: Root value for resolvers
            debug: Enable debug mode for detailed error messages
            introspection: Enable GraphQL introspection
            playground: Enable GraphQL Playground
            name: Route name

        """
        self.path = path
        self.schema = schema
        self.context_value = context_value
        self.root_value = root_value
        self.debug = debug
        self.introspection = introspection
        self.playground = playground
        self.name = name or "graphql"

        # Create the GraphQL endpoint
        self.endpoint = GraphQLEndpoint(
            schema=schema,
            context_value=context_value,
            root_value=root_value,
            debug=debug,
            introspection=introspection,
            playground=playground,
        )

    def matches(self, scope):
        """Check if the route matches the given scope."""
        from velithon._velithon import Match, compile_path
        from velithon.convertors import CONVERTOR_TYPES

        # Compile the path pattern
        regex, _, _ = compile_path(self.path, CONVERTOR_TYPES)

        # Check if the path matches
        path = scope.path if hasattr(scope, 'path') else scope.get('path', '')
        match = regex.match(path)

        if match:
            path_params = match.groupdict()
            if hasattr(scope, 'path_params'):
                scope.path_params = path_params
            else:
                scope['path_params'] = path_params
            return Match.FULL, scope
        else:
            return Match.NONE, scope

    async def handle(self, scope, protocol):
        """Handle the GraphQL request."""
        return await self.endpoint(scope, protocol)

    async def openapi(self):
        """Generate OpenAPI documentation for GraphQL endpoint."""
        # GraphQL endpoints typically don't use OpenAPI, but we can provide basic info
        path_schema = {
            "get": {
                "summary": "GraphQL Playground",
                "description": "Interactive GraphQL IDE for development and testing",
                "responses": {
                    "200": {
                        "description": "GraphQL Playground HTML",
                        "content": {"text/html": {"schema": {"type": "string"}}},
                    }
                },
            },
            "post": {
                "summary": "GraphQL Query",
                "description": "Execute GraphQL queries, mutations, and subscriptions",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "GraphQL query string",
                                    },
                                    "variables": {
                                        "type": "object",
                                        "description": "Query variables",
                                    },
                                    "operationName": {
                                        "type": "string",
                                        "description": "Operation name",
                                    },
                                },
                                "required": ["query"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "GraphQL response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {"description": "Query result"},
                                        "errors": {
                                            "type": "array",
                                            "items": {"type": "object"},
                                            "description": "Query errors",
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            },
        }

        parameters = {}
        return path_schema, parameters


def graphql_route(
    path: str,
    schema: GraphQLSchema,
    context_value: Any = None,
    root_value: Any = None,
    debug: bool = False,
    introspection: bool = True,
    playground: bool = True,
    name: str | None = None,
) -> GraphQLRoute:
    """Create a GraphQL route.

    Args:
        path: URL path for the GraphQL endpoint
        schema: GraphQL schema instance
        context_value: Context value passed to resolvers
        root_value: Root value for resolvers
        debug: Enable debug mode for detailed error messages
        introspection: Enable GraphQL introspection
        playground: Enable GraphQL Playground
        name: Route name

    Returns:
        GraphQLRoute: Configured GraphQL route

    """
    return GraphQLRoute(
        path=path,
        schema=schema,
        context_value=context_value,
        root_value=root_value,
        debug=debug,
        introspection=introspection,
        playground=playground,
        name=name,
    )
