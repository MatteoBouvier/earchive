import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import click
import typer
from rich import print as rprint
from rich.text import Text

import earchive.errors as err
from earchive.check import FS, Check, OutputKind, check_path, parse_config
from earchive.cli import show_tree
from earchive.compare import compare as compare_paths
from earchive.copy import copy_structure
from earchive.doc import print_doc
from earchive.tree import Node

app = typer.Typer(
    help="Collection of helper tools for digital archives management.",
    context_settings=dict(help_option_names=["--help", "-h"]),
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
    no_args_is_help=True,
)


@app.command()
def show(path: Annotated[str, typer.Option("--path", "-p")] = ".") -> None:
    show_tree(Node.from_path(Path(path)))


@app.command()
def empty(
    path: Annotated[str, typer.Option("--path", "-p")] = ".",
    recursive: Annotated[bool, typer.Option("--recursive", "-r")] = False,
) -> None:
    Node.from_path(Path(path)).list_empty(recursive=recursive)


@app.command()
def compare(
    path_1: Annotated[str, typer.Option("--path1")],
    path_2: Annotated[str, typer.Option("--path2")],
    show_root: bool = True,
    depth: int = 0,
) -> None:
    tree_1 = Node.from_path(Path(path_1))
    tree_2 = Node.from_path(Path(path_2))
    compare_paths(tree_1, tree_2, not show_root, max_depth=depth or sys.maxsize)


def _parse_checks(
    check_empty_dirs: bool | None,
    check_invalid_characters: bool | None,
    check_path_length: bool | None,
    check_all: bool,
) -> Check | None:
    if check_all:
        return Check.EMPTY | Check.CHARACTERS | Check.LENGTH

    # no option selected (True OR False) : use defaults
    if all(map(lambda c: c is None, (check_empty_dirs, check_invalid_characters, check_path_length))):
        return None

    # some options selected as True : use only selected checks
    if any(c for c in (check_empty_dirs, check_invalid_characters, check_path_length)):
        return (
            (Check.EMPTY if check_empty_dirs else Check.NO_CHECK)
            | (Check.CHARACTERS if check_invalid_characters else Check.NO_CHECK)
            | (Check.LENGTH if check_path_length else Check.NO_CHECK)
        )

    # some options selected as False only : use all but deselected
    return (
        (Check.EMPTY if check_empty_dirs in (True, None) else Check.NO_CHECK)
        | (Check.CHARACTERS if check_invalid_characters in (True, None) else Check.NO_CHECK)
        | (Check.LENGTH if check_path_length in (True, None) else Check.NO_CHECK)
    )


class _parse_OutputKind(click.ParamType):
    name = f"[{'|'.join(OutputKind.__members__)}]"

    def convert(self, value: str, param: Any, ctx: click.Context | None) -> OutputKind:
        kind = OutputKind(value)
        if kind.path_ is not None and Path(kind.path_).exists():
            with err.raise_typer():
                raise err.os_error(f"Output file '{kind.path_}' already exists")

        return kind


@app.command()
def check(
    path: Annotated[Path, typer.Argument(exists=True, help="Path to check")] = Path("."),
    doc: Annotated[bool, typer.Option("--doc", help="Show documentation and exit")] = False,
    fs: Annotated[FS, typer.Option(help="Target file system")] = FS.AUTO,
    destination: Annotated[
        Optional[Path],
        typer.Option(
            exists=True,
            file_okay=False,
            writable=True,
            help="Destination path where files would be copied to.",
        ),
    ] = None,
    config: Annotated[Optional[Path], typer.Option(exists=True, dir_okay=False, help="Path to config file")] = None,
    output: Annotated[
        OutputKind,
        typer.Option(
            click_type=_parse_OutputKind(),
            help="Output format. For csv, an output file can be specified with 'csv=path/to/output.csv'",
        ),
    ] = OutputKind.cli,
    fix: Annotated[bool, typer.Option("--fix", help="Fix paths to conform with rules of target file system")] = False,
    check_all: Annotated[bool, typer.Option("--check-all", "-A", help="Perform all available checks")] = False,
    check_empty_dirs: Annotated[
        Optional[bool],
        typer.Option(
            "--check-empty-dirs/--no-check-empty-dirs",
            "-e/-E",
            help="Perform check for empty directories",
            show_default=False,
        ),
    ] = None,
    check_invalid_characters: Annotated[
        Optional[bool],
        typer.Option(
            "--check-invalid-characters/--no-check-invalid-characters",
            "-i/-I",
            help="Perform check for invalid characters",
            show_default=False,
        ),
    ] = None,
    check_path_length: Annotated[
        Optional[bool],
        typer.Option(
            "--check-path-length/--no-check-path-length",
            "-l/-L",
            help="Perform check for path length",
            show_default=False,
        ),
    ] = None,
) -> None:
    r""":mag: [blue]Check[/blue] for invalid paths on a target file system and fix them."""
    if doc:
        print_doc("check")
        raise typer.Exit()

    checks = _parse_checks(check_empty_dirs, check_invalid_characters, check_path_length, check_all)
    with err.raise_typer():
        cfg = parse_config(config, fs, destination, checks)

    nb_issues = check_path(path, cfg, output=output, fix=fix)

    if nb_issues:
        raise typer.Exit(code=err.FIX_FAILED if fix else err.CHECK_FAILED)


@app.command()
def copy(
    src: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, readable=True, resolve_path=True, help="Source directory to copy"),
    ],
    dst: Annotated[
        Path,
        typer.Argument(
            file_okay=False, writable=True, resolve_path=True, help="Destination for storing the directory structure"
        ),
    ],
) -> None:
    r""":books: [blue]Copy[/blue] a directory structure (file contents are not copied)."""
    if not dst.exists:
        dst.mkdir(parents=True)

    copy_structure(src, dst)


def main() -> None:
    app()
