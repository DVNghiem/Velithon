"""Type convertors for URL path parameters in Velithon framework.

This module provides type convertor classes for converting URL path parameters
to appropriate Python types (int, float, string, path, UUID).
"""

from __future__ import annotations

import typing

from ._velithon import (
    Convertor,
    FloatConvertor,
    IntegerConvertor,
    PathConvertor,
    StringConvertor,
    UUIDConvertor,
)

CONVERTOR_TYPES: dict[str, Convertor[typing.Any]] = {
    'str': StringConvertor(),
    'path': PathConvertor(),
    'int': IntegerConvertor(),
    'float': FloatConvertor(),
    'uuid': UUIDConvertor(),
}
