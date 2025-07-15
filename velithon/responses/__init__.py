"""Response types for Velithon framework.

This module provides various response types for different use cases while maintaining
backward compatibility with the existing import structure.
"""

# Import all response types from their respective modules
from .base import Response
from .html import HTMLResponse
from .json_unified import JsonResponse
from .plain_text import PlainTextResponse
from .redirect import RedirectResponse
from .file import FileResponse
from .streaming import StreamingResponse
from .sse import SSEResponse
from .proxy import ProxyResponse

# Backward compatibility - alias the unified JsonResponse
JSONResponse = JsonResponse  # For backward compatibility

# Export all response types
__all__ = [
    # Base response
    'Response',
    # Standard response types
    'FileResponse',
    'HTMLResponse',
    'JSONResponse',         # Backward compatibility alias
    'JsonResponse',         # The main JSON response
    'PlainTextResponse',
    'ProxyResponse',
    'RedirectResponse',
    'SSEResponse',
    'StreamingResponse',
]
