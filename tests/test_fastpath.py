from earchive.utils.os import OS
from earchive.utils.path import FastPath


def test_fastpath_root():
    assert FastPath.from_str("/", OS.LINUX).str() == "/"


def test_fastpath_cwd():
    assert FastPath(absolute=False, platform=OS.LINUX, drive="").str() == "."
    assert FastPath.from_str(".", platform=OS.LINUX).str() == "."
    assert FastPath.from_str("./", platform=OS.LINUX).str() == "."


def test_fastpath_parents_abs():
    p = FastPath.from_str("/foo/bar/setup.py", OS.LINUX)
    assert list(p.parents) == [
        FastPath.from_str("/foo/bar", OS.LINUX),
        FastPath.from_str("/foo", OS.LINUX),
        FastPath.from_str("/", OS.LINUX),
    ]


def test_fastpath_parents_rel():
    p = FastPath.from_str("foo/bar/setup.py", OS.LINUX)
    assert list(p.parents) == [
        FastPath.from_str("foo/bar", OS.LINUX),
        FastPath.from_str("foo", OS.LINUX),
        FastPath.from_str(".", OS.LINUX),
    ]


def test_fastpath_join_root():
    assert FastPath.from_str("foo/bar", OS.LINUX) / "/" == FastPath(absolute=True, platform=OS.LINUX, drive="")


def test_fastpath_join_dot():
    assert FastPath.from_str("foo/bar", OS.LINUX) / "." == FastPath.from_str("foo/bar", OS.LINUX)


def test_fastpath_join_other():
    assert FastPath.from_str("foo/bar", OS.LINUX) / "baz/test.py" == FastPath.from_str("foo/bar/baz/test.py", OS.LINUX)
