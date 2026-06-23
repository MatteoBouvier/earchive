import os
import platform
from pathlib import Path

from rich.console import Console
from rich.rule import Rule

from earchive.utils.fs import get_file_system
from earchive.utils.os import get_operating_system

console = Console()


def analyze_path(path: Path) -> None:
    if platform.system() == "Windows":
        max_path_length = "260?"
        max_filename_length = "255?"

    else:
        max_path_length = str(os.pathconf(path, "PC_PATH_MAX"))  # type: ignore[attr-defined,unused-ignore]
        max_filename_length = str(os.pathconf(path, "PC_NAME_MAX"))  # type: ignore[attr-defined,unused-ignore]

    attributes = dict(
        max_path_length=max_path_length,
        max_filename_length=max_filename_length,
        file_system=get_file_system(path),
        operating_system=get_operating_system(path),
    )

    console.print(Rule(str(path)), width=40)

    for attr, value in attributes.items():
        console.print(f"{attr:<30}{value:>10}")
