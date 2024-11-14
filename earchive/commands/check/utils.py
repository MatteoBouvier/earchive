import itertools as it
from collections.abc import Generator
from itertools import chain
from pathlib import Path
from typing import Any

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
from earchive.utils.progress import Bar, NoBar


def plural(value: int) -> str:
    return "" if value == 1 else "s"


def _is_excluded(path: Path, config: Config) -> bool:
    if not len(config.exclude):
        return False
    return any(parent in config.exclude for parent in chain([path], path.parents))


def _is_empty(path: Path, empty_dirs: set[Path]) -> bool:
    for sub in path.iterdir():
        if sub not in empty_dirs:
            return False

    empty_dirs.add(path)
    return True


def check_valid_file(
    path: Path, config: Config, checks: Check, empty_dirs: set[Path]
) -> Generator[PathDiagnostic, None, None]:
    if _is_excluded(path, config):
        return

    if Check.EMPTY in checks:
        if path.is_dir() and _is_empty(path, empty_dirs):
            yield PathEmptyDiagnostic(path)

    if Check.CHARACTERS in checks:
        if len(match := config.invalid_characters.finditer(path.stem)):
            yield PathCharactersDiagnostic(path, matches=match)

        if config.invalid_names.match(path.stem):
            yield PathInvalidNameDiagnostic(path)

    if Check.LENGTH in checks:
        if len(path.name) > config.check.max_name_length:
            yield PathFilenameLengthDiagnostic(path)

        if len(str(path)) > config.check.max_path_length:
            yield PathLengthDiagnostic(path)


def walk_all(
    path: Path,
    errors: list[PathDiagnostic] | None = None,
    top_down: bool = True,
    follow_symlinks: bool = False,
) -> Generator[tuple[Path, list[str], list[str]], None, None]:
    if errors is None:
        errors = []

    def yield_root() -> Generator[tuple[Path, list[str], list[str]], None, None]:
        yield path.parent, [str(path)] if path.is_dir() else [], [str(path)] if path.is_file() else []

    def on_error(err: OSError) -> None:
        errors.append(PathErrorDiagnostic(Path(err.filename), error=err))

    def yield_children() -> Generator[tuple[Path, list[str], list[str]], None, None]:
        if path.is_dir():
            yield from path.walk(top_down=top_down, on_error=on_error, follow_symlinks=follow_symlinks)

    if top_down:
        yield from it.chain(yield_root(), yield_children())

    else:
        yield from it.chain(yield_children(), yield_root())


def invalid_paths(
    config: Config, checks: Check | None = None, progress: Bar[Any] = NoBar
) -> Generator[PathDiagnostic, None, None]:
    empty_dirs: set[Path] = set()
    errors: list[PathDiagnostic] = []

    if checks is None:
        checks = config.check.run

    for root, dirs, files in progress(walk_all(config.check.path, errors, top_down=False)):
        for file in files + dirs:
            yield from check_valid_file(root / file, config, checks, empty_dirs)

    yield from errors
