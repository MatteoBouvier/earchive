import itertools as it
from enum import StrEnum, auto
from typing import Self, override

import psutil

from earchive.utils.path import FastPath


class FS(StrEnum):
    AUTO = auto()
    NTFS_posix = auto()
    NTFS_win32 = auto()
    EXT4 = auto()

    @override
    @classmethod
    def _missing_(cls, value: object) -> Self:
        if value == "ntfs":
            return cls("ntfs_win32")

        return super()._missing_(value)


def get_file_system(path: FastPath) -> FS:
    path = path.resolve()
    partitions = {part.mountpoint: part.fstype for part in psutil.disk_partitions()}

    for p in it.chain([path], path.parents):
        if fs := partitions.get(str(p), None):
            return FS(fs)

    raise OSError(f"Could not determine file system of path '{path}'")
