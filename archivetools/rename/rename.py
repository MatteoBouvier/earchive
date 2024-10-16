import re
from pathlib import Path

from archivetools.progress import Bar
from archivetools.rename.names import CTX, OS, Check
from archivetools.rename.parse_config import DEFAULT_CONFIG, parse_config
from archivetools.rename.utils import invalid_paths
from archivetools.rename.print import console, ERROR_STYLE


def rename_if_match(path: Path, ctx: CTX) -> None:
    new_path = str(path.name)
    total_nsubs = 0

    for pattern in ctx.config.rename:
        sub, nsubs = pattern.match.subn(pattern.replacement, pattern.normalize(new_path))

        if nsubs:
            new_path = sub
            total_nsubs += nsubs

    if total_nsubs:
        path.rename(path.parent / new_path)


# TODO: delete  empty dirs ?
def rename_path(
    dir: Path,
    os: OS,
    cfg: Path | None,
    checks: Check = Check.EMPTY | Check.CHARACTERS | Check.LENGTH,
) -> None:
    dir = dir.resolve(strict=True)
    ctx = CTX(DEFAULT_CONFIG if cfg is None else parse_config(cfg), os)

    # First pass : remove special characters
    if Check.CHARACTERS in checks:
        for invalid_data in invalid_paths(dir, ctx, checks=Check.CHARACTERS, progress=Bar()):
            match invalid_data:
                case Check.CHARACTERS, path, _:
                    path.rename(
                        path.parent
                        / re.sub(
                            ctx.config.get_invalid_characters(os),
                            ctx.config.special_characters["replacement"],
                            path.stem,
                        )
                    )

    # second pass : replace patterns defined in the `cfg` file
    for root, dirs, files in dir.walk(top_down=False, on_error=print):
        for file in files + dirs:
            rename_if_match(root / file, ctx)

    # thrid pass : check for paths still too long / remove empty directories
    remaining_checks = checks ^ Check.CHARACTERS
    if remaining_checks:
        for invalid_data in invalid_paths(dir, ctx, checks=remaining_checks, progress=Bar()):
            match invalid_data:
                case Check.EMPTY, path:
                    path.rmdir()

                case Check.LENGTH, path:
                    console.print(f"Path is too long ({len(str(path))}) : {path}", style=ERROR_STYLE)
