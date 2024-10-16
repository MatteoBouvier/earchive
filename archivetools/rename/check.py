from pathlib import Path
from typing import Any

from archivetools.progress import Bar
from archivetools.rename.names import CTX, OS, Check
from archivetools.rename.parse_config import DEFAULT_CONFIG, parse_config
from archivetools.rename.print import ERROR_STYLE, SUCCESS_STYLE, Grid, console
from archivetools.rename.utils import invalid_paths, plural


def check_path(
    dir: Path,
    os: OS,
    cfg: Path | None,
    checks: Check = Check.EMPTY | Check.CHARACTERS | Check.LENGTH,
) -> None:
    dir = dir.resolve(strict=True)
    ctx = CTX(DEFAULT_CONFIG if cfg is None else parse_config(cfg), os)

    if not checks:
        return

    counter = 0
    invalid_messages = Grid(ctx)

    progress: Bar[Any] = Bar()
    for counter, invalid_data in enumerate(invalid_paths(dir, ctx, checks=checks, progress=progress), start=1):
        invalid_messages.add_row(invalid_data)

    console.print(invalid_messages)
    console.print(
        f"\nFound {counter} invalid path{plural(counter)} out of {progress.counter}",
        style=ERROR_STYLE if counter else SUCCESS_STYLE,
    )
