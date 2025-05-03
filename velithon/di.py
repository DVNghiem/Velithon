import asyncio
import contextvars
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type

from velithon.datastructures import Scope

current_scope = contextvars.ContextVar("current_scope", default=None)


class Lifecycle(Enum):
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


class Provide:
    def __init__(self, cls: Type):
        self.cls = cls


class Container:
    def __init__(self):
        self.registry: Dict[Type, tuple[Callable, Lifecycle]] = {}
        self.singletons: Dict[Type, Any] = {}
        self.scoped_contexts: Dict[str, Dict[Type, Any]] = {}

    def register(
        self,
        cls: Type,
        factory: Callable = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ):
        factory = factory or cls
        self.registry[cls] = (factory, lifecycle)

    async def resolve(self, cls: Type, scope: Optional[Scope] = None) -> Any:
        if cls not in self.registry:
            raise ValueError(f"No dependency registered for {cls}")

        factory, lifecycle = self.registry[cls]

        if lifecycle == Lifecycle.SINGLETON:
            if cls not in self.singletons:
                self.singletons[cls] = await self._create_instance(factory, scope)
            return self.singletons[cls]

        elif lifecycle == Lifecycle.SCOPED:
            if not scope:
                scope = current_scope.get()
                if not scope or not hasattr(scope, "_di_context"):
                    raise RuntimeError("Scoped dependency requires a request scope")
            request_id = scope.request_id
            if request_id not in self.scoped_contexts:
                self.scoped_contexts[request_id] = {}
            if cls not in self.scoped_contexts[request_id]:
                self.scoped_contexts[request_id][cls] = await self._create_instance(
                    factory, scope
                )
            return self.scoped_contexts[request_id][cls]

        else:  # TRANSIENT
            return await self._create_instance(factory, scope)

    async def _create_instance(self, factory: Callable, scope: Optional[Scope]) -> Any:
        if asyncio.iscoroutinefunction(factory):
            return await factory(scope=scope)
        return factory()

    def cleanup_scope(self, request_id: str):
        self.scoped_contexts.pop(request_id, None)


def inject(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        scope = current_scope.get()
        if scope is None or not hasattr(scope, "_di_context"):
            raise RuntimeError(
                "Provide requires a scope (pass scope or call within request)"
            )

        container = scope._di_context.get("velithon").container
        resolved_kwargs = {}

        for param_name in func.__code__.co_varnames[: func.__code__.co_argcount]:
            defaults = func.__defaults__ or ()
            default_idx = len(func.__code__.co_varnames) - len(defaults)
            if param_name in func.__code__.co_varnames[default_idx:]:
                default_value = defaults[
                    func.__code__.co_varnames.index(param_name) - default_idx
                ]
                if isinstance(default_value, Provide):
                    resolved_kwargs[param_name] = await container.resolve(
                        default_value.cls, scope
                    )

        annotations = getattr(func, "__annotations__", {})
        for name, annotation in annotations.items():
            if name not in kwargs and name != "return" and name not in resolved_kwargs:
                if isinstance(annotation, Provide):
                    resolved_kwargs[name] = await container.resolve(
                        annotation.cls, scope
                    )
                elif isinstance(annotation, type):
                    resolved_kwargs[name] = await container.resolve(annotation, scope)

        context = contextvars.copy_context()
        token = current_scope.set(scope)
        kwargs.update(resolved_kwargs)
        try:
            return await context.run(func, *args, **kwargs)
        finally:
            current_scope.reset(token)

    return wrapper
