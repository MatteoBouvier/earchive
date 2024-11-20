from rich.panel import Panel

import earchive.errors as err
from earchive.commands.check.config import Config
from earchive.commands.check.names import (
    CheckRepr,
    OutputKind,
)
from earchive.commands.check.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console, console_err
from earchive.commands.check.utils import Counter, fix_invalid_paths, invalid_paths, plural
from earchive.utils.progress import Bar


def _check_fix(config: Config, messages: Grid, output: OutputKind) -> Counter:
    counter = Counter()
    progress: Bar = Bar(description="processing files ...")

    for message in fix_invalid_paths(config, progress, counter):
        messages.add_row(message)

    messages.print()

    if output in (OutputKind.cli, OutputKind.unfixed):
        console.print(f"\nChecked: {', '.join([CheckRepr[check] for check in config.check.run])}")
        if counter.value:
            console.print(
                f"{counter.value} invalid path{plural(counter.value)} could not be fixed out of {progress.counter}",
                style=ERROR_STYLE,
            )
        else:
            console.print("All invalid paths were fixed.", style=SUCCESS_STYLE)

    return counter


def _check_analyze(config: Config, messages: Grid, output: OutputKind) -> Counter:
    counter = Counter()
    progress: Bar = Bar(description="processing files ...")

    for invalid_data in invalid_paths(config, progress=progress):
        messages.add_row(invalid_data)
        counter.value += 1

    messages.print()

    if output in (OutputKind.cli, OutputKind.unfixed):
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
