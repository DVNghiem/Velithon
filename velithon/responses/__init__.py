"""Response types for Velithon framework.

This module provides various response types for different use cases while maintaining
backward compatibility with the existing import structure.
"""

# Import all response types from their respective modules
from .base import Response
from .html import HTMLResponse
from .json import JSONResponse
from .plain_text import PlainTextResponse
from .redirect import RedirectResponse
from .file import FileResponse
from .streaming import StreamingResponse
from .sse import SSEResponse
from .proxy import ProxyResponse

# Import specialized JSON responses
from .json_optimized import OptimizedJSONResponse, BatchJSONResponse
from .json_optimized import json_response, batch_json_response

# Export all response types for backward compatibility
__all__ = [
    # Base response
    'Response',
    # Standard response types
    'HTMLResponse',
    'JSONResponse',
    'PlainTextResponse',
    'RedirectResponse',
    'FileResponse',
    'StreamingResponse',
    'SSEResponse',
    'ProxyResponse',
    # Optimized JSON responses
    'OptimizedJSONResponse',
    'BatchJSONResponse',
    'json_response',
    'batch_json_response',
]
