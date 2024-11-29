from __future__ import annotations

import os
from collections.abc import Generator
from glob import glob
from pathlib import Path
from typing import cast, override

from typing_extensions import Callable

from earchive.names import COLLISION
from earchive.utils.os import OS


DRIVE = Path.home().drive


class FastPath(os.PathLike[str]):
    def __init__(self, *segments: str, absolute: bool, platform: OS, drive: str) -> None:
        self.segments: tuple[str, ...] = segments
        self._absolute: bool = absolute
        self.platform: OS = platform
        self.drive: str = drive

    @classmethod
    def from_str(cls, path: str, platform: OS) -> FastPath:
        if path == "/":
            return FastPath(absolute=True, platform=platform, drive=DRIVE)

        if path == ".":
            return FastPath(absolute=False, platform=platform, drive="")

        if path[1] == ":":
            drive, path = path[:2], path[2:]

        else:
            drive = DRIVE

        if path[0] == "/":
            return FastPath(*FastPath.get_segments(path), absolute=True, platform=platform, drive=drive)

        else:
            return FastPath(*FastPath.get_segments(path), absolute=False, platform=platform, drive="")

    @classmethod
    def from_path(cls, path: Path, platform: OS) -> FastPath:
        if str(path) == "/":
            return FastPath(absolute=True, platform=platform, drive=path.drive)

        if str(path) == ".":
            return FastPath(absolute=False, platform=platform, drive="")

        if path.is_absolute():
            return FastPath(*cast(list[str], path._tail), absolute=True, platform=platform, drive=path.drive)  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

        else:
            return FastPath(*cast(list[str], path._tail), absolute=True, platform=platform, drive="")  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

    @staticmethod
    def get_segments(path: str) -> list[str]:
        if path.startswith("./"):
            path = path[2:]

        return [s for s in path.strip("/").split("/") if s not in ("", ".")]

    @override
    def __repr__(self) -> str:
        return self.as_str()

    @override
    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, FastPath):
            return False

        return self.segments == value.segments

    def __len__(self) -> int:
        path_len = sum(map(len, self.segments))

        if self.platform is OS.WINDOWS:
            # account for windows' extra path elements : D:/<path><NUL>
            #                                            ^^ <-- <DRIVE>
            path_len += len(self.drive) + 2

        return path_len

    def __truediv__(self, other: str) -> FastPath:
        if other == "/":
            return FastPath(absolute=True, platform=self.platform, drive=self.drive)

        if other == ".":
            return self

        return FastPath(
            *self.segments, *other.split("/"), absolute=self._absolute, platform=self.platform, drive=self.drive
        )

    @override
    def __hash__(self) -> int:
        return hash((self.segments, self._absolute))

    @override
    def __fspath__(self) -> str:
        return self.as_str()

    @property
    def parent(self) -> FastPath:
        return FastPath(*self.segments[:-1], absolute=self._absolute, platform=self.platform, drive=self.drive)

    @property
    def parents(self) -> Generator[FastPath, None, None]:
        segments = list(self.segments[:-1])
        while len(segments):
            yield FastPath(*segments, absolute=self._absolute, platform=self.platform, drive=self.drive)
            segments.pop(-1)

        yield FastPath(absolute=self._absolute, platform=self.platform, drive=self.drive)

    @property
    def name(self) -> str:
        if not len(self.segments):
            return self.as_str()
        return self.segments[-1]

    @property
    def stem(self) -> str:
        if not len(self.segments):
            return ""

        name = self.segments[-1]

        dot_idx = name.rfind(".")
        if dot_idx == -1:
            return name

        return name[:dot_idx]

    @property
    def suffix(self) -> str:
        if not len(self.segments):
            return ""

        name = self.segments[-1]

        dot_idx = name.rfind(".")
        if dot_idx == -1:
            return ""

        return name[dot_idx:]

    def is_dir(self) -> bool:
        return os.path.isdir(self)

    def is_file(self) -> bool:
        return os.path.isfile(self)

    def exists(self) -> bool:
        return os.path.exists(self)

    def is_absolute(self) -> bool:
        return self._absolute

    def as_str(self) -> str:
        if not len(self.segments):
            return "/" if self._absolute else "."

        repr_ = "/".join(self.segments)
        return "/" + repr_ if self._absolute else "./" + repr_

    def walk(
        self, top_down: bool = True, on_error: Callable[[OSError], None] | None = None, follow_symlinks: bool = False
    ) -> Generator[tuple[FastPath, list[str], list[str]], None, None]:
        if top_down:
            yield self.parent, [self.name] if self.is_dir() else [], [self.name] if self.is_file() else []

        for root, dirs, files in os.walk(self, top_down, on_error, follow_symlinks):
            yield FastPath.from_str(root, platform=self.platform), dirs, files

        if not top_down:
            yield self.parent, [self.name] if self.is_dir() else [], [self.name] if self.is_file() else []

    def with_stem(self, stem: str) -> FastPath:
        return FastPath(
            *self.segments[:-1], stem + self.suffix, absolute=self._absolute, platform=self.platform, drive=self.drive
        )

    def rename(self, target: FastPath, collision: COLLISION, do: bool = True) -> tuple[bool, FastPath]:
        if target.exists():
            if collision is COLLISION.SKIP:
                return (False, self)

            # add `(<nb>)` to file name
            next_nb = (
                max([int(g.stem.split("(")[-1][:-1]) for g in self.parent.glob(self.stem + "(*)" + self.suffix)] + [0])
                + 1
            )
            target = target.with_stem(f"{target.stem}({next_nb})")

        if do:
            os.rename(self, target)
        return (True, target)

    def rmdir(self) -> None:
        os.rmdir(self)

    def glob(self, pattern: str) -> Generator[FastPath, None, None]:
        yield from map(
            lambda p: FastPath.from_str(p, platform=self.platform),
            glob(pattern, root_dir=self),
        )
