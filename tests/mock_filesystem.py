from __future__ import annotations

import os
import re
import stat
from collections.abc import Generator, Iterator
from contextlib import AbstractContextManager
from dataclasses import InitVar, dataclass, field
from types import TracebackType
from typing import Callable, Never, Self, cast, final, override

from earchive.utils.path import FastPath

type StrPath = str | os.PathLike[str]


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

    @override
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

    def set_parent(self, dir: Directory) -> None:
        self._children_lookup[".."] = dir

    @property
    def parent(self) -> Directory:
        return cast(Directory, self._children_lookup[".."])

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        del follow_symlinks
        return os.stat_result((self.mode, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    @property
    def absolute_path(self) -> AbsPath:
        if self.name == "/":
            return AbsPath("/")

        abs_path = self.name
        file = self.parent

        while file.name != "/":
            abs_path = f"{file.name}/{abs_path}"
            file = file.parent

        return AbsPath("/" + abs_path)


@dataclass(repr=False)
class Directory(File):
    children: InitVar[list[File] | None] = None

    def __post_init__(self, children: list[File] | None):
        assert self.name != ""
        assert self.mode >= 0 and self.mode <= 262143
        assert stat.S_ISDIR(self.mode)

        if children is None:
            self._children_lookup: dict[str, File] = {}

        else:
            self._children_lookup = {file.name: file for file in children}

    @override
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


@final
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
        del follow_symlinks
        return isinstance(self.file, Directory)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        del follow_symlinks
        return not isinstance(self.file, Directory)

    def is_symlink(self) -> bool:
        return False

    def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
        return self.file.stat(follow_symlinks=follow_symlinks)

    def __fspath__(self) -> str:
        return self.path

    def is_junction(self) -> bool:
        return False


@final
class ScandirIterator(Iterator[DirEntry], AbstractContextManager):  # pyright: ignore[reportMissingTypeArgument]
    def __init__(self, file: Directory) -> None:
        self.file = file
        self.it = None

        if not self.file.mode & stat.S_IRUSR:
            permission_error(self.file.absolute_path)

    @override
    def __enter__(self) -> Self:
        self.it = iter(self.file.list_children())
        return super().__enter__()

    @override
    def __next__(self) -> DirEntry:
        assert self.it is not None
        return DirEntry(next(self.it))

    @override
    def __exit__(  # pyright: ignore[reportMissingSuperCall]
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> bool | None:
        self.it = None
        return

    def close(self) -> None:
        pass


def _set_parent(dir: Directory) -> None:
    for file in dir.list_children(ignore_mode=True):
        file.set_parent(dir)

        if isinstance(file, Directory):
            _set_parent(file)


@final
class FileSystem:
    def __init__(self, files: list[File], mode: int = 0o777) -> None:
        self.root = FileSystem.D("/", files, mode=mode)

        # add .. parent directory to all files
        self.root.set_parent(self.root)
        _set_parent(self.root)

    @override
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

    def walk(
        self,
        top: PathMock,
        top_down: bool = True,
        on_error: Callable[[OSError], None] | None = None,
        follow_symlinks: bool = False,
    ) -> Generator[tuple[PathMock, list[str], list[str]], None, None]:
        stack: list[PathMock | tuple[PathMock, list[str], list[str]]] = [top]
        # islink, join = path.islink, path.join

        while stack:
            top_ = stack.pop()
            if isinstance(top_, tuple):
                yield top_
                continue

            dirs: list[str] = []
            nondirs: list[str] = []
            walk_dirs: list[str] = []

            try:
                scandir_it = self.scandir(top_)
            except PermissionError as error:
                if on_error is not None:
                    on_error(error)
                continue

            cont = False
            with scandir_it:
                while True:
                    try:
                        try:
                            entry = next(scandir_it)
                        except StopIteration:
                            break
                    except PermissionError as error:
                        if on_error is not None:
                            on_error(error)
                        cont = True
                        break

                    is_dir = entry.is_dir()

                    if is_dir:
                        dirs.append(entry.name)
                    else:
                        nondirs.append(entry.name)

                    if not top_down and is_dir:
                        # Bottom-up: traverse into sub-directory, but exclude
                        # symlinks to directories if followlinks is False
                        if follow_symlinks:
                            walk_into = True
                        else:
                            try:
                                is_symlink = entry.is_symlink()
                            except OSError:
                                # If is_symlink() raises an OSError, consider the
                                # entry not to be a symbolic link, same behaviour
                                # as os.path.islink().
                                is_symlink = False
                            walk_into = not is_symlink

                        if walk_into:
                            walk_dirs.append(entry.path)
            if cont:
                continue

            if top_down:
                # Yield before sub-directory traversal if going top down
                yield top_, dirs, nondirs
                # Traverse into sub-directories
                for dirname in reversed(dirs):
                    new_path = top_ / dirname
                    # bpo-23605: os.path.islink() is used instead of caching
                    # entry.is_symlink() result during the loop on os.scandir() because
                    # the caller can replace the directory entry during the "yield"
                    # above.
                    if follow_symlinks:
                        stack.append(new_path)
            else:
                # Yield after sub-directory traversal if going bottom up
                stack.append((top_, dirs, nondirs))
                # Traverse into sub-directories
                for new_path in reversed(walk_dirs):
                    stack.append(PathMock.from_str(new_path, file_system=self))

    def rename(self, src_path: PathMock, dst_path: PathMock) -> None:
        destination = self.get(dst_path.parent)
        if not isinstance(destination, Directory):
            raise not_a_directory(destination.absolute_path)

        source = self.get(src_path)
        destination.set(dst_path.name, source)

        # /!\ steps above may raise exceptions, perform actual renaming after
        source.name = dst_path.name
        source.parent.delete(source.name)

    def get(self, at_path: PathMock) -> File:
        assert at_path.is_absolute()

        file = self.root
        for part in at_path.segments:
            file = file.get(part)

        return file


class PathMock(FastPath):
    def __init__(self, *segments: str, absolute: bool, file_system: FileSystem) -> None:
        super().__init__(*segments, absolute=absolute)
        self.fs: FileSystem = file_system

    @classmethod
    @override
    def from_str(cls, path: str, file_system: FileSystem) -> PathMock:
        fast_path = FastPath.from_str(path)
        return PathMock(*fast_path.segments, absolute=fast_path.is_absolute(), file_system=file_system)

    @override
    def __truediv__(self, other: str) -> PathMock:
        path = super().__truediv__(other)
        return PathMock(*path.segments, absolute=path._absolute, file_system=self.fs)

    @property
    @override
    def parent(self) -> PathMock:
        return PathMock(*self.segments[:-1], absolute=self._absolute, file_system=self.fs)

    @property
    @override
    def parents(self) -> Generator[PathMock, None, None]:
        segments = list(self.segments[:-1])
        while len(segments):
            yield PathMock(*segments, absolute=self._absolute, file_system=self.fs)
            segments.pop(-1)

        yield PathMock(absolute=self._absolute, file_system=self.fs)

    @override
    def is_dir(self) -> bool:
        return isinstance(self.fs.get(self), Directory)

    @override
    def is_file(self) -> bool:
        return not isinstance(self.fs.get(self), Directory)

    @override
    def exists(self) -> bool:
        try:
            self.fs.get(self)
        except FileNotFoundError:
            return False
        else:
            return True

    @override
    def walk(
        self, top_down: bool = True, on_error: Callable[[OSError], None] | None = None, follow_symlinks: bool = False
    ) -> Generator[tuple[PathMock, list[str], list[str]], None, None]:
        yield from self.fs.walk(self, top_down, on_error, follow_symlinks)

    @override
    def iterdir(self) -> list[str]:
        return [str(self.parent) + f.name for f in self.fs.listdir(self)]

    @override
    def with_stem(self, stem: str) -> PathMock:
        return PathMock(*self.segments[:-1], stem + self.suffix, absolute=self._absolute, file_system=self.fs)

    @override
    def rename(self, dst: str | os.PathLike[str]) -> None:
        dst = PathMock.from_str(str(dst), file_system=self.fs)
        self.fs.rename(self, dst)

    @override
    def glob(self, pattern: str) -> Generator[PathMock, None, None]:
        pattern = pattern.replace("(", r"\(").replace(")", r"\)").replace("*", ".*")
        for file in self.fs.listdir(self):
            if re.match(pattern, file.name):
                yield PathMock.from_str(file.absolute_path, file_system=self.fs)

    @override
    def resolve(self, strict: bool = False) -> PathMock:
        if self._absolute:
            return self
        raise NotImplementedError
        # return FastPath.from_str(os.path.realpath(self, strict=strict), file_system=self.fs)
