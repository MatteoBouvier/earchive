import re
import sys
from typing import NamedTuple

from earchive.utils.fs import FS


class _ConfigOneFileSystem(NamedTuple):
    invalid_characters: re.Pattern[str]
    reserved_names: list[re.Pattern[str]]
    max_path_length: int
    max_name_length: int


CONFIG_FILE_SYSTEMS: dict[FS, _ConfigOneFileSystem] = {
    FS.NTFS_posix: _ConfigOneFileSystem(
        invalid_characters=re.compile(r"[/\0]"),
        reserved_names=[
            re.compile(r"\$(Mft|MftMirr|LogFile|Volume|AttrDef|Bitmap|Boot|BadClus|Secure|Upcase|Extend)"),
            re.compile(r"pagefile\.sys"),
        ],
        max_path_length=32767,
        max_name_length=255,
    ),
    FS.NTFS_win32: _ConfigOneFileSystem(
        invalid_characters=re.compile(r'[<>:"/\\?*\|\x00-\x1F]'),
        reserved_names=[
            re.compile(r"\$(Mft|MftMirr|LogFile|Volume|AttrDef|Bitmap|Boot|BadClus|Secure|Upcase|Extend)"),
            re.compile(r"pagefile\.sys"),
        ],
        max_path_length=260,
        max_name_length=255,
    ),
    FS.EXT4: _ConfigOneFileSystem(
        invalid_characters=re.compile(r"[/\0]"), reserved_names=[], max_path_length=sys.maxsize, max_name_length=255
    ),
}
