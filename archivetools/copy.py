import shutil
from pathlib import Path


def _copy_as_empty(_: str, dst: str) -> None:
    Path(dst).touch()


def copy_structure(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, copy_function=_copy_as_empty, dirs_exist_ok=True)
