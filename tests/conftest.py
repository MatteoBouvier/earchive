from __future__ import annotations
from typing import Any, Generator

import pytest
from earchive.tree import Node

type TreeType = dict[str, TreeType | None]

tree: TreeType = {
    "root": {
        "d_a": {
            "f_1": None,
            "f_2": None,
        },
        "d_b": {},
        "d_c": {"f_3": None, "d_c_a": {"f_4": None, "d_c_a_a": {}}},
    }
}


class PathMock:
    def __init__(self, tree: TreeType, position: tuple[str, ...]) -> None:
        self.tree = tree
        self.position = position

    def __truediv__(self, position: str) -> PathMock:
        return PathMock(self.tree, self.position + (position,))

    def __eq__(self, other: Any):
        if not isinstance(other, PathMock):
            return False

        return self.path == other.path

    def __repr__(self) -> str:
        return f"PathMock({self.path})"

    @property
    def path(self) -> str:
        return "/".join(self.position)

    @property
    def name(self) -> str:
        return self.position[-1]

    def is_dir(self) -> bool:
        return self._get() is not None

    def is_file(self) -> bool:
        return self._get() is None

    def _get(self) -> TreeType | None:
        tree = self.tree

        for pos in self.position:
            assert tree is not None
            tree = tree[pos]

        return tree

    def iterdir(self) -> Generator[PathMock, None, None]:
        tree = self._get()
        assert tree is not None

        return (self / pos for pos in tree.keys())


@pytest.fixture()
def path() -> PathMock:
    return PathMock(tree, ("root",))


@pytest.fixture()
def nodes() -> Node:
    path = PathMock(tree, ("root",))
    return Node(
        path,
        [
            Node(
                path / "d_a",
                [
                    Node(path / "d_a" / "f_1"),
                    Node(path / "d_a" / "f_2"),
                ],
            ),
            Node(path / "d_b", []),
            Node(
                path / "d_c",
                [
                    Node(path / "d_c" / "f_3"),
                    Node(
                        path / "d_c" / "d_c_a",
                        [
                            Node(path / "d_c" / "d_c_a" / "f_4"),
                            Node(path / "d_c" / "d_c_a" / "d_c_a_a", []),
                        ],
                    ),
                ],
            ),
        ],
    )
