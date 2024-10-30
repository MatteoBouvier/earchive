from __future__ import annotations

from enum import StrEnum, auto
from typing import NamedTuple, Self

from earchive.check.enum import StrNestedEnum, nested
from earchive.check.names import Check


class FS(StrEnum):
    AUTO = auto()
    WINDOWS = auto()


class HEADER(StrNestedEnum):
    CHECK = auto()
    CHECK_RUN = nested("CHECK")
    CHECK_FILE_SYSTEM = nested("CHECK")
    CHECK_BASE_PATH_LENGTH = nested("CHECK")
    CHECK_CHARACTERS = nested("CHECK")
    FILE_SYSTEMS = auto()
    RENAME = auto()
    EXCLUDE = auto()

    @classmethod
    def _missing_(cls, value: object) -> Self:
        if isinstance(value, str):
            try:
                return cls.__members__[value.replace(":", "_").upper()]
            except KeyError:
                return super()._missing_(value)
        return super()._missing_(value)


class CHECK_CHARACTERS_CONFIG(NamedTuple):
    extra: str
    replacement: str


class CHECK_CONFIG(NamedTuple):
    run: Check
    file_system: FS
    base_path_length: int
    characters: CHECK_CHARACTERS_CONFIG


class FS_CONFIG(NamedTuple):
    special_characters: str
    max_path_length: int
