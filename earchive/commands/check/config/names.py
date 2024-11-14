from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path
from typing import Any, Self, override

from earchive.commands.check.config.substitution import RegexPattern
from earchive.commands.check.names import Check
from earchive.utils.fs import FS
from earchive.utils.os import OS


class HEADER(StrEnum):
    NO_HEADER = ""
    BEHAVIOR = auto()
    BEHAVIOR_COLLISION = auto()
    CHECK = auto()
    CHECK_RUN = auto()
    CHECK_PATH = auto()
    CHECK_OPERATING_SYSTEM = auto()
    CHECK_FILE_SYSTEM = auto()
    CHECK_BASE_PATH_LENGTH = auto()
    CHECK_MAX_PATH_LENGTH = auto()
    CHECK_MAX_NAME_LENGTH = auto()
    CHECK_CHARACTERS = auto()
    CHECK_CHARACTERS_EXTRA_INVALID = auto()
    CHECK_CHARACTERS_REPLACEMENT = auto()
    CHECK_CHARACTERS_ASCII = auto()
    RENAME = auto()
    EXCLUDE = auto()

    @override
    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        if isinstance(value, str):
            try:
                return cls.__members__[value.replace(":", "_").upper()]
            except KeyError:
                return None

        return None

    @override
    def __add__(self, other: object) -> HEADER:
        assert isinstance(other, str)
        if self is HEADER.NO_HEADER:
            return HEADER(other)

        return HEADER(f"{self.name}:{other}")


class ASCII(StrEnum):
    STRICT = auto()
    PRINT = auto()
    ACCENTS = auto()
    NO = auto()


class COLLISION(StrEnum):
    SKIP = auto()
    INCREMENT = auto()


@dataclass
class BEHAVIOR_CONFIG:
    collision: COLLISION

    def to_dict(self) -> dict[str, Any]:
        return dict(collision=self.collision)


@dataclass
class CHECK_CHARACTERS_CONFIG:
    extra_invalid: re.Pattern[str]
    replacement: str
    ascii: ASCII

    def to_dict(self) -> dict[str, Any]:
        return dict(
            extra_invalid=self.extra_invalid,
            replacement=self.replacement,
            ascii=self.ascii,
        )


@dataclass
class CHECK_CONFIG:
    run: Check
    path: Path
    operating_system: OS
    file_system: FS
    base_path_length: int
    max_path_length: int
    max_name_length: int
    characters: CHECK_CHARACTERS_CONFIG

    def to_dict(self) -> dict[str, Any]:
        return dict(
            run=self.run,
            path=self.path,
            operating_system=self.operating_system,
            file_system=self.file_system,
            base_path_length=self.base_path_length,
            max_path_length=self.max_path_length,
            max_name_length=self.max_name_length,
            characters=self.characters.to_dict(),
        )


@dataclass
class ConfigDict:
    behavior: BEHAVIOR_CONFIG
    check: CHECK_CONFIG
    rename: list[RegexPattern]
    exclude: list[Path]