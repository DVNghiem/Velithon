"""Velithon - High-performance async web framework.

Velithon is a modern, fast (high-performance), web framework for building APIs
"""

__version__ = '0.4.1'

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
    OptimizedJSONResponse,
    BatchJSONResponse,
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
    'BadRequestException',
    'BatchJSONResponse',
    'FileResponse',
    'ForbiddenException',
    'Gateway',
    'GatewayRoute',
    'HTMLResponse',
    'HTTPException',
    'InternalServerException',
    'JSONResponse',
    'Middleware',
    'NotFoundException',
    'OptimizedJSONResponse',
    'PlainTextResponse',
    'ProxyResponse',
    'RedirectResponse',
    'Request',
    'Response',
    'Route',
    'Router',
    'SSEResponse',
    'StreamingResponse',
    'UnauthorizedException',
    'ValidationException',
    'Velithon',
    'VelithonError',
    'WebSocket',
    'WebSocketEndpoint',
    'WebSocketRoute',
    'forward_to',
    'gateway_route',
    'request_response',
    'websocket_route',
]
