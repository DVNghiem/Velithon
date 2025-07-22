"""Velithon - High-performance async web framework.

Velithon is a modern, fast (high-performance), web framework for building APIs
"""

__version__ = '0.5.0'

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

# Memory management utilities
from .memory_management import (
    enable_memory_optimizations,
    disable_memory_optimizations,
    get_memory_stats,
    manual_memory_cleanup,
    get_memory_optimizer,
    RequestMemoryContext,
    with_memory_optimization,
    with_lightweight_memory_optimization,
    set_lightweight_mode,
    get_memory_context,
)

# Memory management middleware
from .middleware.memory_management import (
    MemoryManagementMiddleware,
    MemoryMonitoringMiddleware,
    GCTuningMiddleware,
    add_memory_management,
    add_memory_monitoring,
    add_gc_tuning,
)

# Performance configuration
from .performance import PerformanceConfig, configure_performance

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
    'FileResponse',
    'ForbiddenException',
    'GCTuningMiddleware',
    'Gateway',
    'GatewayRoute',
    'HTMLResponse',
    'HTTPException',
    'InternalServerException',
    'JSONResponse',
    # Memory management middleware
    'MemoryManagementMiddleware',
    'MemoryMonitoringMiddleware',
    'Middleware',
    'NotFoundException',
    # Performance configuration
    'PerformanceConfig',
    'PlainTextResponse',
    'ProxyResponse',
    'RedirectResponse',
    'Request',
    'RequestContext',
    'RequestIDManager',
    'RequestMemoryContext',
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
    'add_gc_tuning',
    'add_memory_management',
    'add_memory_monitoring',
    'configure_performance',
    'current_app',
    'disable_memory_optimizations',
    # Memory optimization functions
    'enable_memory_optimizations',
    'forward_to',
    'g',
    'gateway_route',
    'get_current_app',
    'get_current_request',
    'get_memory_context',
    'get_memory_optimizer',
    'get_memory_stats',
    'get_or_create_request',
    'has_app_context',
    'has_request_context',
    'manual_memory_cleanup',
    'request',
    'request_response',
    'set_lightweight_mode',
    'websocket_route',
    'with_lightweight_memory_optimization',
    'with_memory_optimization',
]
