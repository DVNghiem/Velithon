from __future__ import annotations

import typing

from ._velithon import (
    Convertor,
    StringConvertor,
    PathConvertor,
    IntegerConvertor,
    FloatConvertor,
    UUIDConvertor,
)


CONVERTOR_TYPES: dict[str, Convertor[typing.Any]] = {
    "str": StringConvertor(),
    "path": PathConvertor(),
    "int": IntegerConvertor(),
    "float": FloatConvertor(),
    "uuid": UUIDConvertor(),
}
