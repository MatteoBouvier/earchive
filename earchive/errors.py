import contextlib
import traceback
from abc import ABC, abstractmethod
from collections.abc import Iterable
from sys import stderr
from types import TracebackType
from typing import Any, Never, final, overload, override

from rich import print as rprint
from rich.text import Text

import earchive.lib.typer as typer
from earchive.names import SupportsFormat


class ParseError(Exception): ...


class raise_typer(contextlib.AbstractContextManager[None]):
    """Context manager to re-raise exceptions as typer.Exit(). Exception messages are printed to stderr."""

    @override
    def __exit__(
        self, exctype: type[BaseException] | None, excinst: BaseException | None, exctb: TracebackType | None
    ) -> None:
        if exctype is None:
            return

        assert excinst is not None and exctb is not None

        if len(excinst.args) > 1:
            message: str = excinst.args[1]
            code: int = excinst.args[0]

        else:
            traceback.print_tb(exctb, file=stderr)
            message = f"{exctype.__name__}: {excinst}"
            code = 100  # Unknown exception

        rprint(Text(message, style="bold red"), file=stderr)
        raise typer.Exit(code)


# Error codes
def runtime_error(message: str) -> RuntimeError:
    RUNTIME = 1
    return RuntimeError(RUNTIME, message)


def os_error(message: str) -> OSError:
    OSERROR = 2
    return OSError(OSERROR, message)


CHECK_FAILED = 10

FIX_FAILED = 20


def cannot_overwrite(path: str) -> OSError:
    FILE_CANNOT_OVERWRITE = 30
    return OSError(FILE_CANNOT_OVERWRITE, f"Cannot overwrite existing file '{path}'")


def parse_cannot_decode_toml(message: str) -> ParseError:
    PARSE_CANNOT_DECODE_TOML = 40
    return ParseError(PARSE_CANNOT_DECODE_TOML, f"Cannot parse configuration file: {message}")


def parse_invalid_section_name(section: str) -> ParseError:
    PARSE_INVALID_SECTION_NAME = 41
    return ParseError(
        PARSE_INVALID_SECTION_NAME, f"Found invalid section name '{section}' while parsing configuration file"
    )


def parse_invalid_regex_format(pattern: str, value: Any) -> ParseError:
    PARSE_INVALID_REGEX_FORMAT = 42
    return ParseError(
        PARSE_INVALID_REGEX_FORMAT,
        f"Pattern {pattern} has wrong format definition '{value}'\n"
        + "It should be a single replacement string or a dictionary with keys (replacement [,noaccent] [,nocase])",
    )


def parse_pattern_no_replacement(pattern: str) -> ParseError:
    PARSE_PATTERN_HAS_NO_REPLACMENT = 43
    return ParseError(PARSE_PATTERN_HAS_NO_REPLACMENT, f"Replacement was not defined for pattern '{pattern}'")


def parse_unexpected_section(section: str) -> ParseError:
    PARSE_UNEXPECTED_SECTION = 44
    return ParseError(
        PARSE_UNEXPECTED_SECTION, f"Found unexpected section '{section}' while parsing configuration file"
    )


def option_invalid_format(message: SupportsFormat) -> ParseError:
    OPTION_INVALID_FORMAT = 50
    return ParseError(OPTION_INVALID_FORMAT, f"Option '{message}' has invalid format, expected '<option>=<value>'")


def option_invalid_rename_flag(message: SupportsFormat) -> ParseError:
    OPTION_INVALID_RENAME_FLAG = 51
    return ParseError(
        OPTION_INVALID_RENAME_FLAG,
        f"Option 'rename' has received invalid flag '{message}', expected [-noaccent|-nocase]",
    )


def option_cannot_infer(opt: SupportsFormat) -> ValueError:
    OPTION_CANNOT_INFER = 52
    return ValueError(OPTION_CANNOT_INFER, f"Cannot auto infer value for option '{opt}'")


def option_invalid_name(option: str):
    OPTION_INVALID_NAME = 53
    return ParseError(OPTION_INVALID_NAME, f"No such option: '{option}'")


OPTION_INVALID_VALUE = 54


class AssertTest(ABC):
    def __init__(self, opt: str, value: Any) -> None:
        self.opt: str = opt
        self.value: Any = value

    @abstractmethod
    def __call__(self) -> bool:
        pass

    @property
    @abstractmethod
    def expected(self) -> str:
        pass


@final
class Raise(AssertTest):
    def __init__(self, opt: str, value: Any, *, expected: str) -> None:
        super().__init__(opt, value)
        self._expected = expected

    @override
    def __call__(self) -> bool:
        return False

    @property
    @override
    def expected(self) -> str:
        return self._expected


@final
class IsType(AssertTest):
    def __init__(self, opt: str, value: Any, typ: type | tuple[type, ...]) -> None:
        super().__init__(opt, value)
        self._type = typ

    @override
    def __call__(self) -> bool:
        return isinstance(self.value, self._type)

    @property
    @override
    def expected(self) -> str:
        return str(self._type)


@final
class AllIsType(AssertTest):
    def __init__(self, opt: str, value: Iterable[Any], typ: type) -> None:
        super().__init__(opt, value)
        self._type = typ

    @override
    def __call__(self) -> bool:
        return all(isinstance(obj, self._type) for obj in self.value)

    @property
    @override
    def expected(self) -> str:
        return f"all values to be {self._type}"


@final
class IsGreater(AssertTest):
    def __init__(self, opt: str, value: Any, min: int) -> None:
        super().__init__(opt, value)
        self.min = min

    @override
    def __call__(self) -> bool:
        return self.value >= self.min

    @property
    @override
    def expected(self) -> str:
        return f"greater or equal to {self.min}"


@overload
def assert_option(test: Raise) -> Never: ...


@overload
def assert_option(test: AssertTest) -> None: ...


def assert_option(test: AssertTest) -> None:
    if not test():
        raise AssertionError(
            OPTION_INVALID_VALUE,
            f"Got invalid value '{test.value}' for option '{test.opt}', expected {test.expected}",
        )


def unknown_operating_system(message: SupportsFormat) -> OSError:
    OPERATING_SYSTEM_UNKNOWN = 60
    return OSError(OPERATING_SYSTEM_UNKNOWN, f"Operating system '{message}' is not currently supported")


def unknown_file_system(message: SupportsFormat) -> OSError:
    FILE_SYSTEM_UNKNOWN = 61
    return OSError(FILE_SYSTEM_UNKNOWN, f"File system '{message}' is not currently supported")
