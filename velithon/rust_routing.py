"""
Legacy compatibility module for Rust routing

This module now simply re-exports from the main routing module,
which has been enhanced with Rust optimizations.
"""

# Re-export everything from the main routing module
from velithon.routing import *

# Legacy aliases for backwards compatibility
RustOptimizedRoute = Route
RustOptimizedRouter = Router
HighPerformanceRouter = Router
