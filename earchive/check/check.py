import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from earchive.check.names import CTX, FS, Action, Check, OutputKind, PathDiagnostic
from earchive.check.parse_config import DEFAULT_CONFIG, RegexPattern, parse_config
from earchive.check.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console
from earchive.check.utils import invalid_paths, plural
from earchive.progress import Bar


@dataclass
class Counter:
    value: int = 0


def _rename_if_match(path: Path, ctx: CTX) -> PathDiagnostic | None:
    new_name = str(path.name)
    matched_patterns: list[tuple[RegexPattern, str]] = []

    for pattern in ctx.config.rename:
        new_name, nsubs = pattern.match.subn(pattern.replacement, pattern.normalize(new_name))

        if nsubs:
            matched_patterns.append((pattern, new_name))

    if len(matched_patterns):
        new_path = path.rename(path.parent / new_name)
        return PathDiagnostic(Action.RENAME, path, patterns=matched_patterns, new_path=new_path)


def _rename_core(dir: Path, fs: FS, ctx: CTX, checks: Check, counter: Counter) -> Generator[PathDiagnostic, None, None]:
    # First pass : remove special characters
    if Check.CHARACTERS in checks:
        for invalid_data in invalid_paths(dir, ctx, checks=Check.CHARACTERS, progress=Bar()):
            match invalid_data:
                case PathDiagnostic(Check.CHARACTERS, path, matches):
                    new_path = path.rename(
                        path.parent
                        / re.sub(
                            ctx.config.get_invalid_characters(fs),
                            ctx.config.special_characters["replacement"],
                            path.stem,
                        )
                    )
                    yield PathDiagnostic(Check.CHARACTERS, path, matches=matches, new_path=new_path)

    # second pass : replace patterns defined in the `cfg` file
    for root, dirs, files in dir.walk(top_down=False, on_error=print):
        for file in files + dirs:
            rename_data = _rename_if_match(root / file, ctx)

            if rename_data is not None:
                yield rename_data

    # thrid pass : check for paths still too long / remove empty directories
    remaining_checks = checks ^ Check.CHARACTERS
    if remaining_checks:
        for invalid_data in invalid_paths(dir, ctx, checks=remaining_checks, progress=Bar()):
            match invalid_data:
                case PathDiagnostic(Check.EMPTY, path):
                    path.rmdir()
                    yield PathDiagnostic(Check.EMPTY, path)

                case PathDiagnostic(Check.LENGTH, path):
                    console.print(f"Path is too long ({len(str(path))}) : {path}", style=ERROR_STYLE)
                    counter.value += 1
                    yield PathDiagnostic(Check.LENGTH, path)


def check_path(
    dir: Path,
    fs: FS,
    cfg: Path | None,
    checks: Check = Check.CHARACTERS | Check.LENGTH,
    output: OutputKind = OutputKind.cli,
    fix: bool = False,
) -> int:
    if not checks and not fix:
        return 0

    dir = dir.resolve(strict=True)
    ctx = CTX(DEFAULT_CONFIG if cfg is None else parse_config(cfg), fs)

    counter = Counter()
    progress: Bar[Any] = Bar()
    messages = Grid(ctx, kind=output, mode="rename" if fix else "check")

    if fix:
        for message in _rename_core(dir, fs, ctx, checks, counter):
            messages.add_row(message)

    else:
        for invalid_data in invalid_paths(dir, ctx, checks=checks, progress=progress):
            messages.add_row(invalid_data)
            counter.value += 1

    console.print(messages, no_wrap=True)

    if fix:
        if output == OutputKind.cli:
            if counter.value:
                console.print(
                    f"\n{counter.value} invalid path{plural(counter.value)} could not be fixed.", style=ERROR_STYLE
                )
            else:
                console.print("\nAll invalid paths were fixed.", style=SUCCESS_STYLE)

        elif output == OutputKind.silent:
            console.print(counter.value)

    else:
        if output == OutputKind.cli:
            console.print(
                f"\nFound {counter.value} invalid path{plural(counter.value)} out of {progress.counter}",
                style=ERROR_STYLE if counter.value else SUCCESS_STYLE,
            )

        elif output == OutputKind.silent:
            console.print(counter.value)

    return counter.value
