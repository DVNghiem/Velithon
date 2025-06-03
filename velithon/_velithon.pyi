import typing
import uuid
import enum
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

class LogLevel(str, enum.Enum):
    Debug = "DEBUG"
    Info = "INFO"
    Warn = "WARNING"
    Error = "ERROR"
    Critical = "CRITICAL"

    def from_str(cls, s: str) -> "LogLevel":
        ...

    def to_str(self) -> str:
        ...

    def to_int(self)-> int:
        ...

def configure_logger(
    log_file: str | None,
    level: str,
    lof_format: str,
    log_to_file: bool,
    max_bytes: int, 
    backup_count: int,
) -> None:
    ...

def log_debug(
    message: str,
    module: str,
    line: int,
) -> None:
    ...


def log_debug_with_extra(
    message: str,
    module: str,
    line: int,
    extra: typing.Dict[str, typing.Any],
) -> None:
    ...


def log_info(
    message: str,
    module: str,
    line: int,
) -> None:
    ...

def log_info_with_extra(
    message: str,
    module: str,
    line: int,
    extra: typing.Dict[str, typing.Any],
) -> None:
    ...

def log_warn(
    message: str,
    module: str,
    line: int,
) -> None:
    ...


def log_warn_with_extra(
    message: str,
    module: str,
    line: int,
    extra: typing.Dict[str, typing.Any],
) -> None:
    ...

def log_error(
    message: str,
    module: str,
    line: int,
) -> None:
    ...

def log_error_with_extra(
    message: str,
    module: str,
    line: int,
    extra: typing.Dict[str, typing.Any],
) -> None:
    ...

def log_critical(
    message: str,
    module: str,
    line: int,
) -> None:
    ...

def log_critical_with_extra(
    message: str,
    module: str,
    line: int,
    extra: typing.Dict[str, typing.Any],
) -> None:
    ...

def is_enabled_for(level: str) -> bool:
    ...


