import sys
from enum import StrEnum, auto
from pathlib import Path
from typing import Self, override


class OS(StrEnum):
    AUTO = auto()
    WINDOWS = auto()
    LINUX = auto()

    @override
    @classmethod
    def _missing_(cls, value: object) -> Self:
        if value == "win32":
            return cls("windows")

        return super()._missing_(value)


def get_operating_system(path: Path) -> OS:
    # TODO: get OS of distant server
    del path

    return OS(sys.platform)
