"""
Rust-based logging middleware for optimal performance.
This middleware avoids Python GIL limitations by implementing the core logic in Rust.
"""

from velithon._velithon import RustLoggingMiddleware as _RustLoggingMiddleware
from velithon._velithon import RustMiddlewareOptimizer as _RustMiddlewareOptimizer
from velithon.datastructures import Scope, Protocol


class RustLoggingMiddleware:
    """
    High-performance Rust-based logging middleware that avoids GIL issues.
    
    This middleware is significantly faster than the pure Python implementation
    because it:
    1. Minimizes time spent holding the Python GIL
    2. Uses efficient Rust data structures and async processing
    3. Performs logging operations in dedicated threads
    4. Avoids Python overhead for timing and data extraction
    
    Usage:
        from velithon.middleware.rust_logging import RustLoggingMiddleware
        
        app = Velithon(
            middleware=[
                Middleware(RustLoggingMiddleware)
            ]
        )
    """
    
    def __init__(self, app):
        """Initialize the Rust logging middleware.
        
        Args:
            app: The RSGI application to wrap
        """
        self.app = app
        self._rust_middleware = _RustLoggingMiddleware(app)
    
    async def __call__(self, scope: Scope, protocol: Protocol):
        """Process the request through the Rust middleware.
        
        Args:
            scope: The request scope
            protocol: The protocol instance
        """
        # Delegate to Rust implementation for maximum performance
        await self._rust_middleware(scope, protocol)


# For backwards compatibility, also provide the class under the old name
FastLoggingMiddleware = RustLoggingMiddleware


class RustMiddlewareOptimizer:
    """
    Rust-based middleware stack optimizer for better performance.
    
    This optimizer can:
    1. Remove duplicate middleware instances
    2. Reorder middleware for optimal execution
    3. Cache middleware configurations
    4. Detect and resolve middleware conflicts
    """
    
    def __init__(self):
        self._optimizer = _RustMiddlewareOptimizer()
    
    def optimize_middleware_stack(self, middlewares):
        """
        Optimize a list of middleware instances for better performance.
        
        Args:
            middlewares: List of middleware instances
            
        Returns:
            List of optimized middleware instances
        """
        return self._optimizer.optimize_middleware_stack(middlewares)


def get_rust_logging_middleware():
    """Factory function to get the Rust logging middleware class.
    
    Returns:
        RustLoggingMiddleware: The high-performance Rust logging middleware class
    """
    return RustLoggingMiddleware
