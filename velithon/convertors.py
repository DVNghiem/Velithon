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
    "str": StringConvertor(),
    "path": PathConvertor(),
    "int": IntegerConvertor(),
    "float": FloatConvertor(),
    "uuid": UUIDConvertor(),
}
