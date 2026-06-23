import re
from typing import NamedTuple

from earchive.utils.os import OS


class _ConfigOneOperatingSystem(NamedTuple):
    invalid_characters: re.Pattern[str]
    invalid_names: list[re.Pattern[str]]
    reserved_names: list[re.Pattern[str]]


CONFIG_OPERATING_SYSTEMS: dict[OS, _ConfigOneOperatingSystem] = {
    OS.WINDOWS: _ConfigOneOperatingSystem(
        invalid_characters=re.compile(r'[<>:"/\\?*\|\x00-\x1F]'),  # ASCII 0 -> 31 (0x1F)
        invalid_names=[re.compile(r"[ |\.]$")],  # ends with <space> of .
        reserved_names=[
            re.compile(
                r"^(CON|PRN|AUX|NUL|COM[0-9|¹|²|³]?|LPT[0-9|¹|²|³]?)(\..*)?$", re.IGNORECASE
            ),  # name (with any extension)
        ],
    ),
    OS.LINUX: _ConfigOneOperatingSystem(
        invalid_characters=re.compile(r"[/\x00]"),
        invalid_names=[],
        reserved_names=[re.compile(r"^\.(\.)?$")],  # . or ..
    ),
}
