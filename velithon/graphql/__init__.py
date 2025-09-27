"""GraphQL support for Velithon framework.

This module provides comprehensive GraphQL support for Velithon,
including schema definition, query execution, and GraphQL Playground integration.
Following Velithon's Rust-first approach for performance optimization.
"""

from .endpoint import GraphQLEndpoint
from .middleware import GraphQLMiddleware, GraphQLAuthMiddleware, \
    GraphQLLoggingMiddleware
from .playground import GraphQLPlayground, get_playground_html
from .route import GraphQLRoute, graphql_route
from .schema import (
    Field,
    GraphQLSchema,
    Mutation,
    ObjectType,
    Query,
    Subscription,
    graphql_field,
    graphql_type,
)

__all__ = [
    "Field",
    "GraphQLAuthMiddleware",
    "GraphQLEndpoint",
    "GraphQLLoggingMiddleware",
    "GraphQLMiddleware",
    "GraphQLPlayground",
    "GraphQLRoute",
    "GraphQLSchema",
    "Mutation",
    "ObjectType",
    "Query",
    "Subscription",
    "get_playground_html",
    "graphql_field",
    "graphql_route",
    "graphql_type",
]
