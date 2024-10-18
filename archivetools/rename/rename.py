import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from archivetools.progress import Bar
from archivetools.rename.names import CTX, FS, Action, Check, OutputKind, PathDiagnostic
from archivetools.rename.parse_config import DEFAULT_CONFIG, RegexPattern, parse_config
from archivetools.rename.print import ERROR_STYLE, Grid, console
from archivetools.rename.utils import invalid_paths, plural


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

    # TODO: add to docs that if all checks are disabled, only renaming is done
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


# TODO: merge with check command as --fix option
def rename_path(
    dir: Path,
    fs: FS,
    cfg: Path | None,
    checks: Check = Check.EMPTY | Check.CHARACTERS | Check.LENGTH,
    output: OutputKind = OutputKind.silent,
) -> int:
    dir = dir.resolve(strict=True)
    ctx = CTX(DEFAULT_CONFIG if cfg is None else parse_config(cfg), fs)

    messages = Grid(ctx, kind=output, mode="rename")
    counter = Counter()

    for message in _rename_core(dir, fs, ctx, checks, counter):
        messages.add_row(message)

    console.print(messages, no_wrap=True)

    if output == OutputKind.cli:
        console.print(f"\n{counter.value} issue{plural(counter.value)} could not be resolved.")

    elif output == OutputKind.silent:
        console.print(counter.value)

    return counter.value
