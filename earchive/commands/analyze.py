import os
import sys

from rich.console import Console
from rich.rule import Rule

from earchive.utils.fs import get_file_system
from earchive.utils.os import get_operating_system
from earchive.utils.path import FastPath

console = Console()


def analyze_path(path: FastPath) -> None:
    attributes = dict(
        max_path_length="260?" if sys.platform == "win32" else os.pathconf(path, "PC_PATH_MAX"),
        max_filename_length="255?" if sys.platform == "win32" else os.pathconf(path, "PC_NAME_MAX"),
        file_system=get_file_system(path),
        operating_system=get_operating_system(path),
    )

    console.print(Rule(str(path)), width=40)

    for attr, value in attributes.items():
        console.print(f"{attr:<30}{value:>10}")
