import re
from enum import Enum
from typing import Callable

import earchive.errors as err
from earchive.utils.os import OS
from earchive.utils.path import FastPath


def as_uint(value: str, option: str) -> int:
    try:
        uint = int(value)

    except ValueError:
        err.assert_option(err.Raise(option, value, expected="integer"))

    err.assert_option(err.IsGreater(option, uint, 0))

    return uint


def as_bool(value: str | bool, option: str) -> bool:
    if value in ("True", "true", True):
        return True

    elif value in ("False", "false", False):
        return False

    err.assert_option(err.Raise(option, value, expected="[true|false]"))


def as_bool_or_uint(value: str, option: str) -> bool | int:
    try:
        return as_bool(value, option)

    except AssertionError:
        try:
            return as_uint(value, option)

        except AssertionError:
            err.assert_option(err.Raise(option, value, expected="[integer|true|false]"))


def as_str(value: str, option: str) -> str:
    err.assert_option(err.IsType(option, value, str))
    return value


def as_regex(value: str, option: str) -> re.Pattern[str]:
    try:
        return re.compile(value)

    except re.error:
        err.assert_option(err.Raise(option, value, expected="regular expression"))


def as_enum[E: Enum](enum: type[E]) -> Callable[[str, str], E]:
    def inner(value: str, option: str) -> E:
        try:
            return enum(value)

        except ValueError:
            err.assert_option(err.Raise(option, value, expected=f"[{'|'.join(enum.__members__)}]"))

    return inner


def as_path(value: str, option: str, operating_system: OS) -> FastPath:
    try:
        return FastPath.from_str(value, operating_system)
    except TypeError:
        err.assert_option(err.Raise(option, value, expected="file path"))
