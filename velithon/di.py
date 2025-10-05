"""Dependency injection system for Velithon framework.

This module provides dependency injection functionality including providers,
container management, and automatic dependency resolution for endpoints.
"""

import logging
from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any

from velithon._velithon import (
    AsyncFactoryProvider,
    FactoryProvider,
    Provide,
    Provider,
    SingletonProvider,
    di_cached_signature,
)
from velithon._velithon import (
    ServiceContainer as _RustServiceContainer,
)
from velithon.ctx import current_app

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Enhanced ServiceContainer with automatic provider registration.

    Uses Rust implementation for high-performance dependency resolution.
    """

    def __init__(self):
        """Initialize the service container with Rust backend."""
        self._rust_container = _RustServiceContainer()
        # Auto-register providers from class attributes (Python compatibility)
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Provider):
                setattr(self, name, value)

    async def resolve(self, provide, container, resolution_stack=None):
        """Delegate to Rust implementation and handle async results."""
        result = self._rust_container.resolve(provide, container, resolution_stack)

        # If the result is a coroutine, await it
        if hasattr(result, '__await__'):
            return await result
        else:
            return result


def inject(func: Callable) -> Callable:
    """High-performance decorator to inject dependencies into functions.

    Features:
    - Rust-cached function signatures for faster introspection
    - Precomputed dependency mappings
    - Optimized resolution through Rust providers
    - Full backward compatibility with original API
    """
    sig = di_cached_signature(func)  # Rust signature caching
    param_deps = []  # Precomputed (name, dependency) pairs

    # Precompute dependency mappings at decoration time for maximum performance
    for name, param in sig.parameters.items():
        provide = None
        if hasattr(param.annotation, '__metadata__'):
            for metadata in param.annotation.__metadata__:
                if isinstance(metadata, Provide):
                    provide = metadata
                    break
        elif isinstance(param.default, Provide):
            provide = param.default

        if provide:
            param_deps.append((name, provide))

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        container = current_app.container
        if not container:
            raise RuntimeError('No container available in Velithon context.')

        # Fast dependency resolution using Rust implementations
        resolved_kwargs = {}
        for name, dep in param_deps:
            if name in kwargs and not isinstance(kwargs[name], Provide):
                resolved_kwargs[name] = kwargs[
                    name
                ]  # User-provided kwargs take precedence
                continue

            try:
                # Use high-performance Rust container resolution
                resolved_kwargs[name] = await container.resolve(dep, container)
            except ValueError as e:
                logger.error(f'Inject error for {name} in {func.__name__}: {e}')
                raise

        kwargs.update(resolved_kwargs)
        return (
            await func(*args, **kwargs)
            if iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

    return wrapper


__all__ = [
    'AsyncFactoryProvider',
    'FactoryProvider',
    'Provide',
    'Provider',
    'ServiceContainer',
    'SingletonProvider',
    'inject',
]
