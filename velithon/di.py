import logging
from asyncio import Lock
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Optional, Type

from ._velithon import di_cached_signature

from velithon.datastructures import Scope

logger = logging.getLogger(__name__)

# Context variable to store the current request scope for dependency injection.
current_scope: ContextVar[Optional[Scope]] = ContextVar("current_scope", default=None)


class Provide:
    """Represents a dependency to be injected, referencing a service in the container."""

    def __init__(self, service: Any):
        self.service = service

    def __class_getitem__(cls, service: Any) -> "Provide":
        return cls(service)


class Provider:
    """Base class for all dependency providers."""

    def __init__(self):
        self._instances: Dict[str, Any] = {}

    async def get(
        self, scope: Optional[Scope] = None, resolution_stack: Optional[set] = None
    ) -> Any:
        """
        Retrieve or create an instance of the dependency.
        Added resolution_stack to detect circular dependencies.
        """
        raise NotImplementedError


class SingletonProvider(Provider):
    """Provider that creates and reuses a single instance of a class."""

    def __init__(self, cls: Type, **kwargs):
        super().__init__()
        self.cls = cls
        self.kwargs = kwargs
        self._lock = Lock()  # Add lock for thread-safety

    async def get(
        self, scope: Optional[Scope] = None, resolution_stack: Optional[set] = None
    ) -> Any:
        key = f"{self.cls.__name__}"
        if key in self._instances:
            return self._instances[key]

        async with self._lock:  # Ensure thread-safety for singleton creation
            if key in self._instances:  # Double-check after acquiring lock
                return self._instances[key]

            if resolution_stack is None:
                resolution_stack = set()
            if key in resolution_stack:
                raise ValueError(
                    f"Circular dependency detected for {self.cls.__name__}"
                )
            resolution_stack.add(key)

            try:
                container = self._get_container(scope)
                instance = await self._create_instance(
                    container, scope, resolution_stack
                )
                self._instances[key] = instance
                return instance
            finally:
                resolution_stack.discard(key)

    async def _create_instance(
        self, container: Any, scope: Optional[Scope], resolution_stack: set
    ) -> Any:
        sig = di_cached_signature(self.cls)  # Use cached signature
        deps = await self._resolve_dependencies(sig, container, scope, resolution_stack)
        return self.cls(**deps)

    async def _resolve_dependencies(
        self, sig: Any, container: Any, scope: Optional[Scope], resolution_stack: set
    ) -> Dict[str, Any]:
        deps = {}
        for name, param in sig.parameters.items():
            dep = await self._resolve_param(
                name, param, container, scope, resolution_stack
            )
            if dep is not None:
                deps[name] = dep
        return deps

    async def _resolve_param(
        self,
        name: str,
        param: Any,
        container: Any,
        scope: Optional[Scope],
        resolution_stack: set,
    ) -> Any:
        if name in self.kwargs:
            return self.kwargs[name]
        if hasattr(param.annotation, "__metadata__"):
            for metadata in param.annotation.__metadata__:
                if isinstance(metadata, Provide):
                    return await container.resolve(metadata, scope, resolution_stack)
        if isinstance(param.default, Provide):
            return await container.resolve(param.default, scope, resolution_stack)
        raise ValueError(f"Cannot resolve parameter {name} for {self.cls.__name__}")

    def _get_container(self, scope: Optional[Scope]) -> Any:
        if (
            not scope
            or not hasattr(scope, "_di_context")
            or "velithon" not in scope._di_context
        ):
            raise RuntimeError(
                "Invalid scope or missing container in scope._di_context['velithon']"
            )
        return scope._di_context["velithon"].container


class FactoryProvider(Provider):
    """Provider that creates a new instance of a class each time."""

    def __init__(self, cls: Type, **kwargs):
        super().__init__()
        self.cls = cls
        self.kwargs = kwargs
        self._signature = di_cached_signature(cls)  # Cache signature at initialization

    async def get(
        self, scope: Optional[Scope] = None, resolution_stack: Optional[set] = None
    ) -> Any:
        if resolution_stack is None:
            resolution_stack = set()
        key = f"{self.cls.__name__}"
        if key in resolution_stack:
            raise ValueError(f"Circular dependency detected for {self.cls.__name__}")
        resolution_stack.add(key)

        try:
            container = self._get_container(scope)
            return await self._create_instance(container, scope, resolution_stack)
        finally:
            resolution_stack.discard(key)

    async def _create_instance(
        self, container: Any, scope: Optional[Scope], resolution_stack: set
    ) -> Any:
        deps = await self._resolve_dependencies(
            self._signature, container, scope, resolution_stack
        )
        return self.cls(**deps)

    async def _resolve_dependencies(
        self, sig: Any, container: Any, scope: Optional[Scope], resolution_stack: set
    ) -> Dict[str, Any]:
        deps = {}
        for name, param in sig.parameters.items():
            dep = await self._resolve_param(
                name, param, container, scope, resolution_stack
            )
            if dep is not None:
                deps[name] = dep
        return deps

    async def _resolve_param(
        self,
        name: str,
        param: Any,
        container: Any,
        scope: Optional[Scope],
        resolution_stack: set,
    ) -> Any:
        if name in self.kwargs:
            return self.kwargs[name]
        if hasattr(param.annotation, "__metadata__"):
            for metadata in param.annotation.__metadata__:
                if isinstance(metadata, Provide):
                    return await container.resolve(metadata, scope, resolution_stack)
        if isinstance(param.default, Provide):
            return await container.resolve(param.default, scope, resolution_stack)
        raise ValueError(f"Cannot resolve parameter {name} for {self.cls.__name__}")

    def _get_container(self, scope: Optional[Scope]) -> Any:
        if (
            not scope
            or not hasattr(scope, "_di_context")
            or "velithon" not in scope._di_context
        ):
            raise RuntimeError(
                "Invalid scope or missing container in scope._di_context['velithon']"
            )
        return scope._di_context["velithon"].container


class AsyncFactoryProvider(Provider):
    """Provider that creates instances using an async callable."""

    def __init__(self, factory: Callable, **kwargs):
        super().__init__()
        self.factory = factory
        self.kwargs = kwargs
        self._signature = di_cached_signature(factory)  # Cache signature at initialization

    async def get(
        self, scope: Optional[Scope] = None, resolution_stack: Optional[set] = None
    ) -> Any:
        if resolution_stack is None:
            resolution_stack = set()
        key = f"{self.factory.__name__}"
        if key in resolution_stack:
            raise ValueError(
                f"Circular dependency detected for {self.factory.__name__}"
            )
        resolution_stack.add(key)

        try:
            container = self._get_container(scope)
            return await self._create_instance(container, scope, resolution_stack)
        finally:
            resolution_stack.discard(key)

    async def _create_instance(
        self, container: Any, scope: Optional[Scope], resolution_stack: set
    ) -> Any:
        deps = await self._resolve_dependencies(
            self._signature, container, scope, resolution_stack
        )
        return await self.factory(**deps)

    async def _resolve_dependencies(
        self, sig: Any, container: Any, scope: Optional[Scope], resolution_stack: set
    ) -> Dict[str, Any]:
        deps = {}
        for name, param in sig.parameters.items():
            dep = await self._resolve_param(
                name, param, container, scope, resolution_stack
            )
            if dep is not None:
                deps[name] = dep
        return deps

    async def _resolve_param(
        self,
        name: str,
        param: Any,
        container: Any,
        scope: Optional[Scope],
        resolution_stack: set,
    ) -> Any:
        if name in self.kwargs:
            return self.kwargs[name]
        if hasattr(param.annotation, "__metadata__"):
            for metadata in param.annotation.__metadata__:
                if isinstance(metadata, Provide):
                    return await container.resolve(metadata, scope, resolution_stack)
        if isinstance(param.default, Provide):
            return await container.resolve(param.default, scope, resolution_stack)
        raise ValueError(f"Cannot resolve parameter {name} for {self.factory.__name__}")

    def _get_container(self, scope: Optional[Scope]) -> Any:
        if (
            not scope
            or not hasattr(scope, "_di_context")
            or "velithon" not in scope._di_context
        ):
            raise RuntimeError(
                "Invalid scope or missing container in scope._di_context['velithon']"
            )
        return scope._di_context["velithon"].container


class ServiceContainer:
    """Container for managing dependency providers."""

    def __init__(self):
        self._services: Dict[str, Provider] = {}
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Provider):
                self._services[name] = value
                setattr(self, name, value)

    async def resolve(
        self,
        provide: Provide,
        scope: Optional[Scope] = None,
        resolution_stack: Optional[set] = None,
    ) -> Any:
        service = provide.service
        if not isinstance(service, Provider) or service not in self._services.values():
            raise ValueError(f"No service registered for {service}")
        return await service.get(scope, resolution_stack)


def inject(func: Callable) -> Callable:
    """Decorator to inject dependencies into a function with precomputed dependency mappings."""
    sig = di_cached_signature(func)  # Cache signature at decoration time
    param_deps = []  # List of (name, Provide) for parameters with dependencies

    # Precompute dependency mappings - use original approach for maximum compatibility
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

        # Resolve dependencies
        resolved_kwargs = {}
        for name, dep in param_deps:
            if name in kwargs and not isinstance(kwargs[name], Provide):
                resolved_kwargs[name] = kwargs[name]  # Prefer user-provided kwargs
                continue
            if dep is Scope:
                resolved_kwargs[name] = scope
            else:
                try:
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
