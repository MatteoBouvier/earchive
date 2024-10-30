from __future__ import annotations

import re
from enum import Enum, IntFlag, StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Self

if TYPE_CHECKING:
    from earchive.check.config import RegexPattern


class OutputKind(StrEnum):
    silent = auto()
    cli = auto()
    csv = auto()

    def __init__(self, _: object) -> None:
        self.path_ = None
        super().__init__()

    @classmethod
    def _missing_(cls, value: object) -> Self:
        if isinstance(value, str) and value.startswith("csv="):
            kind = cls("csv")
            kind.path_ = value[4:]
            return kind
        return super()._missing_(value)


class Check(IntFlag):
    NO_CHECK = 0
    EMPTY = auto()
    CHARACTERS = auto()
    LENGTH = auto()

    @classmethod
    def _missing_(cls, value: object) -> Self:
        if isinstance(value, str):
            try:
                return cls.__members__[value.upper()]
            except KeyError:
                return super()._missing_(value)

        return super()._missing_(value)


CheckRepr = {Check.EMPTY: "Empty directories", Check.CHARACTERS: "Invalid characters", Check.LENGTH: "Path length"}


class Action(Enum):
    ERROR = auto()
    RENAME = auto()


type Diagnostic = Check | Action


class PathDiagnostic(NamedTuple):
    kind: Diagnostic
    path: Path
    matches: list[re.Match[str]] | None = None
    patterns: list[tuple[RegexPattern, str]] | None = None
    new_path: Path | None = None
    error: Exception | None = None
