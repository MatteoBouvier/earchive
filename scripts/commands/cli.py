from pathlib import Path

from rich.markup import escape
from rich.text import Text
from rich.tree import Tree

from earchive.utils.tree import Node

FIlE_ICON = "📄"
FOLDER_ICON = "📂"


def node_link(path: Path, annotation: str = "", *, color: str = "white") -> Text:
    icon = FOLDER_ICON if path.is_dir() else FIlE_ICON

    text = Text(f"{icon} {escape(path.name)}{annotation}", color)
    text.stylize(f"link file://{path}")

    return text


def _get_tree(node: Node, tree: Tree) -> Tree:
    if node.path.is_dir():
        branch = tree.add(node_link(node.path, "magenta"))

        for n in node.child_nodes:
            _get_tree(n, branch)

    else:
        tree.add(node_link(node.path, "green"))

    return tree


def show_tree(node: Node) -> None:
    tree = Tree("ROOT", hide_root=True)
    print(_get_tree(node, tree))
