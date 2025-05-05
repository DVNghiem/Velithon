import logging
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import Any, Callable, Dict, Optional, Type

from velithon.datastructures import Scope

logger = logging.getLogger(__name__)

# Context variable to store the current request scope for dependency injection.
current_scope: ContextVar[Optional[Scope]] = ContextVar("current_scope", default=None)


class Provide:
    """
    Represents a dependency to be injected, referencing a service in the container.

    Supports subscripting (e.g., Provide[container.user_service]) to create instances
    for use in default values or Annotated metadata.

    Attributes:
        service: The provider instance (e.g., container.user_service) to resolve.
    """

    def __init__(self, service: Any):
        """
        Initialize the Provide instance with a service provider.

        Args:
            service: The provider instance (e.g., container.user_service).
        """
        self.service = service

    def __class_getitem__(cls, service: Any) -> "Provide":
        """
        Allow subscripting syntax (e.g., Provide[container.user_service]).

        Args:
            service: The provider instance to reference.

        Returns:
            A new Provide instance for the given service.
        """
        return cls(service)


class Provider:
    """
    Base class for all dependency providers.

    Providers manage the creation and lifecycle of dependencies.
    Subclasses implement specific instantiation strategies (singleton, factory, etc.).
    """

    def __init__(self):
        # Cache for storing instances (used by SingletonProvider).
        self._instances: Dict[str, Any] = {}

    async def get(self, scope: Optional[Scope] = None) -> Any:
        """
        Retrieve or create an instance of the dependency.

        Args:
            scope: The current request scope, providing access to the container.

        Returns:
            The resolved dependency instance.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


class SingletonProvider(Provider):
    """
    Provider that creates a single instance of a class and reuses it for all requests.

    Suitable for dependencies like database connections that should be shared.
    """

    def __init__(self, cls: Type, **kwargs):
        """
        Initialize the provider with a class to instantiate.

        Args:
            cls: The class to instantiate (e.g., Database).
            **kwargs: Dependencies or parameters for the class's __init__.
        """
        super().__init__()
        self.cls = cls
        self.kwargs = kwargs

    async def get(self, scope: Optional[Scope] = None) -> Any:
        """
        Get the singleton instance, creating it if it doesn't exist.

        Args:
            scope: The current request scope, providing access to the container.

        Returns:
            The singleton instance of the class.
        """
        key = f"{self.cls.__name__}"
        if key in self._instances:
            return self._instances[key]
        container = scope._di_context["velithon"].container if scope else None
        instance = await self._create_instance(container, scope)
        self._instances[key] = instance
        return instance

    async def _create_instance(self, container: Any, scope: Optional[Scope]) -> Any:
        """
        Create an instance of the class, resolving its dependencies.

        Args:
            container: The ServiceContainer to resolve dependencies.
            scope: The current request scope.

        Returns:
            The created instance.

        Raises:
            ValueError: If a required parameter cannot be resolved.
        """
        sig = signature(self.cls)
        deps = {}
        for name, param in sig.parameters.items():
            if name in self.kwargs:
                deps[name] = self.kwargs[name]
            elif hasattr(param.annotation, "__metadata__"):
                for metadata in param.annotation.__metadata__:
                    if isinstance(metadata, Provide):
                        deps[name] = await container.resolve(metadata, scope)
            elif isinstance(param.default, Provide):
                deps[name] = await container.resolve(param.default, scope)
            else:
                raise ValueError(
                    f"Cannot resolve parameter {name} for {self.cls.__name__}"
                )
        instance = self.cls(**deps)
        return instance


class FactoryProvider(Provider):
    """
    Provider that creates a new instance of a class each time it is requested.

    Suitable for dependencies like repositories that need fresh instances per request.
    Takes a class (type) to instantiate, using its __init__ method.
    """

    def __init__(self, cls: Type, **kwargs):
        """
        Initialize the provider with a class to instantiate.

        Args:
            cls: The class to instantiate (e.g., UserRepository).
            **kwargs: Dependencies or parameters for the class's __init__.

        Note:
            Unlike AsyncFactoryProvider, FactoryProvider takes a class (type) rather than
            a callable to simplify instantiation of classes with standard __init__ methods.
            This design mirrors SingletonProvider for consistency, differing only in
            creating new instances each time.
        """
        super().__init__()
        self.cls = cls
        self.kwargs = kwargs

    async def get(self, scope: Optional[Scope] = None) -> Any:
        """
        Create and return a new instance of the class.

        Args:
            scope: The current request scope, providing access to the container.

        Returns:
            A new instance of the class.
        """
        container = scope._di_context["velithon"].container if scope else None
        return await self._create_instance(container, scope)

    async def _create_instance(self, container: Any, scope: Optional[Scope]) -> Any:
        """
        Create a new instance of the class, resolving its dependencies.

        Args:
            container: The ServiceContainer to resolve dependencies.
            scope: The current request scope.

        Returns:
            The created instance.

        Raises:
            ValueError: If a required parameter cannot be resolved.
        """
        sig = signature(self.cls)
        deps = {}
        for name, param in sig.parameters.items():
            if name in self.kwargs:
                deps[name] = self.kwargs[name]
            elif hasattr(param.annotation, "__metadata__"):
                for metadata in param.annotation.__metadata__:
                    if isinstance(metadata, Provide):
                        deps[name] = await container.resolve(metadata, scope)
            elif isinstance(param.default, Provide):
                deps[name] = await container.resolve(param.default, scope)
            else:
                raise ValueError(
                    f"Cannot resolve parameter {name} for {self.cls.__name__}"
                )
        instance = self.cls(**deps)
        return instance


class AsyncFactoryProvider(Provider):
    """
    Provider that creates instances using an async callable (factory function).

    Suitable for dependencies requiring async initialization or complex creation logic.
    Takes a callable (e.g., a function) that returns the instance.
    """

    def __init__(self, factory: Callable, **kwargs):
        """
        Initialize the provider with an async factory function.

        Args:
            factory: The async callable that creates the instance (e.g., create_user_service).
            **kwargs: Dependencies or parameters for the factory function.

        Note:
            Unlike FactoryProvider, this takes a callable to support async creation logic,
            allowing for more flexibility in how instances are created (e.g., async DB connections).
        """
        super().__init__()
        self.factory = factory
        self.kwargs = kwargs

    async def get(self, scope: Optional[Scope] = None) -> Any:
        """
        Create and return an instance using the async factory function.

        Args:
            scope: The current request scope, providing access to the container.

        Returns:
            The instance created by the factory.
        """
        container = scope._di_context["velithon"].container if scope else None
        return await self._create_instance(container, scope)

    async def _create_instance(self, container: Any, scope: Optional[Scope]) -> Any:
        """
        Create an instance using the async factory, resolving its dependencies.

        Args:
            container: The ServiceContainer to resolve dependencies.
            scope: The current request scope.

        Returns:
            The created instance.

        Raises:
            ValueError: If a required parameter cannot be resolved.
        """
        sig = signature(self.factory)
        deps = {}
        for name, param in sig.parameters.items():
            if name in self.kwargs:
                deps[name] = self.kwargs[name]
            elif hasattr(param.annotation, "__metadata__"):
                for metadata in param.annotation.__metadata__:
                    if isinstance(metadata, Provide):
                        deps[name] = await container.resolve(metadata, scope)
            elif isinstance(param.default, Provide):
                deps[name] = await container.resolve(param.default, scope)
            else:
                raise ValueError(
                    f"Cannot resolve parameter {name} for {self.factory.__name__}"
                )
        instance = await self.factory(**deps)
        return instance


class ServiceContainer:
    """
    Container for managing dependency providers, similar to Dependency Injector's DeclarativeContainer.

    Providers are defined as class attributes (e.g., db = SingletonProvider(...)).
    The container collects these providers at initialization and allows access via attributes
    (e.g., container.db).
    """

    def __init__(self):
        """
        Initialize the container by collecting providers from class attributes.

        Providers are stored in a dictionary and made accessible as instance attributes.
        """
        self._services: Dict[str, Provider] = {}
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Provider):
                self._services[name] = value
                setattr(self, name, value)

    async def resolve(self, provide: Provide, scope: Optional[Scope] = None) -> Any:
        """
        Resolve a dependency from a Provide instance.

        Args:
            provide: The Provide instance referencing the service to resolve.
            scope: The current request scope.

        Returns:
            The resolved dependency instance.

        Raises:
            ValueError: If the service is not registered in the container.
        """
        service = provide.service
        if not isinstance(service, Provider) or service not in self._services.values():
            raise ValueError(f"No service registered for {service}")
        return await service.get(scope)


def inject(func: Callable) -> Callable:
    """
    Decorator to inject dependencies into a function.

    Inspects the function's signature and resolves dependencies marked with Provide
    using the container in the current scope. Uses @wraps to preserve the original
    function's metadata (e.g., name, docstring, annotations).

    Args:
        func: The function to decorate.

    Returns:
        A wrapped function that resolves dependencies before calling the original.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        scope = current_scope.get()
        if not scope:
            raise RuntimeError("No scope available for dependency injection")
        container = scope._di_context["velithon"].container
        sig = signature(func)
        resolved_kwargs = {}
        for name, param in sig.parameters.items():
            # Prefer to resolve from Annotated or default Provided
            if hasattr(param.annotation, "__metadata__"):
                for metadata in param.annotation.__metadata__:
                    if isinstance(metadata, Provide):
                        try:
                            resolved_kwargs[name] = await container.resolve(
                                metadata, scope
                            )
                        except ValueError as e:
                            logger.error(
                                f"Inject error for {name} in {func.__name__}: {e}"
                            )
                            raise
                        break
            elif isinstance(param.default, Provide):
                try:
                    resolved_kwargs[name] = await container.resolve(
                        param.default, scope
                    )
                except ValueError as e:
                    logger.error(f"Inject error for {name} in {func.__name__}: {e}")
                    raise
            elif param.annotation == Scope:
                resolved_kwargs[name] = scope
            # Only use kwargs if not resolved and not Provide
            elif name in kwargs:
                if isinstance(kwargs[name], Provide):
                    try:
                        resolved_kwargs[name] = await container.resolve(
                            kwargs[name], scope
                        )
                    except ValueError as e:
                        logger.error(
                            f"Inject error for {name} in {func.__name__} from kwargs: {e}"
                        )
                        raise
                else:
                    resolved_kwargs[name] = kwargs[name]
        kwargs.update(resolved_kwargs)
        return (
            await func(*args, **kwargs)
            if iscoroutinefunction(func)
            else func(*args, **kwargs)
        )

    return wrapper
