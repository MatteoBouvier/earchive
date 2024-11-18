import itertools as it
import sys
from collections.abc import Generator
from itertools import chain

from earchive.commands.check.config import Config
from earchive.commands.check.names import (
    Check,
    PathCharactersDiagnostic,
    PathDiagnostic,
    PathEmptyDiagnostic,
    PathErrorDiagnostic,
    PathFilenameLengthDiagnostic,
    PathInvalidNameDiagnostic,
    PathLengthDiagnostic,
)
from earchive.utils.os import OS
from earchive.utils.path import FastPath
from earchive.utils.progress import Bar, NoBar


def plural(value: int) -> str:
    return "" if value == 1 else "s"


def _is_excluded(path: FastPath, config: Config) -> bool:
    if not len(config.exclude):
        return False

    return any(parent in config.exclude for parent in chain([path], path.parents))


def _is_empty_recurse(path: FastPath, empty_dirs: set[str]) -> bool:
    for sub in path.iterdir():
        if sub not in empty_dirs:
            return False

    empty_dirs.add(path.str())
    return True


# TODO: move to FastPath
def path_len(path: FastPath, os: OS) -> int:
    """Get a Path's true length on a target operating system, even from another os"""
    path_len = len(str(path))

    if os is OS.WINDOWS and sys.platform != "win32":
        # on UNIX platforms, account for windows' extra path elements : <DRIVE>:/<path><NUL> --> 4 less characters
        path_len += 4

    return path_len


def check_valid_file(
    path: FastPath, is_dir: bool, config: Config, checks: Check, empty_dirs: set[str]
) -> Generator[PathDiagnostic, None, None]:
    if _is_excluded(path, config):
        return

    if Check.EMPTY in checks:
        if is_dir:
            try:
                is_empty = _is_empty_recurse(path, empty_dirs)
            except PermissionError as e:
                yield PathErrorDiagnostic(path, error=e)
            else:
                if is_empty:
                    yield PathEmptyDiagnostic(path)

    if Check.CHARACTERS in checks:
        if len(match := config.invalid_characters.finditer(path.stem)):
            yield PathCharactersDiagnostic(path, matches=match)

        if config.invalid_names.match(path.stem):
            yield PathInvalidNameDiagnostic(path)

    if Check.LENGTH in checks:
        if len(path.name) > config.check.max_name_length:
            yield PathFilenameLengthDiagnostic(path)

        if path_len(path, config.check.operating_system) > config.check.max_path_length:
            yield PathLengthDiagnostic(path)


def walk_all(
    path: FastPath,
    errors: list[PathDiagnostic] | None = None,
    top_down: bool = True,
    follow_symlinks: bool = False,
) -> Generator[tuple[FastPath, list[str], list[str]], None, None]:
    if errors is None:
        errors = []

    def yield_root() -> Generator[tuple[FastPath, list[str], list[str]], None, None]:
        yield path.parent, [path.name] if path.is_dir() else [], [path.name] if path.is_file() else []

    def on_error(err: OSError) -> None:
        errors.append(PathErrorDiagnostic(FastPath.from_str(err.filename), error=err))

    def yield_children() -> Generator[tuple[FastPath, list[str], list[str]], None, None]:
        if path.is_dir():
            yield from path.walk(top_down=top_down, on_error=on_error, follow_symlinks=follow_symlinks)

    if top_down:
        yield from it.chain(yield_root(), yield_children())

    else:
        yield from it.chain(yield_children(), yield_root())


def invalid_paths(
    config: Config, checks: Check | None = None, progress: Bar[tuple[FastPath, list[str], list[str]]] = NoBar
) -> Generator[PathDiagnostic, None, None]:
    empty_dirs: set[str] = set()
    errors: list[PathDiagnostic] = []

    if checks is None:
        checks = config.check.run

    paths = walk_all(config.check.path, errors, top_down=False)
    if config.behavior.dry_run:
        paths = it.islice(paths, config.behavior.dry_run)

    for root, dirs, files in progress(paths):
        for file in files:
            yield from check_valid_file(root / file, False, config, checks, empty_dirs)

        for dir in dirs:
            yield from check_valid_file(root / dir, True, config, checks, empty_dirs)

    yield from errors
