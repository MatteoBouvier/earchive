from __future__ import annotations

from collections.abc import Generator, Iterator
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path
from typing import override

from natsort import natsorted
from rich import print


@dataclass
class Node:
    """
    File or Directory representation
    """

    path: Path
    child_nodes: list[Node] = field(default_factory=list)

    # region magic methods
    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False

        if not self.eq_shallow(other):
            return False

        for self_node, value_node in zip_longest(self.iter_nodes(), other.iter_nodes(), fillvalue=None):
            if self_node != value_node:
                return False

        return True

    # endregion

    # region attributes
    @property
    def child_dir(self) -> Iterator[Node]:
        return filter(lambda n: n.path.is_dir(), self.child_nodes)

    @property
    def child_files(self) -> Iterator[Node]:
        return filter(lambda n: not n.path.is_dir(), self.child_nodes)

    # endregion

    # region methods
    @classmethod
    def from_path(cls, path: Path) -> Node:
        if path.is_dir():
            return cls(
                path,
                child_nodes=[
                    cls.from_path(path_element)
                    for path_element in natsorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
                ],
            )

        return Node(path)

    def eq_shallow(self, other: Node) -> bool:
        return self.path == other.path

    def is_empty(self, recursive: bool = False) -> bool:
        if not self.path.is_dir():
            raise ValueError("Not a directory")

        if not recursive:
            return len(self.child_nodes) == 0

        return not len(list(self.child_files)) and all((node.is_empty(recursive=True) for node in self.child_dir))

    def list_empty(self, recursive: bool = False) -> None:
        if not self.path.is_dir():
            raise ValueError("Not a directory")

        for node in self.child_dir:
            if node.is_empty(recursive=recursive):
                print(node.path)

            else:
                node.list_empty(recursive=recursive)

    def iter_nodes(self) -> Generator[Node, None, None]:
        for node in natsorted(self.child_nodes, key=lambda n: (n.path.is_dir(), n.path.name.lower())):
            yield node

    # endregion
