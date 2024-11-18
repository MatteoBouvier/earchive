from earchive.utils.path import FastPath


def test_fastpath_root():
    assert FastPath.from_str("/").str() == "/"


def test_fastpath_cwd():
    assert FastPath(absolute=False).str() == "."
    assert FastPath.from_str(".").str() == "."
    assert FastPath.from_str("./").str() == "."


def test_fastpath_parents_abs():
    p = FastPath.from_str("/foo/bar/setup.py")
    assert list(p.parents) == [FastPath.from_str("/foo/bar"), FastPath.from_str("/foo"), FastPath.from_str("/")]


def test_fastpath_parents_rel():
    p = FastPath.from_str("foo/bar/setup.py")
    assert list(p.parents) == [FastPath.from_str("foo/bar"), FastPath.from_str("foo"), FastPath.from_str(".")]


def test_fastpath_join_root():
    assert FastPath.from_str("foo/bar") / "/" == FastPath(absolute=True)


def test_fastpath_join_dot():
    assert FastPath.from_str("foo/bar") / "." == FastPath.from_str("foo/bar")


def test_fastpath_join_other():
    assert FastPath.from_str("foo/bar") / "baz/test.py" == FastPath.from_str("foo/bar/baz/test.py")
