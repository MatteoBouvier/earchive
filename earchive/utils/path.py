from __future__ import annotations

import os
from collections.abc import Generator
from glob import glob
from typing import override

from typing_extensions import Callable

from earchive.names import COLLISION
from earchive.utils.os import OS


def cache[FastPath, R](func: Callable[[FastPath], R]) -> Callable[[FastPath], R]:
    """Cache for ONE element, works for functions that take no parameters (except self)"""
    _cache: dict[FastPath, R] = dict()

    def wrapper(self: FastPath) -> R:
        nonlocal _cache
        return _cache.setdefault(self, func(self))

    return wrapper


class FastPath(os.PathLike[str]):
    def __init__(self, *segments: str, absolute: bool, platform: OS) -> None:
        self.segments: tuple[str, ...] = segments
        self._absolute: bool = absolute
        self.platform: OS = platform

    @classmethod
    def from_str(cls, path: str, platform: OS) -> FastPath:
        if path == "/":
            return FastPath(absolute=True, platform=platform)

        if path == ".":
            return FastPath(absolute=False, platform=platform)

        return FastPath(*FastPath.get_segments(path), absolute=path[0] == "/", platform=platform)

    @staticmethod
    def get_segments(path: str) -> list[str]:
        if path.startswith("./"):
            path = path[2:]

        return [s for s in path.strip("/").split("/") if s not in ("", ".")]

    @override
    def __repr__(self) -> str:
        return self.str()

    @override
    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, FastPath):
            return False

        return self.segments == value.segments

    # @cache
    def __len__(self) -> int:
        path_len = sum(map(len, self.segments))

        if self.platform is OS.WINDOWS:
            # account for windows' extra path elements : <DRIVE>:/<path><NUL> --> 4 less characters
            path_len += 4

        return path_len

    def __truediv__(self, other: str) -> FastPath:
        return FastPath(*self.segments, other, absolute=self._absolute, platform=self.platform)

    @override
    def __hash__(self) -> int:
        return hash((self.segments, self._absolute))

    @override
    def __fspath__(self) -> str:
        return self.str()

    @property
    def parent(self) -> FastPath:
        return FastPath(*self.segments[:-1], absolute=self._absolute, platform=self.platform)

    @property
    def parents(self) -> Generator[FastPath, None, None]:
        segments = list(self.segments[:-1])
        while len(segments):
            yield FastPath(*segments, absolute=self._absolute, platform=self.platform)
            segments.pop(-1)

        yield FastPath(absolute=self._absolute, platform=self.platform)

    @property
    def name(self) -> str:
        if not len(self.segments):
            return self.str()
        return self.segments[-1]

    @property
    # @cache
    def stem(self) -> str:
        if not len(self.segments):
            return ""

        name = self.segments[-1]

        dot_idx = name.rfind(".")
        if dot_idx == -1:
            return name

        return name[:dot_idx]

    @property
    # @cache
    def suffix(self) -> str:
        if not len(self.segments):
            return ""

        name = self.segments[-1]

        dot_idx = name.rfind(".")
        if dot_idx == -1:
            return ""

        return name[dot_idx:]

    # @cache
    def is_dir(self) -> bool:
        return os.path.isdir(self)

    # @cache
    def is_file(self) -> bool:
        return os.path.isfile(self)

    def exists(self) -> bool:
        return os.path.exists(self)

    def is_absolute(self) -> bool:
        return self._absolute

    # @cache
    def str(self) -> str:
        if not len(self.segments):
            return "/" if self._absolute else "."

        repr_ = "/".join(self.segments)
        return "/" + repr_ if self._absolute else "./" + repr_

    # def join(self, other: str) -> FastPath:
    #     if other == "/":
    #         return FastPath(absolute=True, platform=self.platform)
    #
    #     return FastPath(
    #         *self.segments,
    #         *FastPath.get_segments(other),
    #         absolute=self._absolute,
    #         platform=self.platform,
    #     )

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
            *self.segments[:-1],
            stem + self.suffix,
            absolute=self._absolute,
            platform=self.platform,
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

    def resolve(self, strict: bool = False) -> FastPath:
        return FastPath.from_str(os.path.realpath(self, strict=strict), platform=self.platform)
