import contextlib
import traceback
from sys import stderr

import typer
from rich import print as rprint
from rich.text import Text


class ParseError(Exception): ...


class raise_typer(contextlib.AbstractContextManager):
    """Context manager to re-raise exceptions as typer.Exit(). Exception messages are printed to stderr."""

    def __enter__(self) -> None:
        pass

    def __exit__(self, exctype, excinst, exctb) -> None:
        if exctype is None:
            return

        if len(excinst.args) > 1:
            message = excinst.args[1]
            code = excinst.args[0]

        else:
            traceback.print_tb(exctb, file=stderr)
            message = f"{exctype.__name__}: {excinst}"
            code = 100  # Unknown exception

        rprint(Text(message, style="bold red"), file=stderr)
        raise typer.Exit(code)


# Error codes
RUNTIME = 1


def runtime_error(message: str) -> RuntimeError:
    return RuntimeError(RUNTIME, message)


OSERROR = 2


def os_error(message: str) -> OSError:
    return OSError(OSERROR, message)


CHECK_FAILED = 10

FIX_FAILED = 20

FILE_CANNOT_OVERWRITE = 30

PARSE_NOT_UNDERSTOOD = 40
PARSE_VALUE_OUTSIDE_SECTION = 41
PARSE_INVALID_VALUE = 42
PARSE_PATTERN_HAS_NO_REPLACMENT = 43


def parse_error(code: int, message: str, line_nb: int) -> ParseError:
    if code == PARSE_NOT_UNDERSTOOD:
        comment = "Line was not understood"

    elif code == PARSE_VALUE_OUTSIDE_SECTION:
        comment = "Found values outside a section"

    elif code == PARSE_INVALID_VALUE:
        comment = "Found invalid value"

    elif code == PARSE_PATTERN_HAS_NO_REPLACMENT:
        comment = "Replacement was not defined for pattern"

    else:
        raise runtime_error(f"Invalid error code '{code}'")

    return ParseError(code, f"While parsing configuration file :\n[Line #{line_nb}] {comment}: {message}")


FILE_SYSTEM_UNKNOWN = 50


def unknown_file_system(message) -> OSError:
    return OSError(FILE_SYSTEM_UNKNOWN, f"File system '{message}' is not currently supported")
