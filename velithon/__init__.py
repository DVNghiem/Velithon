"""Velithon - High-performance async web framework.

Velithon is a modern, fast (high-performance), web framework for building APIs
"""

__version__ = '0.6.9'

# Core application
from .application import Velithon

# WebSocket support
from .websocket import WebSocket, WebSocketEndpoint, WebSocketRoute, websocket_route

# Gateway functionality
from .gateway import Gateway, GatewayRoute, gateway_route, forward_to

# Request and Response classes
from .requests import Request
from .responses import (
    Response,
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    FileResponse,
    StreamingResponse,
    SSEResponse,
    ProxyResponse,
)

# Routing
from .routing import Router, Route, request_response

# Middleware
from .middleware import Middleware

# Common exceptions
from .exceptions import (
    HTTPException,
    VelithonError,
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    InternalServerException,
    ValidationException,
)

# HTTP status codes (most commonly used)
from .status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

# GraphQL support
from .graphql import (
    GraphQLEndpoint,
    GraphQLMiddleware,
    GraphQLPlayground,
    GraphQLRoute,
    GraphQLSchema,
    Field,
    Mutation,
    ObjectType,
    Query,
    Subscription,
    graphql_field,
    graphql_route,
    graphql_type,
)

# Context management (Flask-style)
from .ctx import (
    AppContext,
    RequestContext,
    current_app,
    request,
    g,
    has_app_context,
    has_request_context,
    get_current_app,
    get_current_request,
    get_or_create_request,
    RequestIDManager,
)

__all__ = [
    'HTTP_200_OK',
    'HTTP_201_CREATED',
    'HTTP_204_NO_CONTENT',
    'HTTP_400_BAD_REQUEST',
    'HTTP_401_UNAUTHORIZED',
    'HTTP_403_FORBIDDEN',
    'HTTP_404_NOT_FOUND',
    'HTTP_422_UNPROCESSABLE_ENTITY',
    'HTTP_500_INTERNAL_SERVER_ERROR',
    # Context management
    'AppContext',
    'BadRequestException',
    'Field',
    'FileResponse',
    'ForbiddenException',
    'Gateway',
    'GatewayRoute',
    'GraphQLEndpoint',
    'GraphQLMiddleware',
    'GraphQLPlayground',
    'GraphQLRoute',
    'GraphQLSchema',
    'HTMLResponse',
    'HTTPException',
    'InternalServerException',
    'JSONResponse',
    'Middleware',
    'Mutation',
    'NotFoundException',
    'ObjectType',
    # Performance configuration
    'PlainTextResponse',
    'ProxyResponse',
    'Query',
    'RedirectResponse',
    'Request',
    'RequestContext',
    'RequestIDManager',
    'Response',
    'Route',
    'Router',
    'SSEResponse',
    'StreamingResponse',
    'Subscription',
    'UnauthorizedException',
    'ValidationException',
    'Velithon',
    'VelithonError',
    'WebSocket',
    'WebSocketEndpoint',
    'WebSocketRoute',
    'current_app',
    'forward_to',
    'g',
    'gateway_route',
    'get_current_app',
    'get_current_request',
    'get_or_create_request',
    'graphql_field',
    'graphql_route',
    'graphql_type',
    'has_app_context',
    'has_request_context',
    'request',
    'request_response',
    'websocket_route',
]
