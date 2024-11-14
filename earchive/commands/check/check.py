from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.panel import Panel

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
    PathLengthDiagnostic,
    PathRenameDiagnostic,
)
from earchive.commands.check.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console, console_err
from earchive.commands.check.utils import invalid_paths, plural, walk_all
from earchive.utils.progress import Bar


@dataclass
class Counter:
    value: int = 0


def safe_rename(path: Path, target: Path, config: Config) -> bool:
    if target.exists():
        if config.behavior.collision is COLLISION.SKIP:
            return False

        # add `(<nb>)` to file name
        next_nb = (
            max([int(g.stem.split("(")[-1][:-1]) for g in path.parent.glob(path.stem + "(*)" + path.suffix)] + [0]) + 1
        )
        target = target.with_stem(f"{target.stem}({next_nb})")

    if not config.behavior.dry_run:
        path.rename(target)

    return True


def _rename_if_match(path: Path, config: Config) -> PathDiagnostic | None:
    new_name = str(path.name)
    matched_patterns: list[tuple[RegexPattern, str]] = []

    for pattern in config.rename:
        new_name, nsubs = pattern.match.subn(pattern.replacement, pattern.normalize(new_name))

        if nsubs:
            matched_patterns.append((pattern, new_name))

    new_path = path.parent / new_name

    if len(matched_patterns) and safe_rename(path, new_path, config):
        return PathRenameDiagnostic(path, new_path, patterns=matched_patterns)


def rename(config: Config, counter: Counter) -> Generator[PathDiagnostic, None, None]:
    # First pass : remove special characters
    if Check.CHARACTERS in config.check.run:
        repl = bytearray(config.check.characters.replacement, encoding="utf-8")

        for invalid_data in invalid_paths(config, checks=Check.CHARACTERS, progress=Bar()):
            match invalid_data:
                case PathCharactersDiagnostic(Path() as path, matches=matches):
                    new_stem = bytearray(path.stem, encoding="utf-8")

                    for match in matches:
                        new_stem[match.start() : match.start() + len(bytearray(match.group(0), "utf-8"))] = repl

                    new_path = path.with_stem(new_stem.decode())

                    if safe_rename(path, new_path, config):
                        yield PathCharactersReplaceDiagnostic(path, new_path, matches=matches)

                    else:
                        yield invalid_data

                case _:
                    pass

    # second pass : replace patterns defined in the `cfg` file
    for root, dirs, files in walk_all(config.check.path, top_down=False):
        for file in files + dirs:
            rename_data = _rename_if_match(root / file, config)

            if rename_data is not None:
                yield rename_data

    # thrid pass : check for paths still too long / remove empty directories
    remaining_checks = config.check.run ^ Check.CHARACTERS
    if remaining_checks:
        for invalid_data in invalid_paths(config, checks=remaining_checks, progress=Bar()):
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


def check_path(
    config: Config,
    output: OutputKind = OutputKind.cli,
    fix: bool = False,
) -> int:
    if not config.check.run and not fix:
        return 0

    counter = Counter()
    progress: Bar[Any] = Bar("processed files ...")
    messages = Grid(config, kind=output, mode="fix" if fix else "check")

    if fix:
        for message in rename(config, counter):
            messages.add_row(message)

    else:
        for invalid_data in invalid_paths(config, progress=progress):
            messages.add_row(invalid_data)
            counter.value += 1

    messages.print()

    if fix:
        if output == OutputKind.cli:
            console.print(f"\nChecked: {', '.join([CheckRepr[check] for check in config.check.run])}")
            if counter.value:
                console.print(
                    f"{counter.value} invalid path{plural(counter.value)} could not be fixed.", style=ERROR_STYLE
                )
            else:
                console.print("All invalid paths were fixed.", style=SUCCESS_STYLE)

        elif output == OutputKind.silent:
            console.print(counter.value)

    else:
        if output == OutputKind.cli:
            console.print(f"\nChecked: {', '.join([CheckRepr[check] for check in config.check.run])}")
            console.print(
                f"Found {counter.value} invalid path{plural(counter.value)} out of {progress.counter}",
                style=ERROR_STYLE if counter.value else SUCCESS_STYLE,
            )

        elif output == OutputKind.silent:
            console.print(counter.value)

    if output != OutputKind.silent and config.behavior.dry_run:
        console_err.print(Panel(" >>> Performed dry-run, nothing was changed <<< ", style=ERROR_STYLE, expand=False))

    return counter.value
