"""Performance configuration for Velithon framework.

This module provides easy configuration options for optimizing Velithon's performance
based on different use cases and requirements.
"""

import os
from .memory_management import (
    enable_memory_optimizations,
    disable_memory_optimizations,
    set_lightweight_mode,
)


class PerformanceConfig:
    """Configure Velithon's performance settings."""

    # Performance modes
    MAXIMUM_PERFORMANCE = 'maximum'
    HIGH_PERFORMANCE = 'high'
    BALANCED = 'balanced'
    MEMORY_OPTIMIZED = 'memory'

    @staticmethod
    def configure_for_production():
        """Configure Velithon for production use (high performance)."""
        enable_memory_optimizations(lightweight=True)

    @staticmethod
    def configure_for_maximum_performance():
        """Configure Velithon for absolute maximum performance (no memory management)."""
        disable_memory_optimizations()

    @staticmethod
    def configure_for_memory_intensive():
        """Configure Velithon for memory-intensive applications."""
        enable_memory_optimizations(lightweight=False)

    @staticmethod
    def configure_from_environment():
        """Configure performance based on environment variables."""
        mode = os.environ.get('VELITHON_PERFORMANCE_MODE', 'high').lower()

        if mode == PerformanceConfig.MAXIMUM_PERFORMANCE:
            PerformanceConfig.configure_for_maximum_performance()
        elif mode == PerformanceConfig.HIGH_PERFORMANCE:
            PerformanceConfig.configure_for_production()
        elif mode == PerformanceConfig.MEMORY_OPTIMIZED:
            PerformanceConfig.configure_for_memory_intensive()
        else:  # balanced
            enable_memory_optimizations(lightweight=True)


def configure_performance(mode: str = 'high'):
    """Configure Velithon performance mode.

    Args:
        mode: Performance mode - "maximum", "high", "balanced", or "memory"
    """
    if mode == 'maximum':
        PerformanceConfig.configure_for_maximum_performance()
    elif mode == 'high':
        PerformanceConfig.configure_for_production()
    elif mode == 'memory':
        PerformanceConfig.configure_for_memory_intensive()
    else:  # balanced
        enable_memory_optimizations(lightweight=True)


# Auto-configure based on environment variable if set
_auto_mode = os.environ.get('VELITHON_PERFORMANCE_MODE')
if _auto_mode:
    configure_performance(_auto_mode.lower())
