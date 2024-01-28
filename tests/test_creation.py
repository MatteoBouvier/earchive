from archivetools.tree import Node


def test_creation(path, nodes) -> None:
    tree = Node.from_path(path)
    assert tree == nodes
