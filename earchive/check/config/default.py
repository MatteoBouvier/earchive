from typing import Any
from earchive.check.config.names import FS, HEADER
from earchive.check.names import Check


DEFAULT_CHECK_RUN = Check.CHARACTERS | Check.LENGTH
DEFAULT_CHECK_FS = FS.WINDOWS
DEFAULT_CHECK_BASE_CHAR_LEN = 0
DEFAULT_CHECK_CHARACTERS = dict(extra="", replacement="_")

DEFAULT_FILE_SYSTEMS = {FS.WINDOWS: dict(special_characters=r"<>:/\\?*", max_path_length=255)}


DEFAULT_CONFIG: dict[HEADER, Any] = {
    HEADER.CHECK: {
        HEADER.CHECK_RUN: DEFAULT_CHECK_RUN,
        HEADER.CHECK_FILE_SYSTEM: DEFAULT_CHECK_FS,
        HEADER.CHECK_BASE_PATH_LENGTH: DEFAULT_CHECK_BASE_CHAR_LEN,
        HEADER.CHECK_CHARACTERS: DEFAULT_CHECK_CHARACTERS,
    },
    HEADER.FILE_SYSTEMS: {fs: fs_config for fs, fs_config in DEFAULT_FILE_SYSTEMS.items()},
    HEADER.RENAME: [],
    HEADER.EXCLUDE: [],
}
