"""Response types for Velithon framework.

This module provides various response types for different use cases while maintaining
backward compatibility with the existing import structure.
"""

# Import all response types from their respective modules
from .base import Response
from .html import HTMLResponse
from .plain_text import PlainTextResponse
from .redirect import RedirectResponse
from .file import FileResponse
from .streaming import StreamingResponse
from .sse import SSEResponse
from .proxy import ProxyResponse
from .json import JSONResponse


# Export all response types
__all__ = [
    # Standard response types
    'FileResponse',
    'HTMLResponse',
    'JSONResponse',
    'PlainTextResponse',
    'ProxyResponse',
    'RedirectResponse',
    # Base response
    'Response',
    'SSEResponse',
    'StreamingResponse',
]
