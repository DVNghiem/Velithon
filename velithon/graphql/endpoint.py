"""GraphQL endpoint implementation for Velithon framework.

This module provides the core GraphQL endpoint that handles GraphQL queries,
mutations, and subscriptions following Velithon's performance-first approach.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from graphql import GraphQLError, execute, parse, validate

from velithon.endpoint import HTTPEndpoint
from velithon.exceptions import BadRequestException, InternalServerException
from velithon.requests import Request
from velithon.responses import HTMLResponse, JSONResponse, Response

from .schema import GraphQLSchema

logger = logging.getLogger(__name__)


class GraphQLEndpoint(HTTPEndpoint):
    """HTTP endpoint for handling GraphQL requests.

    This endpoint supports both GET and POST requests for GraphQL operations:
    - GET requests for queries with query parameters
    - POST requests for queries, mutations, and subscriptions with JSON body
    """

    def __init__(
        self,
        schema: GraphQLSchema,
        context_value: Any = None,
        root_value: Any = None,
        debug: bool = False,
        introspection: bool = True,
        playground: bool = True,
    ):
        """Initialize GraphQL endpoint.

        Args:
            schema: GraphQL schema instance
            context_value: Context value passed to resolvers
            root_value: Root value for resolvers
            debug: Enable debug mode for detailed error messages
            introspection: Enable GraphQL introspection
            playground: Enable GraphQL Playground

        """
        self.schema = schema
        self.context_value = context_value
        self.root_value = root_value
        self.debug = debug
        self.introspection = introspection
        self.playground = playground

    async def get(self, request: Request) -> Response:
        """Handle GET requests for GraphQL queries.

        Args:
            request: The HTTP request object

        Returns:
            Response: GraphQL query result or GraphQL Playground HTML

        """
        # Check if this is a request for GraphQL Playground
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and self.playground:
            return await self._serve_playground(request)

        # Handle GraphQL query via GET
        query = request.query_params.get("query")
        if not query:
            raise BadRequestException("Missing 'query' parameter")

        variables_param = request.query_params.get("variables")
        variables = None
        if variables_param:
            try:
                variables = json.loads(variables_param)
            except json.JSONDecodeError as e:
                raise BadRequestException(f"Invalid variables JSON: {e}") from e

        operation_name = request.query_params.get("operationName")

        return await self._execute_graphql(
            query=query,
            variables=variables,
            operation_name=operation_name,
            context_value=self.context_value,
            request=request,
        )

    async def post(self, request: Request) -> Response:
        """Handle POST requests for GraphQL operations.

        Args:
            request: The HTTP request object

        Returns:
            Response: GraphQL operation result

        """
        content_type = request.headers.get("content-type", "")

        if not content_type.startswith("application/json"):
            raise BadRequestException("Content-Type must be application/json")

        try:
            body = await request.json()
        except Exception as e:
            raise BadRequestException(f"Invalid JSON body: {e}") from e

        if not isinstance(body, dict):
            raise BadRequestException("Request body must be a JSON object")

        query = body.get("query")
        if not query:
            raise BadRequestException("Missing 'query' field in request body")

        variables = body.get("variables")
        operation_name = body.get("operationName")

        return await self._execute_graphql(
            query=query,
            variables=variables,
            operation_name=operation_name,
            context_value=self.context_value,
            request=request,
        )

    async def _execute_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
        context_value: Any = None,
        request: Request | None = None,
    ) -> Response:
        """Execute a GraphQL operation.

        Args:
            query: GraphQL query string
            variables: Query variables
            operation_name: Name of the operation to execute
            context_value: Context value for resolvers
            request: HTTP request object

        Returns:
            Response: GraphQL execution result

        """
        try:
            # Parse the query
            try:
                document = parse(query)
            except GraphQLError as e:
                return JSONResponse(
                    {"errors": [{"message": str(e)}]},
                    status_code=400,
                )

            # Validate the query against the schema
            schema = self.schema.build()
            validation_errors = validate(schema, document)
            if validation_errors:
                return JSONResponse(
                    {
                        "errors": [
                            {"message": str(error)} for error in validation_errors
                        ]
                    },
                    status_code=400,
                )

            # Create context with request if available
            execution_context = context_value or {}
            if request:
                execution_context = {
                    **(
                        execution_context
                        if isinstance(execution_context, dict)
                        else {}
                    ),
                    "request": request,
                }

            # Execute the query
            result = execute(
                schema=schema,
                document=document,
                root_value=self.root_value,
                context_value=execution_context,
                variable_values=variables,
                operation_name=operation_name,
            )

            # Format the response
            response_data = {"data": result.data}

            if result.errors:
                response_data["errors"] = [
                    {
                        "message": str(error),
                        "locations": (
                            [
                                {"line": loc.line, "column": loc.column}
                                for loc in error.locations
                            ]
                            if error.locations
                            else None
                        ),
                        "path": error.path,
                    }
                    for error in result.errors
                ]

            # Include extensions if present
            if hasattr(result, "extensions") and result.extensions:
                response_data["extensions"] = result.extensions

            return JSONResponse(response_data)

        except Exception as e:
            logger.exception("GraphQL execution error: %s", str(e))

            if self.debug:
                return JSONResponse(
                    {
                        "errors": [
                            {
                                "message": str(e),
                                "extensions": {
                                    "code": "INTERNAL_ERROR",
                                    "exception": {
                                        "stacktrace": [str(e)],
                                    },
                                },
                            }
                        ]
                    },
                    status_code=500,
                )
            else:
                raise InternalServerException("Internal server error") from e

    async def _serve_playground(self, request: Request) -> Response:
        """Serve GraphQL Playground HTML.

        Args:
            request: HTTP request object

        Returns:
            Response: HTML response with GraphQL Playground

        """
        from .playground import get_playground_html

        playground_html = get_playground_html(
            endpoint_url=str(request.url.path),
            subscription_endpoint=None,  # TODO: Add WebSocket support
        )

        return HTMLResponse(playground_html)
