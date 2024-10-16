from itertools import chain
from pathlib import Path
from typing import Any, Generator

from archivetools.progress import Bar
from archivetools.rename.names import CTX, INVALID_PATH_DATA, Check


def plural(value: int) -> str:
    return "" if value == 1 else "s"


def _is_excluded(path: Path, ctx: CTX) -> bool:
    if not len(ctx.config.exclude):
        return False
    return any(parent in ctx.config.exclude for parent in chain([path], path.parents))


def _is_empty(path: Path, empty_dirs: set[Path]) -> bool:
    for sub in path.iterdir():
        if sub not in empty_dirs:
            return False

    empty_dirs.add(path)
    return True


def check_valid_file(
    path: Path, ctx: CTX, checks: Check, empty_dirs: set[Path]
) -> Generator[INVALID_PATH_DATA, None, None]:
    if _is_excluded(path, ctx):
        return

    if Check.EMPTY in checks:
        if path.is_dir() and _is_empty(path, empty_dirs):
            yield (Check.EMPTY, path)

    if Check.CHARACTERS in checks:
        match = list(ctx.config.get_invalid_characters(ctx.os).finditer(path.stem))

        if len(match):
            yield (Check.CHARACTERS, path, match)

    if Check.LENGTH in checks:
        if len(str(path)) > ctx.config.get_max_path_length(ctx.os):
            yield (Check.LENGTH, path)


def invalid_paths(path: Path, ctx: CTX, checks: Check, progress: Bar[Any]) -> Generator[INVALID_PATH_DATA, None, None]:
    if path.is_file():
        yield from check_valid_file(path, ctx, checks, set())

    else:
        empty_dirs = set()

        for root, dirs, files in progress(path.walk(top_down=False, on_error=print)):
            for file in files + dirs:
                # split: avoid checking dirs empty
                yield from check_valid_file(root / file, ctx, checks, empty_dirs)
