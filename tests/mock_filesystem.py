from __future__ import annotations

from contextlib import AbstractContextManager
import os
import stat
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import Any, Generator, Iterator, Never, Self, cast


def permission_error(filename: str) -> Never:
    raise PermissionError(13, "Permission denied", filename)


def not_a_directory(filename: str) -> Never:
    raise NotADirectoryError(20, "Not a directory", filename)


def file_not_found(filename: str) -> Never:
    raise FileNotFoundError(2, "No such file or directory", filename)


def invalid_cross_device_link(filename: str) -> Never:
    raise OSError(18, "Invalid cross-device link", filename)


class AbsPath(str):
    def __truediv__(self, other: str) -> AbsPath:
        return AbsPath(f"{'' if self == '/' else self}/{other}")


@dataclass(repr=False)
class File:
    name: str
    mode: int
    # 0oXXYZZZ
    #   ~~ <----- file types (04 = directory, 10 = file, 12 = symlink)
    #     ~ <---- access right flag (1 = sticky bit, 2 = GID, 4 = UID)
    #      ~~~ <- permissions (owner, group, others)
    _children_lookup: dict[str, File] = field(init=False)

    def __post_init__(self):
        assert self.name != ""
        assert self.mode >= 0 and self.mode <= 262143  # Oo777777
        assert stat.S_ISREG(self.mode)

        self._children_lookup = {}

    def __repr__(self) -> str:
        return f"{stat.filemode(self.mode)} \t{self.absolute_path}"

    def get(self, name: str, ignore_mode: bool = False) -> File:
        if not ignore_mode and not self.mode & stat.S_IRUSR:
            permission_error(self.absolute_path)

        try:
            return self._children_lookup[name]
        except KeyError:
            file_not_found(self.absolute_path / name)

    def get_all(self, ignore_mode: bool = False) -> Generator[File, None, None]:
        for name in self._children_lookup.keys():
            if name != "..":
                yield self.get(name, ignore_mode)

    def _set_parent(self, dir: Directory) -> None:
        self._children_lookup[".."] = dir

    @property
    def parent(self) -> Directory:
        return cast(Directory, self._children_lookup[".."])

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        return os.stat_result((self.mode, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    @property
    def absolute_path(self) -> AbsPath:
        if self.name == "/":
            return AbsPath("/")

        abs_path = "/" + self.name
        file = self.parent

        while file.name != "/":
            abs_path = f"{file.name}/{abs_path}"
            file = file.parent

        return AbsPath(abs_path)


@dataclass(repr=False)
class Directory(File):
    children: InitVar[list[File] | None] = None

    def __post_init__(self, children: list[File] | None):
        assert self.name != ""
        assert self.mode >= 0 and self.mode <= 262143
        assert stat.S_ISDIR(self.mode)

        if children is None:
            self._children_lookup = {}

        else:
            self._children_lookup = {file.name: file for file in children}

    def __repr__(self) -> str:
        dir_repr = super().__repr__()
        for file in self.list_children():
            dir_repr += f"\n{repr(file)}"

        return dir_repr

    def set(self, name: str, file: File, overwrite: bool = False, ignore_mode: bool = False) -> None:
        if not ignore_mode and not self.mode & stat.S_IRUSR:
            permission_error(self.absolute_path)

        if name in self._children_lookup and not overwrite:
            raise invalid_cross_device_link(self.absolute_path / name)

        self._children_lookup[name] = file

    def delete(self, name: str, ignore_mode: bool = False) -> None:
        if not ignore_mode and not self.mode & stat.S_IRUSR:
            permission_error(self.absolute_path)

        try:
            del self._children_lookup[name]
        except KeyError:
            file_not_found(self.absolute_path / name)

    def list_children(self, ignore_mode: bool = False) -> list[File]:
        return [child for child in self.get_all(ignore_mode=ignore_mode) if child.name != ".."]


class DirEntry:
    def __init__(self, file: File):
        self.file = file

    @property
    def name(self) -> str:
        return self.file.name

    @property
    def path(self) -> str:
        return self.file.absolute_path

    def inode(self) -> int:
        return 0

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return isinstance(self.file, Directory)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return not isinstance(self.file, Directory)

    def is_symlink(self) -> bool:
        return False

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        return self.file.stat(follow_symlinks=follow_symlinks)

    def __fspath__(self) -> str:
        return self.path

    def is_junction(self) -> bool:
        return False


class ScandirIterator(Iterator[DirEntry], AbstractContextManager):
    def __init__(self, file: Directory) -> None:
        self.file = file
        self.it = None

        if not self.file.mode & stat.S_IRUSR:
            permission_error(self.file.absolute_path)

    def __enter__(self) -> Self:
        self.it = iter(self.file.list_children())
        return self

    def __next__(self) -> DirEntry:
        assert self.it is not None
        return DirEntry(next(self.it))

    def __exit__(self, *args) -> None:
        self.it = None

    def close(self) -> None:
        pass


def _set_parent(dir: Directory) -> None:
    for file in dir.list_children(ignore_mode=True):
        file._set_parent(dir)

        if isinstance(file, Directory):
            _set_parent(file)


class FileSystem:
    def __init__(self, files: list[File], mode: int = 0o777) -> None:
        self.root = FileSystem.D("/", files, mode=mode)

        # add .. parent directory to all files
        self.root._set_parent(self.root)
        _set_parent(self.root)

    def __repr__(self) -> str:
        return "Permissions\tName\n" + repr(self.root)

    @staticmethod
    def D(name: str, children: list[File] | None = None, mode: int = 0o777) -> Directory:
        if children is None:
            children = []
        return Directory(name, stat.S_IFDIR | mode, children=children)

    @staticmethod
    def F(name: str, mode: int = 0o777) -> File:
        return File(name, stat.S_IFREG | mode)

    def listdir(self, at_path: PathMock) -> list[File]:
        file = self.get(at_path)

        if not isinstance(file, Directory):
            not_a_directory(file.absolute_path)

        return file.list_children()

    def scandir(self, at_path: PathMock) -> ScandirIterator:
        file = self.get(at_path)

        if not isinstance(file, Directory):
            not_a_directory(file.absolute_path)

        return ScandirIterator(file)

    def rename(self, src_path: PathMock, dst_path: PathMock) -> None:
        destination = self.get(dst_path.parent)
        if not isinstance(destination, Directory):
            not_a_directory(destination.absolute_path)

        source = self.get(src_path)
        source.parent.delete(source.name)

        source.name = dst_path.name
        destination.set(source.name, source)

    def get(self, at_path: PathMock) -> File:
        path_parts = at_path.parts
        assert path_parts[0] == "/"

        file = self.root
        for part in path_parts[1:]:
            file = file.get(part)

        return file


class PathMock(Path):
    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        return object.__new__(cls)

    def __init__(self, *args: str, file_system: FileSystem) -> None:
        self._raw_paths = args
        self.fs = file_system

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        return self.fs.get(self).stat(follow_symlinks=follow_symlinks)

    def iterdir(self) -> Generator[Self, None, None]:
        for file in self.fs.listdir(self):
            yield self._make_child_relpath(file.name)  # pyright: ignore[reportAttributeAccessIssue]

    def _scandir(self) -> ScandirIterator:
        return self.fs.scandir(self)

    def with_segments(self, *pathsegments) -> PathMock:
        return PathMock(*pathsegments, file_system=self.fs)

    def rename(self, target: str | os.PathLike) -> PathMock:
        target = self.with_segments(target)

        self.fs.rename(self, target)
        return target


if __name__ == "__main__":
    fs = FileSystem([FileSystem.D("a"), FileSystem.D("b", children=[FileSystem.F("c"), FileSystem.D("d")])])
    p = PathMock("/b", file_system=fs)
    for file in p.iterdir():
        print(file, file.is_dir())
