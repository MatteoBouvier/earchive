from __future__ import annotations

import re
import string
import sys
from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict, override

import earchive.errors as err
from earchive.commands.check.config.fs import CONFIG_FILE_SYSTEMS
from earchive.commands.check.config.names import ASCII, BEHAVIOR_CONFIG, CHECK_CONFIG, COLLISION, ConfigDict
from earchive.commands.check.config.os import CONFIG_OPERATING_SYSTEMS
from earchive.commands.check.config.substitution import RegexPattern
from earchive.utils.fs import FS
from earchive.utils.os import OS
from earchive.utils.path import FastPath

ASCII_INVALID = {
    ASCII.STRICT: [re.compile("(?![a-zA-Z0-9_]).")],
    ASCII.PRINT: [re.compile(f"(?![a-zA-Z0-9{string.punctuation}]).")],
    ASCII.ACCENTS: [re.compile(f"(?![a-zA-Z\u00c0-\u017f0-9{string.punctuation}]).")],
    ASCII.NO: [],
}


class MultiPattern:
    def __init__(self, patterns: list[re.Pattern[str]]) -> None:
        self.patterns: list[re.Pattern[str]] = [p for p in patterns if p.pattern != ""]
        assert len(self.patterns)

    def finditer(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> list[re.Match[str]]:
        seen: set[tuple[int, int]] = set()
        return [
            match
            for pattern in self.patterns
            for match in pattern.finditer(string, pos, endpos)
            if (span := match.span()) not in seen and (seen.add(span) or True)  # get only unique matches
        ]

    def match(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> re.Match[str] | None:
        for pattern in self.patterns:
            if (match := pattern.match(string, pos, endpos)) is not None:
                return match

        return None


class _Cache(TypedDict):
    invalid_characters: NotRequired[MultiPattern]
    invalid_names: NotRequired[MultiPattern]


@dataclass(frozen=True, repr=False)
class Config:
    behavior: BEHAVIOR_CONFIG
    check: CHECK_CONFIG
    rename: list[RegexPattern]
    exclude: set[FastPath]
    _cache: _Cache = field(init=False, default_factory=lambda: _Cache())

    @classmethod
    def from_dict(cls, data: ConfigDict) -> Config:
        return Config(behavior=data.behavior, check=data.check, rename=data.rename, exclude=data.exclude)

    def to_dict(self) -> dict[str, Any]:
        return dict(
            behavior=self.behavior.to_dict(), check=self.check.to_dict(), rename=self.rename, exclude=self.exclude
        )

    @override
    def __repr__(self) -> str:
        from earchive.utils import toml

        return toml.dumps(self.to_dict())

    @property
    def invalid_characters(self) -> MultiPattern:
        if (pattern := self._cache.get("invalid_characters")) is not None:
            return pattern

        pattern = MultiPattern(
            [
                CONFIG_OPERATING_SYSTEMS[self.check.operating_system].invalid_characters,
                CONFIG_FILE_SYSTEMS[self.check.file_system].invalid_characters,
                self.check.characters.extra_invalid,
            ]
            + ASCII_INVALID[self.check.characters.ascii]
        )

        self._cache["invalid_characters"] = pattern
        return pattern

    @property
    def invalid_names(self) -> MultiPattern:
        if (pattern := self._cache.get("invalid_names")) is not None:
            return pattern

        pattern = MultiPattern(
            CONFIG_OPERATING_SYSTEMS[self.check.operating_system].invalid_names
            + CONFIG_OPERATING_SYSTEMS[self.check.operating_system].reserved_names
            + CONFIG_FILE_SYSTEMS[self.check.file_system].reserved_names
        )

        self._cache["invalid_names"] = pattern
        return pattern


@dataclass(frozen=True)
class CliConfig:
    os: OS | None = None
    fs: FS | None = None
    base_path_length: int | None = None
    max_path_length: int | None = None
    max_name_length: int | None = None
    characters_extra_invalid: re.Pattern[str] | None = None
    characters_replacement: str | None = None
    characters_ascii: ASCII | None = None
    rename: list[RegexPattern] = field(default_factory=list)
    behavior_collision: COLLISION | None = None
    behavior_dry_run: bool | int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CliConfig:
        return CliConfig(**data)

    def update_config(self, config: ConfigDict) -> None:
        if self.behavior_collision is not None:
            err.assert_option(err.IsType("behavior:collision", self.behavior_collision, COLLISION))
            config.behavior.collision = self.behavior_collision

        if self.behavior_dry_run is not None:
            err.assert_option(err.IsType("behavior:dry_run", self.behavior_dry_run, (bool, int)))
            err.assert_option(err.IsGreater("behavior:dry_run", self.behavior_dry_run, 0))
            config.behavior.dry_run = sys.maxsize if self.behavior_dry_run is True else int(self.behavior_dry_run)

        if self.os is not None:
            err.assert_option(err.IsType("os", self.os, OS))
            config.check.operating_system = self.os

        if self.fs is not None:
            err.assert_option(err.IsType("fs", self.fs, FS))
            config.check.file_system = self.fs

        if self.base_path_length is not None:
            err.assert_option(err.IsType("base_path_length", self.base_path_length, int))
            err.assert_option(err.IsGreater("base_path_length", self.base_path_length, 0))
            config.check.base_path_length = self.base_path_length

        if self.max_path_length is not None:
            err.assert_option(err.IsType("max_path_length", self.max_path_length, int))
            err.assert_option(err.IsGreater("max_path_length", self.max_path_length, 0))
            config.check.max_path_length = self.max_path_length

        if self.max_name_length is not None:
            err.assert_option(err.IsType("max_path_length", self.max_name_length, int))
            err.assert_option(err.IsGreater("max_path_length", self.max_name_length, 0))
            config.check.max_name_length = self.max_name_length

        if self.characters_extra_invalid is not None:
            err.assert_option(err.IsType("characters:extra_invalid", self.characters_extra_invalid, re.Pattern))
            config.check.characters.extra_invalid = self.characters_extra_invalid

        if self.characters_replacement is not None:
            err.assert_option(err.IsType("characters:replacement", self.characters_replacement, str))
            config.check.characters.replacement = self.characters_replacement

        if self.characters_ascii is not None:
            err.assert_option(err.IsType("characters:ascii", self.characters_ascii, ASCII))
            config.check.characters.ascii = self.characters_ascii

        if len(self.rename):
            err.assert_option(err.IsType("rename", self.rename, list))
            err.assert_option(err.AllIsType("rename", self.rename, RegexPattern))
            config.rename = list(set(config.rename) | set(self.rename))
