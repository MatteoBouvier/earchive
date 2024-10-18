from pathlib import Path
from typing import Any

from archivetools.progress import Bar
from archivetools.rename.names import CTX, FS, Check, OutputKind
from archivetools.rename.parse_config import DEFAULT_CONFIG, parse_config
from archivetools.rename.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console
from archivetools.rename.utils import invalid_paths, plural


def check_path(
    dir: Path,
    fs: FS,
    cfg: Path | None,
    checks: Check = Check.EMPTY | Check.CHARACTERS | Check.LENGTH,
    output: OutputKind = OutputKind.cli,
) -> None:
    if not checks:
        return

    dir = dir.resolve(strict=True)
    ctx = CTX(DEFAULT_CONFIG if cfg is None else parse_config(cfg), fs)

    counter = 0
    invalid_messages = Grid(ctx, kind=output, mode="check")

    progress: Bar[Any] = Bar()
    for counter, invalid_data in enumerate(invalid_paths(dir, ctx, checks=checks, progress=progress), start=1):
        invalid_messages.add_row(invalid_data)

    console.print(invalid_messages, no_wrap=True)

    if output == OutputKind.cli:
        console.print(
            f"\nFound {counter} invalid path{plural(counter)} out of {progress.counter}",
            style=ERROR_STYLE if counter else SUCCESS_STYLE,
        )
