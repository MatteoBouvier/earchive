import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, cast

import tomllib

import earchive.errors as err
from earchive.commands.check.config.cast import as_bool, as_bool_or_uint, as_enum, as_path, as_regex, as_str, as_uint
from earchive.commands.check.config.config import CliConfig, Config
from earchive.commands.check.config.default import DEFAULT_CONFIG
from earchive.commands.check.config.fs import CONFIG_FILE_SYSTEMS
from earchive.commands.check.config.names import ASCII, COLLISION, HEADER, ConfigDict
from earchive.commands.check.config.substitution import RegexPattern
from earchive.commands.check.names import Check
from earchive.utils.fs import FS, get_file_system
from earchive.utils.os import OS, get_operating_system
from earchive.utils.path import FastPath


def parse_pattern(rhs: str, lhs: Any) -> RegexPattern:
    if isinstance(lhs, str):
        replacement = lhs
        case_sensitive = True
        accent_sensitive = True

    elif isinstance(lhs, dict):
        lhs = cast(dict[str, str | bool], lhs)
        try:
            replacement = as_str(lhs["replacement"], f"rename ({rhs}, replacement)")
        except KeyError:
            raise err.parse_pattern_no_replacement(rhs)

        case_sensitive = not as_bool(lhs.get("nocase", False), f"rename ({rhs}, nocase)")
        accent_sensitive = not as_bool(lhs.get("noaccent", False), f"rename ({rhs}, noaccent)")

    else:
        raise err.parse_invalid_regex_format(rhs, lhs)

    match = re.compile(as_str(rhs, f"rename ({rhs})").strip(), flags=re.NOFLAG if case_sensitive else re.IGNORECASE)

    return RegexPattern(match, replacement, accent_sensitive)


def _destructure(data: dict[Any, Any], root_header: HEADER = HEADER.NO_HEADER) -> list[tuple[HEADER, Any]]:
    elements: list[tuple[HEADER, Any]] = []

    for header, content in data.items():
        if root_header in (HEADER.RENAME, HEADER.EXCLUDE):
            elements.append((root_header, (header, content)))
            continue

        try:
            full_header = root_header + header
        except ValueError:
            raise err.parse_invalid_section_name(header)

        if isinstance(content, dict):
            elements.extend(_destructure(cast(dict[Any, Any], content), full_header))

        else:
            elements.append((full_header, content))

    return elements


def _update_config_from_file(config: ConfigDict, path: Path) -> None:
    with open(path, "rb") as config_file:
        try:
            data = tomllib.load(config_file)

        except tomllib.TOMLDecodeError as e:
            raise err.parse_cannot_decode_toml(e.args[0])

        for header, value in _destructure(data):
            match header:
                case HEADER.BEHAVIOR_COLLISION:
                    config.behavior.collision = as_enum(COLLISION)(value, "behavior:collision")

                case HEADER.BEHAVIOR_DRY_RUN:
                    dry_run = as_bool_or_uint(value, "behavior:collision")
                    config.behavior.dry_run = sys.maxsize if dry_run is True else int(dry_run)

                case HEADER.CHECK_RUN:
                    config.check.run = as_enum(Check)(value, "run")

                case HEADER.CHECK_OPERATING_SYSTEM:
                    config.check.operating_system = as_enum(OS)(value, "operating_system")

                case HEADER.CHECK_FILE_SYSTEM:
                    config.check.file_system = as_enum(FS)(value, "file_system")

                case HEADER.CHECK_PATH:
                    config.check.path = as_path(value, "path", config.check.operating_system)

                case HEADER.CHECK_BASE_PATH_LENGTH:
                    config.check.base_path_length = as_uint(value, "base_path_length")

                case HEADER.CHECK_MAX_PATH_LENGTH:
                    config.check.max_path_length = as_uint(value, "max_path_length")

                case HEADER.CHECK_MAX_NAME_LENGTH:
                    config.check.max_name_length = as_uint(value, "max_name_length")

                case HEADER.CHECK_CHARACTERS_EXTRA_INVALID:
                    # escape regex syntax characters
                    value = re.sub(r"(\.|\$|\^|\*|\+|\(|\)|\[|\]|\|)", r"\\\1", value)
                    config.check.characters.extra_invalid = as_regex(value, "characters:extra_invalid")

                case HEADER.CHECK_CHARACTERS_REPLACEMENT:
                    config.check.characters.replacement = as_str(value, "characters:replacement")

                case HEADER.CHECK_CHARACTERS_ASCII:
                    config.check.characters.ascii = as_enum(ASCII)(value, "characters:ascii")

                case HEADER.RENAME:
                    config.rename.append(parse_pattern(value[0], value[1]))
                    pass

                case HEADER.EXCLUDE:
                    pass

                case _:
                    raise err.parse_unexpected_section(header)


def _update_config_from_cli(
    config: ConfigDict, cli_config: CliConfig, checks: Check | None, dest_path: Path | None, exclude: set[Path]
) -> None:
    if checks is not None:
        config.check.run = checks

    cli_config.update_config(config)

    if isinstance(dest_path, Path):
        if config.check.operating_system is OS.AUTO:
            try:
                config.check.operating_system = get_operating_system(dest_path)

            except ValueError as e:
                raise err.unknown_operating_system(e)

            config.check.path.platform = config.check.operating_system

        if config.check.file_system is FS.AUTO:
            try:
                config.check.file_system = get_file_system(dest_path)

            except ValueError as e:
                raise err.unknown_file_system(e)

            except OSError as e:
                raise err.os_error(str(e))

        if config.check.base_path_length < 0:
            config.check.base_path_length = len(str(dest_path)) + 1

        if config.check.max_path_length < 0:
            if sys.platform == "win32":
                # cannot use pathconf to infer, use default value even if it might rarely be larger
                config.check.max_path_length = 260

            else:
                config.check.max_path_length = os.pathconf(dest_path, "PC_PATH_MAX")

        if config.check.max_name_length < 0:
            if sys.platform == "win32":
                # cannot use pathconf to infer, use default value even if it might rarely be different
                config.check.max_name_length = 255

            else:
                config.check.max_name_length = os.pathconf(dest_path, "PC_NAME_MAX")

    else:
        if config.check.operating_system is OS.AUTO:
            raise err.option_cannot_infer("os")

        if config.check.file_system is FS.AUTO:
            raise err.option_cannot_infer("fs")

        if config.check.base_path_length < 0:
            config.check.base_path_length = 0

        if config.check.max_path_length < 0:
            config.check.max_path_length = CONFIG_FILE_SYSTEMS[config.check.file_system].max_path_length

        if config.check.max_name_length < 0:
            config.check.max_name_length = CONFIG_FILE_SYSTEMS[config.check.file_system].max_name_length

    config.exclude |= set(FastPath.from_str(str(path), config.check.operating_system) for path in exclude)


def parse_config(
    path: Path | None,
    cli_config: CliConfig,
    check_path: Path,
    dest_path: Path | None,
    checks: Check | None,
    exclude: set[Path],
) -> Config:
    r"""
    Merge config options from the cli and from a file.
    /!\ Cli options override configuration values from the file.
    """
    # defaults
    check_path = check_path.resolve(strict=True)
    config = DEFAULT_CONFIG(check_path)

    if path is not None:
        _update_config_from_file(config, path)

    _update_config_from_cli(config, cli_config, checks, dest_path, exclude)

    return Config.from_dict(config)


def _parse_cli_rename(pattern: str, replacement: str) -> RegexPattern:
    accent_sensitive, case_sensitive = True, True

    flags, match = pattern.split(":")

    for flag in flags.split("-"):
        match flag:
            case "noaccent":
                accent_sensitive = False

            case "nocase":
                case_sensitive = False

            case "":
                pass

            case _:
                raise err.option_invalid_rename_flag(flag)

    return RegexPattern(
        re.compile(match, re.IGNORECASE if not case_sensitive else re.NOFLAG),
        replacement,
        accent_sensitive=accent_sensitive,
    )


def parse_cli_config(options: list[str]) -> CliConfig:
    _parse: dict[str, Callable[[str, str], Any]] = dict(
        os=as_enum(OS),
        fs=as_enum(FS),
        base_path_length=as_uint,
        max_path_length=as_uint,
        max_name_length=as_uint,
        characters_extra_invalid=as_regex,
        characters_replacement=as_str,
        characters_ascii=as_enum(ASCII),
        behavior_collision=as_enum(COLLISION),
        behavior_dry_run=as_bool_or_uint,
    )

    cli_options: dict[str, Any] = {}

    for option in options:
        try:
            opt, val = option.split("=")
        except ValueError:
            raise err.option_invalid_format(option)

        if opt.startswith("rename"):
            cli_options.setdefault("rename", []).append(_parse_cli_rename(opt[6:], val))

        else:
            opt = opt.replace(":", "_").replace("-", "_")

            try:
                cli_options[opt] = _parse[opt](val, opt)

            except KeyError:
                raise err.option_invalid_name(opt)

    return CliConfig.from_dict(cli_options)
