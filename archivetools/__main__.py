from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from archivetools.rename import FS, Check, OutputKind, check_path, rename_path

# from archivetools.tree import Node
# from archivetools.compare import compare as compare_paths
# from archivetools.cli import show_tree
from archivetools.rename.doc import print_doc

app = typer.Typer(
    help="Collection of helper tools for digital archives management.",
    context_settings=dict(help_option_names=["--help", "-h"]),
    rich_markup_mode="rich",
)


# @app.command()
# def show(path: Annotated[str, typer.Option("--path", "-p")] = ".") -> None:
#     show_tree(Node.from_path(Path(path)))
#
#
# @app.command()
# def empty(
#     path: Annotated[str, typer.Option("--path", "-p")] = ".",
#     recursive: Annotated[bool, typer.Option("--recursive", "-r")] = False,
# ) -> None:
#     Node.from_path(Path(path)).list_empty(recursive=recursive)
#
#
# @app.command()
# def compare(
#     path_1: Annotated[str, typer.Option("--path1")],
#     path_2: Annotated[str, typer.Option("--path2")],
#     show_root: bool = True,
#     depth: int = 0,
# ) -> None:
#     tree_1 = Node.from_path(Path(path_1))
#     tree_2 = Node.from_path(Path(path_2))
#     compare_paths(tree_1, tree_2, not show_root, max_depth=depth or sys.maxsize)


def _parse_checks(
    check_empty_dirs: bool | None,
    check_invalid_characters: bool | None,
    check_path_length: bool | None,
    add_check_empty_dirs: bool,
) -> Check:
    # no option selected (True OR False) : use defaults
    if all(map(lambda c: c is None, (check_empty_dirs, check_invalid_characters, check_path_length))):
        if add_check_empty_dirs:
            return Check.EMPTY | Check.CHARACTERS | Check.LENGTH
        return Check.CHARACTERS | Check.LENGTH

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


@app.command()
def check(
    path: Annotated[Path, typer.Argument(exists=True, help="Path to check")] = Path("."),
    fs: Annotated[FS, typer.Option("--fs", "-f", help="Target file system")] = FS.windows,
    config: Annotated[
        Optional[Path], typer.Option("--config", "-c", exists=True, dir_okay=False, help="Path to config file")
    ] = None,
    check_empty_dirs: Annotated[
        Optional[bool],
        typer.Option(
            "--check-empty-dirs/--no-check-empty-dirs",
            "-e/-E",
            help="Perform check for empty directories",
            show_default=False,
        ),
    ] = None,
    add_check_empty_dirs: Annotated[
        bool, typer.Option("--add-check-empty-dirs", "+e", help="Add check for empty directories to default checks")
    ] = False,
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
    output: Annotated[
        OutputKind, typer.Option(help="Output format (cli = in command line | csv = as csv)")
    ] = OutputKind.cli,
    doc: Annotated[bool, typer.Option("--doc", help="Show documentation and exit")] = False,
) -> None:
    r""":mag: [blue]Check[/blue] for invalid paths on a target file system."""
    if doc:
        print_doc("check")
        raise typer.Exit()

    checks = _parse_checks(check_empty_dirs, check_invalid_characters, check_path_length, add_check_empty_dirs)
    check_path(path, fs, config, checks=checks, output=output)


@app.command()
def rename(
    path: Annotated[Path, typer.Argument(exists=True, writable=True, help="Path to rename")] = Path("."),
    fs: Annotated[FS, typer.Option("--fs", "-f", help="Target file system")] = FS.windows,
    config: Annotated[
        Optional[Path], typer.Option("--config", "-c", exists=True, dir_okay=False, help="Path to config file")
    ] = None,
    check_empty_dirs: Annotated[
        Optional[bool],
        typer.Option(
            "--check-empty-dirs/--no-check-empty-dirs",
            "-e/-E",
            help="Remove empty directories recursively",
            show_default=False,
        ),
    ] = None,
    add_check_empty_dirs: Annotated[
        bool, typer.Option("--add-check-empty-dirs", "+e", help="Add check for empty directories to default checks")
    ] = False,
    check_invalid_characters: Annotated[
        Optional[bool],
        typer.Option(
            "--check-invalid-characters/--no-check-invalid-characters",
            "-i/-I",
            help="Replace invalid characters",
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
    # TODO: add to docs
    output: Annotated[
        Optional[OutputKind], typer.Option(help="Output format (cli = in command line | csv = as csv)")
    ] = None,
    doc: Annotated[bool, typer.Option("--doc", help="Show documentation and exit")] = False,
) -> None:
    r""":fountain_pen:  [blue]Rename[/blue] paths to conform with rules on a target operating system."""
    if doc:
        print_doc("rename")
        raise typer.Exit()

    checks = _parse_checks(check_empty_dirs, check_invalid_characters, check_path_length, add_check_empty_dirs)
    rename_path(path, fs, config, checks=checks, output=output)


app()
