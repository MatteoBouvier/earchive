# Adapted from https://github.com/uiri/toml

import datetime
import re
from collections.abc import Generator, Iterable
from decimal import Decimal
from enum import IntFlag
from typing import Any

from typing_extensions import Callable

from earchive.commands.check import RegexPattern
from earchive.names import SupportsWrite
from earchive.utils.path import FastPath

# FIXME: bug when writing config to same file, file is wrong or completely blank


def dump(obj: dict[str, Any], fp: SupportsWrite[str]) -> str:
    """Writes out dict as toml to a file

    Args:
        obj: Object to dump into toml
        fp: File descriptor where the toml should be stored

    Returns:
        String containing the toml corresponding to dictionary

    Raises:
        TypeError: When anything other than file descriptor is passed
    """

    if not hasattr(fp, "write"):
        raise TypeError("You can only dump an object to a file descriptor")

    d = dumps(obj)
    _ = fp.write(d)

    return d


def dumps(obj: dict[str, Any]) -> str:
    """Stringifies input dict as toml

    Args:
        obj: Object to dump into toml

    Returns:
        String containing the toml corresponding to dict
    """
    encoder = TomlEncoder()
    return encoder.dump_sections(obj)


class TomlEncoder:
    def __init__(self) -> None:
        self._dump_functions: dict[type, Callable[[Any], str]] = {
            str: self._dump_str,
            list: self._dump_list,
            bool: lambda value: str(value).lower(),
            IntFlag: lambda value: self._dump_list([f.name for f in value]),
            int: lambda value: str(value),
            float: self._dump_float,
            Decimal: self._dump_float,
            datetime.datetime: lambda value: value.isoformat().replace("+00:00", "Z"),
            datetime.time: self._dump_time,
            datetime.date: lambda value: value.isoformat(),
            re.Pattern: self._dump_pattern,
            RegexPattern: self._dump_regex,
            FastPath: lambda value: self._dump_str(str(value)),
        }

    def _dump_str(self, value: str) -> str:
        assert isinstance(value, str)

        value = value.strip("'\"").replace('"', '\\"')
        return '"' + value + '"'

    def _dump_float(self, value: float) -> str:
        assert isinstance(value, float)

        return str(value).replace("e+0", "e+").replace("e-0", "e-")

    def _dump_time(self, value: datetime.time):
        utcoffset = value.utcoffset()
        if utcoffset is None:
            return value.isoformat()
        # The TOML norm specifies that it's local time thus we drop the offset
        return value.isoformat()[:-6]

    def _dump_list(self, value: Iterable[Any]) -> str:
        assert hasattr(value, "__iter__")

        retval = ", ".join(map(self._dump_value, value))
        return f"[{retval}]"

    def _dump_pattern(self, value: re.Pattern[str]) -> str:
        return '"' + value.pattern + '"'

    def _dump_regex(self, value: RegexPattern) -> str:
        assert isinstance(value, RegexPattern)

        match, replacement, accent_sensitive = value.match, value.replacement, value.accent_sensitive
        case_sensitive = not (match.flags & re.IGNORECASE)

        replacement = replacement.replace("\\", "\\\\")
        match_pattern = match.pattern.replace("\\", "\\\\")

        if not accent_sensitive or not case_sensitive:
            retval = f'replacement = "{replacement}"'
            if not accent_sensitive:
                retval += ", noaccent = true"

            if not case_sensitive:
                retval += ", nocase = true"

            return f'"{match_pattern}" = {{{retval}}}'

        return f'"{match_pattern}" = "{replacement}"'

    def _encode_section(self, section: str) -> str:
        assert isinstance(section, str)

        if re.match(r"^[A-Za-z0-9_-]+$", section):
            return section

        return self._dump_str(section)

    def _dump_value(self, value: Any) -> str:
        # Lookup function corresponding to value's type
        dump_fn = next((f for t, f in self._dump_functions.items() if isinstance(value, t)), None)

        if dump_fn is None:
            if hasattr(value, "__iter__"):
                dump_fn = self._dump_list

            else:
                raise TypeError(f"Object of type '{type(value)}' is not toml-encodable")

        return dump_fn(value)

    def dump_sections(self, obj: dict[str, Any]) -> str:
        retstr = ""

        def dump_section(section: dict[str, Any], previous_section: str) -> Generator[str, None, None]:
            if previous_section != "" and not previous_section.endswith("."):
                previous_section += "."

            for sub_section in section:
                section_name = self._encode_section(sub_section)

                # dict
                if isinstance(section[sub_section], dict):
                    if previous_section:
                        yield "\n"
                    yield f"[{previous_section}{section_name}]\n"
                    yield from dump_section(section[sub_section], previous_section + section_name)
                    if not previous_section:
                        yield "\n"

                elif isinstance(section[sub_section], list) and not previous_section:
                    yield f"[{previous_section}{section_name}]\n"
                    for value in section[sub_section]:
                        yield self._dump_value(value) + "\n"
                    yield "\n"

                else:
                    yield f"{section_name} = {self._dump_value(section[sub_section])}\n"

        for txt in dump_section(obj, ""):
            retstr += txt

        return retstr
