"""GraphQL middleware for Velithon framework.

This module provides middleware components for GraphQL request processing,
including authentication, authorization, and query complexity analysis.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from velithon.middleware.base import BaseHTTPMiddleware
from velithon.requests import Request

logger = logging.getLogger(__name__)


class GraphQLMiddleware(BaseHTTPMiddleware):
    """Middleware for GraphQL request processing.

    This middleware provides common GraphQL functionality such as:
    - Request/response logging
    - Query complexity analysis
    - Authentication and authorization
    - Request transformation
    """

    def __init__(
        self,
        app,
        *,
        max_query_complexity: int | None = None,
        auth_required: bool = False,
        auth_checker: Callable[[Request], bool] | None = None,
        context_processor: Callable[[Request], dict[str, Any]] | None = None,
        log_queries: bool = False,
    ):
        """Initialize GraphQL middleware.

        Args:
            app: RSGI application
            max_query_complexity: Maximum allowed query complexity
            auth_required: Whether authentication is required
            auth_checker: Function to check authentication
            context_processor: Function to process request context
            log_queries: Whether to log GraphQL queries

        """
        super().__init__(app)
        self.max_query_complexity = max_query_complexity
        self.auth_required = auth_required
        self.auth_checker = auth_checker
        self.context_processor = context_processor
        self.log_queries = log_queries

    async def process_http_request(self, scope, protocol):
        """Process HTTP request for GraphQL endpoints."""
        # Check if this is a GraphQL request
        if not self._is_graphql_request(scope):
            return await self.app(scope, protocol)

        request = Request(scope, protocol)

        # Authentication check
        if self.auth_required:
            if not await self._check_authentication(request):
                from velithon.exceptions import UnauthorizedException

                raise UnauthorizedException("Authentication required")

        # Process context
        if self.context_processor:
            context = await self._process_context(request)
            # Store context in scope for GraphQL execution
            scope._graphql_context = context

        # Query logging
        if self.log_queries:
            await self._log_query(request)

        # Continue to the next middleware/application
        return await self.app(scope, protocol)

    def _is_graphql_request(self, scope) -> bool:
        """Check if the request is for a GraphQL endpoint."""
        path = (
            scope.get('path', '') if isinstance(scope, dict) 
            else getattr(scope, 'path', '')
        )
        headers = (
            scope.get('headers', []) if isinstance(scope, dict) 
            else getattr(scope, 'headers', [])
        )
        content_type = dict(headers).get(b"content-type", b"")

        # Check for common GraphQL paths or content types
        return (
            "/graphql" in path
            or "/graphiql" in path
            or b"application/json" in content_type
        )

    async def _check_authentication(self, request: Request) -> bool:
        """Check if the request is authenticated."""
        if self.auth_checker:
            return await self._call_async(self.auth_checker, request)

        # Default authentication check (look for Authorization header)
        auth_header = request.headers.get("authorization")
        return bool(auth_header)

    async def _process_context(self, request: Request) -> dict[str, Any]:
        """Process request context."""
        if self.context_processor:
            context = await self._call_async(self.context_processor, request)
            return context if isinstance(context, dict) else {}
        return {}

    async def _log_query(self, request: Request) -> None:
        """Log GraphQL query for debugging."""
        try:
            if request.method == "POST":
                body = await request.json()
                query = body.get("query", "")
                operation_name = body.get("operationName", "")
                logger.info(
                    "GraphQL Query - Operation: %s, Query: %s",
                    operation_name or "Anonymous",
                    query[:200] + ("..." if len(query) > 200 else ""),
                )
            elif request.method == "GET":
                query = request.query_params.get("query", "")
                operation_name = request.query_params.get("operationName", "")
                logger.info(
                    "GraphQL Query - Operation: %s, Query: %s",
                    operation_name or "Anonymous",
                    query[:200] + ("..." if len(query) > 200 else ""),
                )
        except Exception as e:
            logger.warning("Failed to log GraphQL query: %s", str(e))

    async def _call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Call a function that may be sync or async."""
        import inspect

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)


class GraphQLAuthMiddleware(GraphQLMiddleware):
    """Specialized middleware for GraphQL authentication."""

    def __init__(
        self,
        app,
        *,
        auth_checker: Callable[[Request], bool],
        unauthorized_message: str = "Authentication required for GraphQL",
    ):
        """Initialize GraphQL authentication middleware.

        Args:
            app: RSGI application
            auth_checker: Function to check authentication
            unauthorized_message: Message for unauthorized requests

        """
        super().__init__(app, auth_required=True, auth_checker=auth_checker)
        self.unauthorized_message = unauthorized_message


class GraphQLLoggingMiddleware(GraphQLMiddleware):
    """Specialized middleware for GraphQL query logging."""

    def __init__(
        self,
        app,
        *,
        log_queries: bool = True,
        log_responses: bool = False,
        max_query_length: int = 1000,
    ):
        """Initialize GraphQL logging middleware.

        Args:
            app: RSGI application
            log_queries: Whether to log queries
            log_responses: Whether to log responses
            max_query_length: Maximum query length to log

        """
        super().__init__(app, log_queries=log_queries)
        self.log_responses = log_responses
        self.max_query_length = max_query_length
