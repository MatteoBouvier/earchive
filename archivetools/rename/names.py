import re
from enum import IntFlag, auto
from pathlib import Path
from typing import Literal, NamedTuple

from archivetools.rename.parse_config import OS, Config


class CTX(NamedTuple):
    config: Config
    os: OS


class Check(IntFlag):
    EMPTY = auto()
    CHARACTERS = auto()
    LENGTH = auto()


INVALID_PATH_CHR = tuple[Literal[Check.CHARACTERS], Path, list[re.Match[str]]]
INVALID_PATH_LEN = tuple[Literal[Check.LENGTH], Path]
INVALID_PATH_EMPTY = tuple[Literal[Check.EMPTY], Path]
INVALID_PATH_DATA = INVALID_PATH_CHR | INVALID_PATH_LEN | INVALID_PATH_EMPTY
