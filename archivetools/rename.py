from enum import Enum
from pathlib import Path
import re
from typing import Generator, Literal, NamedTuple
from itertools import chain

from archivetools.names import OS
from archivetools.parse_config import DEFAULT_CONFIG, parse_config, Config
from archivetools.progress import Bar


class CTX(NamedTuple):
    config: Config
    os: OS


class INVALID_KIND(str, Enum):
    CHR = "CHARACTERS"
    LEN = "LENGTH"


INVALID_PATH_CHR = tuple[Literal[INVALID_KIND.CHR], Path, list[re.Match]]
INVALID_PATH_LEN = tuple[Literal[INVALID_KIND.LEN], Path]
INVALID_PATH_DATA = INVALID_PATH_CHR | INVALID_PATH_LEN


def _print_matches(matches: list[re.Match]) -> str:
    txt = " "
    last_offset = 0

    for m in matches:
        txt += " " * (m.start() - last_offset)
        last_offset = m.end()
        txt += "^"
    return txt


def repr_invalid_data(data: INVALID_PATH_DATA, ctx: CTX) -> str:
    match data:
        case INVALID_KIND.CHR, path, matches:
            return (
                f"* Invalid path {path.absolute()}\n"
                f"               {' ' * len(str(path.absolute().parent))}{_print_matches(matches)}\n"
            )

        case INVALID_KIND.LEN, path:
            return f"* Invalid path length ({len(str(path))} is larger than {ctx.config.get_max_path_length(ctx.os)}) {path}\n"

        case _:
            raise RuntimeError("Found invalid kind")


def _is_excluded(path: Path, ctx: CTX) -> bool:
    return any(parent in ctx.config.exclude for parent in chain([path], path.parents))


def check_valid_file(
    path: Path, ctx: CTX, check_chr: bool, check_len: bool
) -> Generator[INVALID_PATH_DATA, None, None]:
    if _is_excluded(path, ctx):
        return

    if check_chr:
        match = list(ctx.config.get_invalid_characters(ctx.os).finditer(path.stem))

        if len(match):
            yield (INVALID_KIND.CHR, path, match)

    if check_len and len(str(path)) > ctx.config.get_max_path_length(ctx.os):
        yield (INVALID_KIND.LEN, path)


def invalid_paths(
    path: Path, ctx: CTX, check_chr: bool = True, check_len: bool = True, progress: bool = False
) -> Generator[INVALID_PATH_DATA, None, None]:
    if path.is_file():
        yield from check_valid_file(path, ctx, check_chr, check_len)

    else:
        paths = path.walk(top_down=False, on_error=print)
        if progress:
            paths = Bar(paths)

        for root, dirs, files in paths:
            for file in files + dirs:
                yield from check_valid_file(root / file, ctx, check_chr, check_len)


def check_path(dir: Path, cfg: str, os: OS = OS.windows) -> None:
    dir = dir.resolve(strict=True)
    ctx = CTX(parse_config(Path(cfg)) if cfg else DEFAULT_CONFIG, os)

    counter = 0
    invalid_msg = ""
    for counter, invalid_data in enumerate(invalid_paths(dir, ctx, progress=True), start=1):
        invalid_msg += repr_invalid_data(invalid_data, ctx)

    print(invalid_msg)
    print(f"--> Found {counter} invalid path{'' if counter == 1 else 's'}")


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
def rename_path(dir: Path, cfg: str, os: OS = OS.windows) -> None:
    dir = dir.resolve(strict=True)
    ctx = CTX(parse_config(Path(cfg)) if cfg else DEFAULT_CONFIG, os)

    # First pass : remove special characters
    for invalid_data in invalid_paths(dir, ctx, check_len=False):
        match invalid_data:
            case INVALID_KIND.CHR, path, _:
                path.rename(
                    path.parent
                    / re.sub(
                        ctx.config.get_invalid_characters(os), ctx.config.special_characters["replacement"], path.stem
                    )
                )

    # second pass : replace patterns defined in the `cfg` file
    for root, dirs, files in dir.walk(top_down=False, on_error=print):
        for file in files + dirs:
            rename_if_match(root / file, ctx)

    # thrid pass : check for paths still too long
    for invalid_data in invalid_paths(dir, ctx, check_chr=False):
        match invalid_data:
            case INVALID_KIND.LEN, path:
                print(f"Path is too long ({len(str(path))}) : {path}")
