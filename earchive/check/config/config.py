from __future__ import annotations

import re
from typing import Any
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from earchive.check.config.names import CHECK_CHARACTERS_CONFIG, CHECK_CONFIG, FS, FS_CONFIG, HEADER
from earchive.check.names import Check


@dataclass(frozen=True, repr=False)
class RegexPattern:
    match: re.Pattern[str]
    replacement: str
    accent_sensitive: bool

    def __repr__(self) -> str:
        return f"RegexPattern<{self.match.pattern} -> {self.replacement}, ignore-case: {bool(self.match.flags & re.IGNORECASE)}, ignore-accents: {not self.accent_sensitive}>"

    def normalize(self, string: str) -> str:
        if self.accent_sensitive:
            return string

        # remove all accents (unicode combining diacritical marks) from string
        return re.sub(r"[\u0300-\u036f]", "", unicodedata.normalize("NFD", string))


@dataclass(frozen=True, repr=False)
class Config:
    check: CHECK_CONFIG
    file_systems: dict[FS, FS_CONFIG]
    rename: list[RegexPattern]
    exclude: list[Path]
    invalid_characters: re.Pattern[str] = field(init=False)

    def __post_init__(self) -> None:
        extras = self.check.characters.extra.replace("-", "\\-")
        object.__setattr__(
            self,
            "invalid_characters",
            re.compile("[" + self.file_systems[self.check.file_system].special_characters + extras + "]"),
        )

    @classmethod
    def from_dict(cls, data: dict[HEADER, Any]) -> Config:
        return Config(
            check=CHECK_CONFIG(
                run=Check(data[HEADER.CHECK][HEADER.CHECK_RUN]),
                file_system=FS(data[HEADER.CHECK][HEADER.CHECK_FILE_SYSTEM]),
                base_path_length=data[HEADER.CHECK][HEADER.CHECK_BASE_PATH_LENGTH],
                characters=CHECK_CHARACTERS_CONFIG(**data[HEADER.CHECK][HEADER.CHECK_CHARACTERS]),
            ),
            file_systems={FS(fs): FS_CONFIG(**fs_config) for fs, fs_config in data[HEADER.FILE_SYSTEMS].items()},
            rename=data[HEADER.RENAME],
            exclude=data[HEADER.EXCLUDE],
        )

    def __repr__(self) -> str:
        def repr_section(section_name: str) -> str:
            section = getattr(self, section_name)

            if isinstance(section, dict):
                key_values = [f"{key}={value}" for key, value in section.items()]
                return f"[{section_name}]\n{'\n'.join(map(lambda s: '\t' + str(s), key_values))}"

            else:
                return f"[{section_name}]\n{'\n'.join(map(lambda s: '\t' + str(s), section))}"

        return f"== Config ==\n{'\n\n'.join(map(repr_section, self.__dict__))}"

    def get_max_path_length(self) -> int:
        return self.file_systems[self.check.file_system].max_path_length - self.check.base_path_length
