import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from earchive.check.names import Action, Check, CheckRepr, OutputKind, PathDiagnostic
from earchive.check.config import Config, RegexPattern
from earchive.check.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console
from earchive.check.utils import invalid_paths, plural, walk_all
from earchive.progress import Bar


@dataclass
class Counter:
    value: int = 0


def _rename_if_match(path: Path, config: Config) -> PathDiagnostic | None:
    new_name = str(path.name)
    matched_patterns: list[tuple[RegexPattern, str]] = []

    for pattern in config.rename:
        new_name, nsubs = pattern.match.subn(pattern.replacement, pattern.normalize(new_name))

        if nsubs:
            matched_patterns.append((pattern, new_name))

    if len(matched_patterns):
        new_path = path.rename(path.parent / new_name)
        return PathDiagnostic(Action.RENAME, path, patterns=matched_patterns, new_path=new_path)


def _rename(dir: Path, config: Config, counter: Counter) -> Generator[PathDiagnostic, None, None]:
    # First pass : remove special characters
    if Check.CHARACTERS in config.check.run:
        for invalid_data in invalid_paths(dir, config, checks=Check.CHARACTERS, progress=Bar()):
            match invalid_data:
                case PathDiagnostic(Check.CHARACTERS, path, matches):
                    new_path = path.rename(
                        (
                            path.parent
                            / re.sub(
                                config.invalid_characters,
                                config.check.characters.replacement,
                                path.stem,
                            )
                        ).with_suffix(path.suffix)
                    )
                    yield PathDiagnostic(Check.CHARACTERS, path, matches=matches, new_path=new_path)

    # second pass : replace patterns defined in the `cfg` file
    for root, dirs, files in walk_all(dir, top_down=False):
        for file in files + dirs:
            rename_data = _rename_if_match(root / file, config)

            if rename_data is not None:
                yield rename_data

    # thrid pass : check for paths still too long / remove empty directories
    remaining_checks = config.check.run ^ Check.CHARACTERS
    if remaining_checks:
        for invalid_data in invalid_paths(dir, config, checks=remaining_checks, progress=Bar()):
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
    config: Config,
    output: OutputKind = OutputKind.cli,
    fix: bool = False,
) -> int:
    if not config.check.run and not fix:
        return 0

    dir = dir.resolve(strict=True)

    counter = Counter()
    progress: Bar[Any] = Bar("processed files ...")
    messages = Grid(config, kind=output, mode="fix" if fix else "check")

    if fix:
        for message in _rename(dir, config, counter):
            messages.add_row(message)

    else:
        for invalid_data in invalid_paths(dir, config, progress=progress):
            messages.add_row(invalid_data)
            counter.value += 1

    messages.print(no_wrap=True)

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

    return counter.value
