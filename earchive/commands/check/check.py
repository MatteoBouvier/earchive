import itertools as it
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from rich.panel import Panel

import earchive.errors as err
from earchive.commands.check.config import Config
from earchive.commands.check.config.names import COLLISION
from earchive.commands.check.config.substitution import RegexPattern
from earchive.commands.check.names import (
    Check,
    CheckRepr,
    OutputKind,
    PathCharactersDiagnostic,
    PathCharactersReplaceDiagnostic,
    PathDiagnostic,
    PathEmptyDiagnostic,
    PathErrorDiagnostic,
    PathLengthDiagnostic,
    PathRenameDiagnostic,
)
from earchive.commands.check.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console, console_err
from earchive.commands.check.utils import invalid_paths, plural, walk_all
from earchive.utils.path import FastPath
from earchive.utils.progress import Bar


@dataclass
class Counter:
    value: int = 0


def safe_rename(path: FastPath, target: FastPath, config: Config) -> tuple[bool, FastPath]:
    if target.exists():
        if config.behavior.collision is COLLISION.SKIP:
            return (False, path)

        # add `(<nb>)` to file name
        next_nb = (
            max([int(g.stem.split("(")[-1][:-1]) for g in path.parent.glob(path.stem + "(*)" + path.suffix)] + [0]) + 1
        )
        target = target.with_stem(f"{target.stem}({next_nb})")

    if not config.behavior.dry_run:
        path.rename(target)

    return (True, target)


def _rename_if_match(parent: FastPath, filename: str, config: Config) -> PathDiagnostic | None:
    new_name = filename
    matched_patterns: list[tuple[RegexPattern, str]] = []

    for pattern in config.rename:
        new_name, nsubs = pattern.match.subn(pattern.replacement, pattern.normalize(new_name))

        if nsubs:
            matched_patterns.append((pattern, new_name))

    if len(matched_patterns):
        old_path = parent / filename
        success, new_path = safe_rename(old_path, parent / new_name, config)

        if success:
            return PathRenameDiagnostic(old_path, new_path, patterns=matched_patterns)

        else:
            return PathErrorDiagnostic(old_path, error=err.cannot_overwrite(new_path.str()))


def rename(config: Config, counter: Counter) -> Generator[PathDiagnostic, None, None]:
    # First pass : remove special characters
    if Check.CHARACTERS in config.check.run:
        repl = bytearray(config.check.characters.replacement, encoding="utf-8")

        for invalid_data in invalid_paths(
            config, checks=Check.CHARACTERS, progress=Bar(description="Processing (invalid characters)")
        ):
            match invalid_data:
                case PathCharactersDiagnostic(FastPath() as path, matches=matches):
                    new_stem = bytearray(path.stem, encoding="utf-8")

                    for match in matches:
                        new_stem[match.start() : match.start() + len(bytearray(match.group(0), "utf-8"))] = repl

                    success, new_path = safe_rename(path, path.with_stem(new_stem.decode()), config)

                    if success:
                        yield PathCharactersReplaceDiagnostic(path, new_path, matches=matches)

                    else:
                        yield invalid_data

                case _:
                    pass

    # second pass : replace patterns defined in the `cfg` file
    paths = walk_all(config.check.path, top_down=False)
    if config.behavior.dry_run:
        paths = it.islice(paths, config.behavior.dry_run)

    for root, dirs, files in Bar(paths, description="Processing (renaming files)"):
        for file in files + dirs:
            rename_data = _rename_if_match(root, file, config)

            if rename_data is not None:
                yield rename_data

    # thrid pass : check for paths still too long / remove empty directories
    remaining_checks = config.check.run ^ Check.CHARACTERS
    if remaining_checks:
        for invalid_data in invalid_paths(
            config,
            checks=remaining_checks,
            progress=Bar(description=f"Processing (path {' & '.join(str(c.name).lower() for c in remaining_checks)})"),
        ):
            match invalid_data:
                case PathEmptyDiagnostic(path) as diagnostic:
                    if not config.behavior.dry_run:
                        path.rmdir()

                    yield diagnostic

                case PathLengthDiagnostic(path) as diagnostic:
                    counter.value += 1
                    yield diagnostic

                case _:
                    pass


def _check_fix(config: Config, messages: Grid, output: OutputKind) -> Counter:
    counter = Counter()

    for message in rename(config, counter):
        messages.add_row(message)

    messages.print()

    if output == OutputKind.cli:
        console.print(f"\nChecked: {', '.join([CheckRepr[check] for check in config.check.run])}")
        if counter.value:
            console.print(f"{counter.value} invalid path{plural(counter.value)} could not be fixed.", style=ERROR_STYLE)
        else:
            console.print("All invalid paths were fixed.", style=SUCCESS_STYLE)

    return counter


def _check_analyze(config: Config, messages: Grid, output: OutputKind) -> Counter:
    counter = Counter()
    progress: Bar[Any] = Bar(description="processed files ...")

    for invalid_data in invalid_paths(config, progress=progress):
        messages.add_row(invalid_data)
        counter.value += 1

    messages.print()

    if output == OutputKind.cli:
        console.print(f"\nChecked: {', '.join([CheckRepr[check] for check in config.check.run])}")
        console.print(
            f"Found {counter.value} invalid path{plural(counter.value)} out of {progress.counter}",
            style=ERROR_STYLE if counter.value else SUCCESS_STYLE,
        )

    return counter


def check_path(
    config: Config,
    output: OutputKind = OutputKind.cli,
    fix: bool = False,
) -> int:
    if not config.check.run and not fix:
        return 0

    messages = Grid(config, kind=output, mode="fix" if fix else "check")

    try:
        if fix:
            counter = _check_fix(config, messages, output)

        else:
            counter = _check_analyze(config, messages, output)

        if output == OutputKind.silent:
            console.print(counter.value)

    except KeyboardInterrupt:
        raise err.runtime_error("Keyboard interrupt")

    finally:
        if config.behavior.dry_run:
            console_err.print(
                Panel(" >>> Performed dry-run, nothing was changed <<< ", style=ERROR_STYLE, expand=False)
            )

    return counter.value
