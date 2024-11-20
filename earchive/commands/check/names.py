from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, IntFlag, StrEnum, auto
from typing import TYPE_CHECKING, Self, cast, override

from earchive.commands.check.config.substitution import RegexPattern
from earchive.utils.path import FastPath

if TYPE_CHECKING:
    pass


class OutputKind(StrEnum):
    silent = auto()
    cli = auto()
    unfixed = auto()
    csv = auto()

    def __init__(self, _: object) -> None:
        self.path_ = None
        super().__init__()

    @classmethod
    @override
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
    @override
    def _missing_(cls, value: object) -> Self:
        if isinstance(value, str):
            try:
                return cls.__members__[value.upper()]
            except KeyError:
                return super()._missing_(value)

        elif isinstance(value, list):
            value = cast(list[str], value)
            chk = cls.NO_CHECK

            for v in value:
                assert isinstance(v, str)
                chk |= cls.__members__[v.upper()]

            return chk

        return super()._missing_(value)


CheckRepr = {Check.EMPTY: "Empty directories", Check.CHARACTERS: "Invalid characters", Check.LENGTH: "Path length"}


class Diagnostic(Enum):
    CHARACTERS = auto()
    INVALID = auto()
    RENAME_INVALID = auto()
    RENAME_MATCH = auto()
    LENGTH_PATH = auto()
    LENGTH_NAME = auto()
    EMPTY = auto()
    ERROR = auto()


@dataclass
class PathDiagnostic(ABC):
    path: FastPath
    kind: Diagnostic


@dataclass
class PathCharactersDiagnostic(PathDiagnostic):
    matches: list[re.Match[str]] = field(kw_only=True)
    kind: Diagnostic = field(init=False, default=Diagnostic.CHARACTERS)


@dataclass
class PathInvalidNameDiagnostic(PathDiagnostic):
    kind: Diagnostic = field(init=False, default=Diagnostic.INVALID)


@dataclass
class PathRenameDiagnostic(PathDiagnostic):
    new_path: FastPath
    patterns: list[tuple[RegexPattern, str]] = field(kw_only=True)
    kind: Diagnostic = field(init=False, default=Diagnostic.RENAME_MATCH)


@dataclass
class PathCharactersReplaceDiagnostic(PathDiagnostic):
    new_path: FastPath
    matches: list[re.Match[str]] = field(kw_only=True)
    kind: Diagnostic = field(init=False, default=Diagnostic.RENAME_INVALID)


@dataclass
class PathLengthDiagnostic(PathDiagnostic):
    kind: Diagnostic = field(init=False, default=Diagnostic.LENGTH_PATH)


@dataclass
class PathFilenameLengthDiagnostic(PathDiagnostic):
    kind: Diagnostic = field(init=False, default=Diagnostic.LENGTH_NAME)


@dataclass
class PathEmptyDiagnostic(PathDiagnostic):
    kind: Diagnostic = field(init=False, default=Diagnostic.EMPTY)


@dataclass
class PathErrorDiagnostic(PathDiagnostic):
    error: Exception = field(kw_only=True)
    kind: Diagnostic = field(init=False, default=Diagnostic.ERROR)
