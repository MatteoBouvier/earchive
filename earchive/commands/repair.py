import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

MIN_DATE_TIMESTAMP = datetime(1979, 12, 31, 23, 0, 0).timestamp()


def fix_last_modified_timestamp(
    path: Path, reference_path: Path | None = None, fix_under_timestamp: float = MIN_DATE_TIMESTAMP
) -> None:
    if reference_path is None:
        reference_path = path

    if path.is_dir():
        files: Iterable[Path] = path.iterdir()
        reference_files: Iterable[Path] = reference_path.iterdir()

    else:
        files = [path]
        reference_files = [reference_path]

    for file, reference_file in zip(files, reference_files):
        file_info = os.stat(file)
        reference_file_info = os.stat(reference_file)

        if file_info.st_mtime <= fix_under_timestamp:
            print(f"fix timestamp for {file}")
            os.utime(file, (file_info.st_atime, reference_file_info.st_mtime))
