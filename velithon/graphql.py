"""
High-performance GraphQL implementation for Velithon framework.

This module provides GraphQL functionality with a Rust backend for maximum performance,
including schema creation, query execution, batch operations, and GraphQL Playground.
"""

from typing import Any, Dict, List, Optional, Union
from velithon.endpoint import HTTPEndpoint
from velithon.datastructures import Protocol, Scope
from velithon.responses import HTMLResponse, JSONResponse

# Import the Rust GraphQL module
from velithon._velithon import create_query_builder as _create_query_builder

import json
from typing import Any, Optional, Dict, List
from dataclasses import dataclass

from ._velithon import (
    GraphQLSchema as RustGraphQLSchema,
    GraphQLQueryBuilder as RustGraphQLQueryBuilder,
    create_graphql_schema,
    create_query_builder,
)
from .endpoint import HTTPEndpoint
from .responses import JSONResponse


@dataclass
class GraphQLResponse:
    """GraphQL response data structure."""
    
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    extensions: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json(cls, json_str: str) -> "GraphQLResponse":
        """Create GraphQL response from JSON string."""
        try:
            data = json.loads(json_str)
            return cls(
                data=data.get("data"),
                errors=data.get("errors"),
                extensions=data.get("extensions")
            )
        except json.JSONDecodeError as e:
            return cls(errors=[{"message": f"JSON decode error: {str(e)}"}])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {}
        if self.data is not None:
            result["data"] = self.data
        if self.errors is not None:
            result["errors"] = self.errors
        if self.extensions is not None:
            result["extensions"] = self.extensions
        return result


class GraphQLSchema:
    """High-performance GraphQL schema with Rust backend."""

    def __init__(self, extended: bool = False):
        """
        Initialize GraphQL schema.
        
        Args:
            extended: Whether to use the extended schema with User/Post types
        """
        if extended:
            # For now, use basic schema
            # TODO: Implement ExtendedGraphQLSchema when needed
            self._rust_schema = RustGraphQLSchema()
        else:
            self._rust_schema = RustGraphQLSchema()

    def execute(
        self, 
        query: str, 
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GraphQLResponse:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Name of the operation to execute
            context: Execution context
            
        Returns:
            GraphQLResponse object with results
        """
        try:
            result_json = self._rust_schema.execute(query, variables, operation_name)
            return GraphQLResponse.from_json(result_json)
        except Exception as e:
            return GraphQLResponse(errors=[{"message": str(e)}])

    def execute_batch(self, queries: List[Dict[str, Any]]) -> List[GraphQLResponse]:
        """
        Execute multiple GraphQL queries in batch.
        
        Args:
            queries: List of query objects with 'query', 'variables', and 'operationName' keys
            
        Returns:
            List of GraphQLResponse objects
        """
        try:
            results = self._rust_schema.execute_batch(queries)
            return [GraphQLResponse.from_json(result) for result in results]
        except Exception as e:
            return [GraphQLResponse(errors=[{"message": str(e)}])]

    def validate(self, query: str) -> bool:
        """
        Validate a GraphQL query without executing it.
        
        Args:
            query: GraphQL query string to validate
            
        Returns:
            True if query is valid, False otherwise
        """
        return self._rust_schema.validate(query)

    def get_schema_sdl(self) -> str:
        """
        Get the GraphQL schema definition (SDL).
        
        Returns:
            Schema definition language string
        """
        return self._rust_schema.get_schema_sdl()


class GraphQLQueryBuilder:
    """High-performance GraphQL query builder."""

    def __init__(self):
        """Initialize query builder."""
        self._rust_builder = RustGraphQLQueryBuilder()

    def field(
        self, 
        field_name: str, 
        args: Optional[Dict[str, Any]] = None, 
        subfields: Optional[List[str]] = None
    ) -> "GraphQLQueryBuilder":
        """
        Add a field to the query.
        
        Args:
            field_name: Name of the field
            args: Field arguments
            subfields: Subfields to include
            
        Returns:
            Self for method chaining
        """
        self._rust_builder.field(field_name, args, subfields)
        return self

    def build(self, operation_type: str = "query") -> str:
        """
        Build the GraphQL query string.
        
        Args:
            operation_type: Type of operation (query, mutation, subscription)
            
        Returns:
            GraphQL query string
        """
        return self._rust_builder.build(operation_type)

    def reset(self) -> "GraphQLQueryBuilder":
        """
        Reset the query builder.
        
        Returns:
            Self for method chaining
        """
        self._rust_builder.reset()
        return self


class GraphQLEndpoint(HTTPEndpoint):
    """HTTP endpoint for GraphQL queries with built-in GraphQL Playground."""

    def __init__(self, scope: Scope, protocol: Protocol, schema: Optional[GraphQLSchema] = None, playground: bool = True):
        """
        Initialize GraphQL endpoint.
        
        Args:
            scope: ASGI scope
            protocol: Protocol instance
            schema: GraphQL schema to use (creates default if None)
            playground: Whether to enable GraphQL Playground
        """
        super().__init__(scope, protocol)
        self.schema = schema or GraphQLSchema()
        self.playground_enabled = playground

    async def get(self, request):
        """
        Handle GET requests - serve GraphQL Playground if enabled.
        
        Args:
            request: HTTP request object
            
        Returns:
            GraphQL Playground HTML or 404 error
        """
        if not self.playground_enabled:
            return JSONResponse({"error": "GraphQL Playground is disabled"}, status_code=404)

        playground_html = self._get_playground_html()
        return JSONResponse(playground_html, headers={"Content-Type": "text/html"})

    async def post(self, request):
        """
        Handle POST requests - execute GraphQL queries.
        
        Args:
            request: HTTP request object
            
        Returns:
            GraphQL execution results
        """
        try:
            # Parse request body
            content_type = request.headers.get("content-type", "").lower()
            
            if "application/json" in content_type:
                body = await request.json()
                
                if isinstance(body, list):
                    # Batch query
                    responses = self.schema.execute_batch(body)
                    return JSONResponse([resp.to_dict() for resp in responses])
                else:
                    # Single query
                    query = body.get("query", "")
                    variables = body.get("variables")
                    operation_name = body.get("operationName")
                    
                    response = self.schema.execute(query, variables, operation_name)
                    return JSONResponse(response.to_dict())
            else:
                return JSONResponse(
                    {"errors": [{"message": "Content-Type must be application/json"}]}, 
                    status_code=400
                )
                
        except Exception as e:
            return JSONResponse(
                {"errors": [{"message": str(e)}]}, 
                status_code=500
            )

    def _get_playground_html(self) -> str:
        """
        Generate GraphQL Playground HTML.
        
        Returns:
            HTML string for GraphQL Playground
        """
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GraphQL Playground</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <link
                rel="stylesheet"
                href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/static/css/index.css"
            />
            <link
                rel="shortcut icon"
                href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/favicon.png"
            />
        </head>
        <body>
            <div id="root"></div>
            <script
                src="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.8/build/static/js/middleware.js"
            ></script>
            <script>
                window.GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: window.location.href,
                    settings: {
                        'editor.theme': 'dark',
                        'editor.fontSize': 14,
                        'request.credentials': 'same-origin'
                    }
                });
            </script>
        </body>
        </html>
        """


# Convenience functions
def create_schema(**kwargs) -> GraphQLSchema:
    """
    Create a new GraphQL schema.
    
    Args:
        **kwargs: Arguments passed to GraphQLSchema constructor
        
    Returns:
        New GraphQLSchema instance
    """
    return GraphQLSchema(**kwargs)


def create_query_builder() -> GraphQLQueryBuilder:
    """
    Create a new GraphQL query builder.
    
    Returns:
        New GraphQLQueryBuilder instance
    """
    return GraphQLQueryBuilder()


# Export all public classes and functions
__all__ = [
    "GraphQLSchema",
    "GraphQLQueryBuilder", 
    "GraphQLEndpoint",
    "GraphQLResponse",
    "create_schema",
    "create_query_builder",
]