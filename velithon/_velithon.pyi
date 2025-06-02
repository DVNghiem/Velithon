import typing
import uuid
from dataclasses import dataclass

@dataclass(frozen=True)
class Convertor:
    regex: str

    def convert(self, value: str) -> typing.Any: ...
    def to_string(self, value: typing.Any) -> str: ...

@dataclass(frozen=True)
class StringConvertor(Convertor):
    regex = ".*"

    def convert(self, value: str) -> str: ...
    def to_string(self, value: str) -> str: ...

@dataclass(frozen=True)
class PathConvertor(Convertor):
    regex = ".*"

    def convert(self, value: str) -> str: ...
    def to_string(self, value: str) -> str: ...

@dataclass(frozen=True)
class IntegerConvertor(Convertor):
    regex = "[0-9]+"

    def convert(self, value: str) -> int: ...
    def to_string(self, value: int) -> str: ...

@dataclass(frozen=True)
class FloatConvertor(Convertor):
    regex = r"[0-9]+(\.[0-9]+)?"

    def convert(self, value: str) -> float: ...
    def to_string(self, value: float) -> str: ...

@dataclass(frozen=True)
class UUIDConvertor(Convertor):
    regex = (
        "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    def convert(self, value: str) -> uuid.UUID: ...
    def to_string(self, value: uuid.UUID) -> str: ...

def compile_path(
    path: str, convertor_types: typing.Dict[str, Convertor]
) -> typing.Tuple[str, str, typing.Dict[str, Convertor]]:
    # This function would compile a path using the provided convertor types.
    # The implementation is not provided in the original code snippet.
    ...

@dataclass(frozen=True)
class ResponseCache:
    max_size: int
    cache: typing.Dict[str, typing.Any]
    access_order: typing.List[str]

    def get(self, key: str) -> typing.Optional[typing.Any]:
        ...

    def put(self, key: str, value: typing.Any) -> None:
        ...


def di_cached_signature(func: typing.Callable) -> typing.Any:
    pass