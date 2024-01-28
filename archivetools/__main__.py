import sys
import typer
from pathlib import Path
from typing_extensions import Annotated

from archivetools.tree import Node
from archivetools.compare import compare as compare_paths
from archivetools.cli import show_tree


app = typer.Typer()


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


app()
