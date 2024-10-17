from __future__ import annotations
from enum import StrEnum, auto
import re
from pathlib import Path
from typing import Any, Callable, TypedDict
import unicodedata
import dataclasses as dt


class FS(StrEnum):
    windows = auto()


class SECTIONS(StrEnum):
    windows = auto()
    special_characters = auto()
    rename = auto()
    exclude = auto()


class ParseError(Exception): ...


@dt.dataclass(frozen=True, repr=False)
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


class FS_CONFIG(TypedDict):
    special_characters: str
    max_path_length: int


class SPECIAL_CHARACTERS_CONFIG(TypedDict):
    extra: str
    replacement: str


@dt.dataclass(frozen=True, repr=False)
class Config:
    windows: FS_CONFIG
    special_characters: SPECIAL_CHARACTERS_CONFIG
    rename: list[RegexPattern]
    exclude: list[Path]
    invalid_characters: dict[FS, re.Pattern[str]] = dt.field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "invalid_characters",
            {FS.windows: re.compile("[" + self.windows["special_characters"] + self.special_characters["extra"] + "]")},
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

    def get_max_path_length(self, fs: FS) -> int:
        if fs is FS.windows:
            return self.windows["max_path_length"]

        raise ValueError

    def get_invalid_characters(self, os: FS) -> re.Pattern[str]:
        return self.invalid_characters[os]

    def to_dict(self) -> dict[SECTIONS, Any]:
        return {
            SECTIONS.windows: self.windows.copy(),
            SECTIONS.special_characters: self.special_characters.copy(),
            SECTIONS.rename: [dt.replace(p) for p in self.rename],
            SECTIONS.exclude: self.exclude.copy(),
        }


DEFAULT_CONFIG = Config(
    windows={"special_characters": r"<>:/\\|?*", "max_path_length": 260},
    special_characters={"extra": "", "replacement": "_"},
    rename=[],
    exclude=[],
)


_SECTION_FACTORY: dict[SECTIONS, type[dict[Any, Any] | list[Any]]] = {
    SECTIONS.windows: dict,
    SECTIONS.special_characters: dict,
    SECTIONS.rename: list,
    SECTIONS.exclude: list,
}


def parse_value(string: str, _: int) -> str | int:
    try:
        return int(string)
    except ValueError:
        return string.strip()


def parse_key(string: str, _: int) -> str:
    return string.strip()


def parse_key_value(key: str, value: str, line_nb: int) -> tuple[str, str | int]:
    return parse_key(key, line_nb), parse_value(value, line_nb)


def parse_pattern(key: str, value: str, line_nb: int) -> tuple[None, RegexPattern]:
    parts = value.strip().split(" ")

    replacement = None
    case_sensitive = True
    accent_sensitive = True

    for part in parts:
        if part == "NO_CASE":
            case_sensitive = False

        elif part == "NO_ACCENT":
            accent_sensitive = False

        elif replacement is None:
            replacement = part

        else:
            raise ParseError(f"Invalid value '{part}' at line {line_nb}")

    if replacement is None:
        raise ParseError(f"Replacement pattern was not defined at line {line_nb}")

    match = re.compile(key.strip(), flags=re.NOFLAG if case_sensitive else re.IGNORECASE)

    return None, RegexPattern(match, replacement, accent_sensitive)


def parse_path(value: str, _: int) -> Path:
    return Path(value).resolve()


def _dict_setter(section: dict[Any, Any], key: Any, value: Any) -> None:
    section[key] = value


def _list_setter(section: list[Any], _: Any, value: Any) -> None:
    section.append(value)


_SETTER_FUNCTION = Callable[[dict[Any, Any], Any, Any], None] | Callable[[list[Any], Any, Any], None]

_KEY_VALUE_PARSER: dict[SECTIONS, tuple[Callable[[str, str, int], tuple[Any, Any]], _SETTER_FUNCTION]] = {
    SECTIONS.windows: (parse_key_value, _dict_setter),
    SECTIONS.special_characters: (parse_key_value, _dict_setter),
    SECTIONS.rename: (parse_pattern, _list_setter),
}

_VALUE_PARSER: dict[SECTIONS, tuple[Callable[[str, int], Any], _SETTER_FUNCTION]] = {
    SECTIONS.exclude: (parse_path, _list_setter),
}


def parse_config(path: Path) -> Config:
    config = {}
    section: SECTIONS | None = None

    with open(path, "r") as config_file:
        for line_nb, line in enumerate(config_file, start=1):
            line = line.strip()
            if line == "":
                continue

            match re.split(r"[\[\]=]", line):
                case ["", str(section_str), ""]:
                    section_str = section_str.strip()
                    if section_str not in SECTIONS:
                        raise ParseError(f"Invalid section name '{section_str}'")

                    section = SECTIONS(section_str)
                    config[section] = _SECTION_FACTORY[section]()

                case [str(p)]:
                    if section is None:
                        raise ParseError(f"Found values outside a section at line {line_nb}")

                    parse_, set_ = _VALUE_PARSER[section]
                    set_(config[section], None, parse_(p, line_nb))

                case [str(key), str(value)]:
                    if section is None:
                        raise ParseError(f"Found values outside a section at line {line_nb}")

                    parse_, set_ = _KEY_VALUE_PARSER[section]
                    set_(config[section], *parse_(key, value, line_nb))

                case _:
                    raise ParseError(f"Line {line_nb} was not understood")

    config = DEFAULT_CONFIG.to_dict() | config
    return Config(**config)
