# pyright: reportDeprecated=false

import sys
from pathlib import Path
from typing import Annotated, Any, Optional, final, override
from importlib import metadata

import click

import earchive.errors as err
import earchive.lib.typer as typer
from earchive.commands.analyze import analyze_path
from earchive.commands.check import Check, OutputKind, check_path, parse_cli_config, parse_config
from earchive.commands.cli import show_tree
from earchive.commands.compare import compare as compare_paths
from earchive.commands.copy import copy_structure
from earchive.doc import Language
from earchive.doc.doc import print_doc
from earchive.utils.os import OS
from earchive.utils.path import FastPath
from earchive.utils.tree import Node

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


@final
class _parse_OutputKind(click.ParamType):
    name = f"[{'|'.join(OutputKind.__members__)}]"

    @override
    def convert(self, value: str, param: Any, ctx: click.Context | None) -> OutputKind:
        kind = OutputKind(value)
        if kind.path_ is not None and Path(kind.path_).exists():
            with err.raise_typer():
                raise err.cannot_overwrite(kind.path_)

        return kind


def maybe_print_doc(lang: Language | None) -> None:
    if lang is not None:
        print_doc("check", lang)
        raise typer.Exit()


@app.command(no_args_is_help=True)
def check(
    path: Annotated[
        Path,
        typer.Argument(exists=True, show_default=False, help="Path to check"),
    ],
    doc: Annotated[
        bool | Language,
        typer.Option(callback=maybe_print_doc, help="Show documentation and exit"),
    ] = Language.en,
    fix: Annotated[bool, typer.Option("--fix", help="Fix paths to conform with rules of target file system")] = False,
    check_all: Annotated[bool, typer.Option("--all", help="Perform all available checks")] = False,
    options: Annotated[list[str], typer.Option("-o", help="Configuration options")] = [],  # pyright: ignore[reportCallInDefaultInitializer]
    behavior_options: Annotated[list[str], typer.Option("-O", help="Behavior configuration options")] = [],  # pyright: ignore[reportCallInDefaultInitializer]
    destination: Annotated[
        Optional[Path],
        typer.Option(
            exists=True,
            file_okay=False,
            writable=True,
            help="Destination path where files would be copied to",
        ),
    ] = None,
    config: Annotated[
        Optional[Path],
        typer.Option(exists=True, dir_okay=False, help="Path to config file"),
    ] = None,
    make_config: Annotated[
        bool, typer.Option("--make-config", show_default=False, help="Create a config file from supplied options")
    ] = False,
    output: Annotated[
        OutputKind,
        typer.Option(
            click_type=_parse_OutputKind(),
            help="Output format. For csv, an output file can be specified with 'csv=path/to/output.csv'",
        ),
    ] = OutputKind.cli,
    exclude: Annotated[list[Path], typer.Option(help="Exclude path from cheked paths")] = [],  # pyright: ignore[reportCallInDefaultInitializer]
    check_empty_dirs: Annotated[
        Optional[bool],
        typer.Option(
            "--empty-dirs/--no-empty-dirs",
            "-e/-E",
            help="Perform check for empty directories",
            show_default=False,
        ),
    ] = None,
    check_invalid_characters: Annotated[
        Optional[bool],
        typer.Option(
            "--invalid-characters/--no-invalid-characters",
            "-i/-I",
            help="Perform check for invalid characters",
            show_default=False,
        ),
    ] = None,
    check_path_length: Annotated[
        Optional[bool],
        typer.Option(
            "--path-length/--no-path-length",
            "-l/-L",
            help="Perform check for path length",
            show_default=False,
        ),
    ] = None,
) -> None:
    r""":mag: [blue]Check[/blue] for invalid paths on a target file system and fix them."""
    del doc

    with err.raise_typer():
        cli_config = parse_cli_config(options + ["behavior:" + bo for bo in behavior_options])
        checks = _parse_checks(check_empty_dirs, check_invalid_characters, check_path_length, check_all)
        cfg = parse_config(config, cli_config, path, destination, checks, set(exclude))

    if make_config:
        print(cfg)
        raise typer.Exit()

    with err.raise_typer():
        nb_issues = check_path(cfg, output=output, fix=fix)

    if nb_issues:
        raise typer.Exit(code=err.FIX_FAILED if fix else err.CHECK_FAILED)


@app.command()
def analyze(
    path: Annotated[
        FastPath,
        typer.Argument(
            exists=True,
            show_default=False,
            parser=lambda s: FastPath.from_str(s, OS(sys.platform)),
            help="Path to analyze",
        ),
    ],
) -> None:
    r""":mag: [blue]Analyze[/blue] a file or directory and list attributes."""
    analyze_path(path)


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
    if not dst.exists():
        dst.mkdir(parents=True)

    copy_structure(src, dst)


@app.callback(invoke_without_command=True)
def main_callback(version: Annotated[bool, typer.Option("--version")] = False) -> None:
    if version:
        print("EArchive version ", metadata.version("earchive"))


def main() -> None:
    app()
