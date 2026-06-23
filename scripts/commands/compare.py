import sys

from rich import print
from rich.tree import Tree

from earchive.commands.cli import node_link
from earchive.utils.tree import Node


def _index(node: Node, others: list[Node]) -> int:
    for i, other_node in enumerate(others):
        if node.path.name == other_node.path.name:
            return i

    return -1


def _add_subtree(t: Node, tree: Tree, id: int, max_depth: int, depth: int) -> None:
    if depth == max_depth:
        return
    depth += 1

    for node in t.child_nodes:
        branch = tree.add(node_link(node.path, f"\t({id})", color="red"))
        _add_subtree(node, branch, id, max_depth, depth)


def _split(t1: list[Node], t2: list[Node]) -> tuple[list[tuple[Node, Node]], list[Node]]:
    specific_to_1 = []
    common_nodes = []

    for node_1 in t1:
        i = _index(node_1, t2)
        if i == -1:
            specific_to_1.append(node_1)

        else:
            common_nodes.append((node_1, t2[i]))

    return common_nodes, specific_to_1


def _compare_subtree(st1: list[Node], st2: list[Node], tree: Tree, max_depth: int, depth: int = 0) -> Tree:
    if depth == max_depth:
        return tree
    depth += 1

    common_nodes, specific_to_1 = _split(st1, st2)

    for node_1, node_2 in common_nodes:
        branch = tree.add(node_link(node_1.path, color="green"))
        _compare_subtree(node_1.child_nodes, node_2.child_nodes, branch, max_depth, depth)

    for node_1 in specific_to_1:
        branch = tree.add(node_link(node_1.path, "\t(1)", color="red"))
        _add_subtree(node_1, branch, 1, max_depth, depth)

    for node_2 in _split(st2, st1)[1]:
        branch = tree.add(node_link(node_2.path, "\t(2)", color="red"))
        _add_subtree(node_2, branch, 2, max_depth, depth)

    return tree


def compare(t1: Node, t2: Node, hide_root: bool = False, max_depth: int = sys.maxsize) -> None:
    tree = Tree(f"{t1.path.name} vs {t2.path.name}", hide_root=hide_root)

    tree = _compare_subtree(t1.child_nodes, t2.child_nodes, tree, max_depth)

    print(tree)
