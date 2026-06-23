from enum import StrEnum, auto
from typing import Protocol, override, runtime_checkable


@runtime_checkable
class SupportsFormat(Protocol):
    @override
    def __format__(self, format_spec: str, /) -> str: ...


@runtime_checkable
class SupportsWrite[T](Protocol):
    def write(self, s: T, /) -> object: ...


class COLLISION(StrEnum):
    SKIP = auto()
    INCREMENT = auto()
