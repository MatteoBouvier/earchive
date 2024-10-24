import re
from enum import Enum, IntFlag, StrEnum, auto
from pathlib import Path
from typing import NamedTuple

from earchive.check.parse_config import FS, Config, RegexPattern


class OutputKind(StrEnum):
    silent = auto()
    cli = auto()
    csv = auto()


class CTX(NamedTuple):
    config: Config
    fs: FS


class Check(IntFlag):
    NO_CHECK = 0
    EMPTY = auto()
    CHARACTERS = auto()
    LENGTH = auto()


class Action(Enum):
    RENAME = auto()


type Diagnostic = Check | Action


class PathDiagnostic(NamedTuple):
    kind: Diagnostic
    path: Path
    matches: list[re.Match[str]] | None = None
    patterns: list[tuple[RegexPattern, str]] | None = None
    new_path: Path | None = None
