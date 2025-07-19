"""Memory-optimized parameter classes for Velithon framework.

This module provides memory-efficient parameter classes using __slots__ optimization
and reduced code duplication. The classes are designed for minimal memory usage
while maintaining full functionality for HTTP parameter handling.
"""

from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

_Unset: Any = PydanticUndefined

# Memory-optimized constants for parameter types (more efficient than Enum)
_PARAM_QUERY = 'query'
_PARAM_HEADER = 'header'
_PARAM_PATH = 'path'
_PARAM_COOKIE = 'cookie'

# Memory-optimized constants for media types (string interning)
_MEDIA_JSON = 'application/json'
_MEDIA_FORM = 'application/x-www-form-urlencoded'
_MEDIA_MULTIPART = 'multipart/form-data'


# Memory-optimized parameter creation helper with reduced overhead
def _create_kwargs_dict(
    default: Any = ...,
    default_factory: Callable[[], Any] | None = _Unset,
    annotation: Any | None = None,
    alias: str | None = None,
    alias_priority: int | None = _Unset,
    validation_alias: str | None = None,
    serialization_alias: str | None = None,
    title: str | None = None,
    description: str | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    discriminator: str | None = None,
    strict: bool | None = _Unset,
    multiple_of: float | None = _Unset,
    allow_inf_nan: bool | None = _Unset,
    max_digits: int | None = _Unset,
    decimal_places: int | None = _Unset,
    examples: list[Any] | None = None,
    json_schema_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create kwargs dictionary with minimal memory overhead, filtering _Unset."""
    # Pre-allocate result dict for efficiency
    result = {}

    # Only add non-_Unset values to minimize memory usage
    if default is not _Unset:
        result['default'] = default
    if default_factory is not _Unset:
        result['default_factory'] = default_factory
    if annotation is not None:
        result['annotation'] = annotation
    if alias is not None:
        result['alias'] = alias
    if alias_priority is not _Unset:
        result['alias_priority'] = alias_priority
    if validation_alias is not None:
        result['validation_alias'] = validation_alias
    if serialization_alias is not None:
        result['serialization_alias'] = serialization_alias
    if title is not None:
        result['title'] = title
    if description is not None:
        result['description'] = description
    if gt is not None:
        result['gt'] = gt
    if ge is not None:
        result['ge'] = ge
    if lt is not None:
        result['lt'] = lt
    if le is not None:
        result['le'] = le
    if min_length is not None:
        result['min_length'] = min_length
    if max_length is not None:
        result['max_length'] = max_length
    if pattern is not None:
        result['pattern'] = pattern
    if discriminator is not None:
        result['discriminator'] = discriminator
    if strict is not _Unset:
        result['strict'] = strict
    if multiple_of is not _Unset:
        result['multiple_of'] = multiple_of
    if allow_inf_nan is not _Unset:
        result['allow_inf_nan'] = allow_inf_nan
    if max_digits is not _Unset:
        result['max_digits'] = max_digits
    if decimal_places is not _Unset:
        result['decimal_places'] = decimal_places
    if examples is not None:
        result['examples'] = examples
    if json_schema_extra is not None:
        result['json_schema_extra'] = json_schema_extra

    return result


class ParamTypes(Enum):
    """Enum for HTTP parameter types with memory-efficient string values."""

    __slots__ = ()  # Memory optimization for enum

    query = _PARAM_QUERY
    header = _PARAM_HEADER
    path = _PARAM_PATH
    cookie = _PARAM_COOKIE


class Param(FieldInfo):
    """Base parameter class with memory optimizations using __slots__."""

    __slots__ = ('convert_underscores', 'in_', 'include_in_schema')

    in_: ParamTypes

    def __init__(
        self,
        default: Any = ...,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | None = None,
        serialization_alias: str | None = None,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
        convert_underscores: bool = True,
    ):
        """Initialize parameter with memory-optimized processing."""
        # Direct assignment to minimize function calls
        object.__setattr__(self, 'include_in_schema', include_in_schema)
        object.__setattr__(self, 'convert_underscores', convert_underscores)

        # Use the memory-efficient kwargs creation helper
        super().__init__(
            **_create_kwargs_dict(
                default,
                default_factory,
                annotation,
                alias,
                alias_priority,
                validation_alias,
                serialization_alias,
                title,
                description,
                gt,
                ge,
                lt,
                le,
                min_length,
                max_length,
                pattern,
                discriminator,
                strict,
                multiple_of,
                allow_inf_nan,
                max_digits,
                decimal_places,
                examples,
                json_schema_extra,
            )
        )

    def __repr__(self) -> str:
        """Return memory-efficient string representation."""
        return f'{self.__class__.__name__}({self.default})'


class Path(Param):
    """Path parameter class with memory optimization."""

    __slots__ = ()  # Inherit slots from parent

    in_ = ParamTypes.path

    def __init__(
        self,
        default: Any = ...,
        **kwargs: Any,
    ):
        """Initialize path parameter with validation."""
        assert default is ..., 'Path parameters cannot have a default value'
        # Remove convert_underscores from kwargs as it's not applicable to paths
        kwargs.pop('convert_underscores', None)
        super().__init__(default=default, convert_underscores=False, **kwargs)


class Query(Param):
    """Query parameter class with memory optimization."""

    __slots__ = ()  # Inherit slots from parent

    in_ = ParamTypes.query

    def __init__(self, default: Any = ..., **kwargs: Any):
        """Initialize query parameter."""
        super().__init__(default=default, **kwargs)


class Header(Param):
    """Header parameter class with memory optimization."""

    __slots__ = ()  # Inherit slots from parent

    in_ = ParamTypes.header

    def __init__(self, default: Any = ..., **kwargs: Any):
        """Initialize header parameter."""
        super().__init__(default=default, **kwargs)


class Cookie(Param):
    """Cookie parameter class with memory optimization."""

    __slots__ = ()  # Inherit slots from parent

    in_ = ParamTypes.cookie

    def __init__(self, default: Any = ..., **kwargs: Any):
        """Initialize cookie parameter."""
        super().__init__(default=default, **kwargs)


class Body(FieldInfo):
    """Body parameter class with memory optimization using __slots__."""

    __slots__ = ('embed', 'include_in_schema', 'media_type')

    def __init__(
        self,
        default: Any = ...,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        embed: bool | None = None,
        media_type: str = _MEDIA_JSON,
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | None = None,
        serialization_alias: str | None = None,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
    ):
        """Initialize body parameter with memory-optimized processing."""
        # Direct assignment to minimize function calls
        object.__setattr__(self, 'embed', embed)
        object.__setattr__(self, 'media_type', media_type)
        object.__setattr__(self, 'include_in_schema', include_in_schema)

        # Use the memory-efficient kwargs creation helper
        super().__init__(
            **_create_kwargs_dict(
                default,
                default_factory,
                annotation,
                alias,
                alias_priority,
                validation_alias,
                serialization_alias,
                title,
                description,
                gt,
                ge,
                lt,
                le,
                min_length,
                max_length,
                pattern,
                discriminator,
                strict,
                multiple_of,
                allow_inf_nan,
                max_digits,
                decimal_places,
                examples,
                json_schema_extra,
            )
        )

    def __repr__(self) -> str:
        """Return memory-efficient string representation."""
        return f'{self.__class__.__name__}({self.default})'


class Form(Body):
    """Form parameter class with memory optimization."""

    __slots__ = ()  # Inherit slots from parent

    def __init__(
        self,
        default: Any = ...,
        *,
        media_type: str = _MEDIA_FORM,
        **kwargs: Any,
    ):
        """Initialize form parameter."""
        super().__init__(default=default, media_type=media_type, **kwargs)


class File(Form):
    """File parameter class with memory optimization."""

    __slots__ = ()  # Inherit slots from parent

    def __init__(
        self,
        default: Any = ...,
        *,
        media_type: str = _MEDIA_MULTIPART,
        **kwargs: Any,
    ):
        """Initialize file parameter."""
        super().__init__(default=default, media_type=media_type, **kwargs)
