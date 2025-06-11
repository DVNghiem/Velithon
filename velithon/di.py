import logging
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Optional

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
from velithon.datastructures import Scope

logger = logging.getLogger(__name__)

# Context variable to store the current request scope for dependency injection.
current_scope: ContextVar[Optional[Scope]] = ContextVar("current_scope", default=None)


class ServiceContainer:
    """
    Enhanced ServiceContainer with automatic provider registration.
    Uses Rust implementation for high-performance dependency resolution.
    """

    def __init__(self):
        self._rust_container = _RustServiceContainer()
        # Auto-register providers from class attributes (Python compatibility)
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Provider):
                setattr(self, name, value)

    async def resolve(self, provide, scope=None, resolution_stack=None):
        """Delegate to Rust implementation and handle async results"""
        result = self._rust_container.resolve(provide, scope, resolution_stack)

        # If the result is a coroutine, await it
        if hasattr(result, "__await__"):
            return await result
        else:
            return result


def inject(func: Callable) -> Callable:
    """
    High-performance decorator to inject dependencies into functions.

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
        if hasattr(param.annotation, "__metadata__"):
            for metadata in param.annotation.__metadata__:
                if isinstance(metadata, Provide):
                    provide = metadata
                    break
        elif isinstance(param.default, Provide):
            provide = param.default

        if provide:
            param_deps.append((name, provide))
        elif param.annotation == Scope:
            param_deps.append((name, Scope))

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        scope = current_scope.get()
        if scope is None:
            raise RuntimeError("No scope available for dependency injection")

        container = scope._di_context.get("velithon", {}).container
        if not container:
            raise RuntimeError(
                "No container available in scope._di_context['velithon']"
            )

        # Fast dependency resolution using Rust implementations
        resolved_kwargs = {}
        for name, dep in param_deps:
            if name in kwargs and not isinstance(kwargs[name], Provide):
                resolved_kwargs[name] = kwargs[
                    name
                ]  # User-provided kwargs take precedence
                continue

            if dep is Scope:
                resolved_kwargs[name] = scope
            else:
                try:
                    # Use high-performance Rust container resolution
                    resolved_kwargs[name] = await container.resolve(dep, scope)
                except ValueError as e:
                    logger.error(f"Inject error for {name} in {func.__name__}: {e}")
                    raise

        kwargs.update(resolved_kwargs)
        return (
            await func(*args, **kwargs)
            if iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

    return wrapper


__all__ = [
    "ServiceContainer",
    "inject",
    "Provide",
    "Provider",
    "SingletonProvider",
    "FactoryProvider",
    "AsyncFactoryProvider",
    "current_scope",
]
