import os
from pathlib import Path


def fix_last_modified_timestamp(path: Path, reference_path: Path | None = None, fix_under: int = 315525600):
    if reference_path is None:
        reference_path = path

    if path.is_dir():
        files = path.iterdir()
        reference_files = reference_path.iterdir()

    else:
        files = [path]
        reference_files = [reference_path]

    for file, reference_file in zip(files, reference_files):
        file_info = os.stat(file)
        reference_file_info = os.stat(reference_file)

        if file_info.st_mtime <= fix_under:
            print(f"fix timestamp for {file}")
            os.utime(file, (file_info.st_atime, reference_file_info.st_mtime))
