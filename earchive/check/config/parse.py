import itertools as it
import re
from pathlib import Path
from typing import Any, Callable

import psutil

from earchive.check.enum import NestedEnumDict
import earchive.errors as err
from earchive.check.config.config import Config, RegexPattern
from earchive.check.config.default import DEFAULT_CONFIG
from earchive.check.config.names import FS, HEADER
from earchive.check.names import Check


def parse_value(string: str, _: int) -> str | int:
    try:
        return int(string)
    except ValueError:
        return string.strip().strip("\"'")  # /!\ strip in 2 steps to avoid removing the space character in " "


def parse_check(string: str, _: int) -> Check:
    return Check(string.strip())


def parse_key(string: str, _: int) -> str:
    return string.strip()


def parse_key_value(key: str, value: str, line_nb: int) -> tuple[str, str | int]:
    return parse_key(key, line_nb), parse_value(value, line_nb)


def parse_key_check(key: str, value: str, line_nb: int) -> tuple[str, Check]:
    return parse_key(key, line_nb), parse_check(value, line_nb)


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
            raise err.parse_error(err.PARSE_INVALID_VALUE, part, line_nb)

    if replacement is None:
        raise err.parse_error(err.PARSE_PATTERN_HAS_NO_REPLACMENT, key.strip(), line_nb)

    match = re.compile(key.strip(), flags=re.NOFLAG if case_sensitive else re.IGNORECASE)

    return None, RegexPattern(match, replacement, accent_sensitive)


def parse_path(value: str, _: int) -> Path:
    return Path(value).resolve()


def _dict_setter(dct: dict[Any, Any], key: Any, value: Any) -> None:
    assert isinstance(dct, dict)
    dct[key] = value


def _list_setter(lst: list[Any], _: Any, value: Any) -> None:
    assert isinstance(lst, list)
    lst.append(value)


_SETTER_FUNCTION = Callable[[dict[Any, Any], Any, Any], None] | Callable[[list[Any], Any, Any], None]


_KEY_VALUE_PARSER: NestedEnumDict[HEADER, tuple[Callable[[str, str, int], tuple[Any, Any]], _SETTER_FUNCTION]] = (
    NestedEnumDict(
        HEADER,
        {
            HEADER.CHECK: (parse_key_value, _dict_setter),
            HEADER.CHECK_RUN: (parse_key_check, _dict_setter),
            HEADER.FILE_SYSTEMS: (parse_key_value, _dict_setter),
            HEADER.RENAME: (parse_pattern, _list_setter),
        },
    )
)

_VALUE_PARSER: dict[HEADER, tuple[Callable[[str, int], Any], _SETTER_FUNCTION]] = {
    HEADER.EXCLUDE: (parse_path, _list_setter),
}


def _get_filesystem(path: Path) -> FS:
    partitions = {part.mountpoint: part.fstype for part in psutil.disk_partitions()}

    for p in it.chain([path], path.parents):
        if fs := partitions.get(str(p), None):
            try:
                return FS(fs)
            except ValueError:
                raise err.unknown_file_system(fs)

    raise err.os_error(f"Could not determine file system of path '{path}'")


def _parse_section(section_str: str, line_nb: int) -> tuple[HEADER, HEADER | FS | None]:
    parts = section_str.split(".")

    match parts:
        case ["check"] | ["rename"] | ["exclude"]:
            return HEADER(parts[0]), None

        case ["check", "characters"]:
            return HEADER(parts[0]), HEADER(f"check:{parts[1]}")

        case ["file_systems", fs]:
            return HEADER(parts[0]), FS(fs)

        case _:
            raise err.parse_error(err.PARSE_INVALID_VALUE, section_str, line_nb)


def parse_config(path: Path | None, file_system: FS, dest_path: Path | None, checks: Check | None) -> Config:
    """
    Get config from a file. Cli options may override configuration values from the file for:
    - target file system
    - performed checks
    - base path length
    """
    # defaults
    config = DEFAULT_CONFIG

    # parse config file
    if path is not None:
        header: HEADER | None = None
        config_section: Any = None

        with open(path, "r") as config_file:
            for line_nb, line in enumerate(config_file, start=1):
                line = line.strip()
                if line == "":
                    continue

                match re.split(r"[\[\]=]", line):
                    case ["", str(section_str), ""]:
                        header, sub_section = _parse_section(section_str, line_nb)
                        config_section = config[header]
                        if sub_section is not None:
                            config_section = config_section[sub_section]

                    case [str(p)]:
                        if header is None:
                            raise err.parse_error(err.PARSE_VALUE_OUTSIDE_SECTION, p, line_nb)

                        parse_, set_ = _VALUE_PARSER[header]
                        set_(config_section, None, parse_(p, line_nb))

                    case [str(key), str(value)]:
                        if header is None:
                            raise err.parse_error(err.PARSE_VALUE_OUTSIDE_SECTION, f"{key} = {value}", line_nb)

                        parse_, set_ = _KEY_VALUE_PARSER[header]
                        set_(config_section, *parse_(key, value, line_nb))

                    case _:
                        raise err.parse_error(err.PARSE_NOT_UNDERSTOOD, line, line_nb)

    # cli overrides
    match (file_system, dest_path):
        case FS.AUTO, Path() as path:
            config[HEADER.CHECK] |= {
                HEADER.CHECK_FILE_SYSTEM: _get_filesystem(path),
                HEADER.CHECK_BASE_PATH_LENGTH: len(str(path)) + 1,
            }

        case fs, Path() as path:
            config[HEADER.CHECK] |= {HEADER.CHECK_FILE_SYSTEM: fs, HEADER.CHECK_BASE_PATH_LENGTH: len(str(path)) + 1}

        case fs, None:
            if fs is not FS.AUTO:
                config[HEADER.CHECK][HEADER.CHECK_FILE_SYSTEM] = fs

    if checks is not None:
        config[HEADER.CHECK][HEADER.CHECK_RUN] = checks

    return Config.from_dict(config)
