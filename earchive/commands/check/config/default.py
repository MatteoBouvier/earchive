from pathlib import Path
import re

from earchive.commands.check.config.names import (
    ASCII,
    BEHAVIOR_CONFIG,
    CHECK_CHARACTERS_CONFIG,
    CHECK_CONFIG,
    COLLISION,
    ConfigDict,
)
from earchive.commands.check.names import Check
from earchive.utils.fs import FS
from earchive.utils.os import OS
from earchive.utils.path import FastPath

DEFAULT_CHECK_RUN = Check.CHARACTERS | Check.LENGTH
DEFAULT_CHECK_OS = OS.AUTO
DEFAULT_CHECK_FS = FS.AUTO
DEFAULT_CHECK_BASE_PATH_LEN: int = -1
DEFAULT_CHECK_MAX_PATH_LEN: int = -1
DEFAULT_CHECK_MAX_NAME_LEN: int = -1
DEFAULT_CHECK_CHARACTERS = CHECK_CHARACTERS_CONFIG(
    extra_invalid=re.compile(""),
    replacement="_",
    ascii=ASCII.NO,
)


def DEFAULT_CONFIG(check_path: Path) -> ConfigDict:
    return ConfigDict(
        behavior=BEHAVIOR_CONFIG(collision=COLLISION.INCREMENT, dry_run=False),
        check=CHECK_CONFIG(
            run=DEFAULT_CHECK_RUN,
            path=FastPath.from_str(str(check_path), DEFAULT_CHECK_OS),
            operating_system=DEFAULT_CHECK_OS,
            file_system=DEFAULT_CHECK_FS,
            base_path_length=DEFAULT_CHECK_BASE_PATH_LEN,
            max_path_length=DEFAULT_CHECK_MAX_PATH_LEN,
            max_name_length=DEFAULT_CHECK_MAX_NAME_LEN,
            characters=DEFAULT_CHECK_CHARACTERS,
        ),
        rename=[],
        exclude=set(),
    )
