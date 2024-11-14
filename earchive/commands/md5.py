import hashlib
import sys
from pathlib import Path

BUF_SIZE = 65536  # 64kb chunks


def _get_file_hash(path: Path) -> str:
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)

    return md5.hexdigest()


def compute_hash(path: Path) -> int:
    if path.is_file():
        print(f"{_get_file_hash(path)}\t{path}")
        return 0

    for sub_path in path.iterdir():
        compute_hash(sub_path)

    return 0


if __name__ == "__main__":
    path = Path(sys.argv[1])
    if not path.exists():
        raise OSError(f"File {path} does not exist")

    sys.exit(compute_hash(path))
