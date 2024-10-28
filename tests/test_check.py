from pathlib import Path
from tempfile import NamedTemporaryFile

from earchive.check.check import Counter, _rename
from earchive.check.names import CTX, Action, Check, PathDiagnostic
from earchive.check.parse_config import DEFAULT_CONFIG, FS, Config, parse_config
from earchive.check.utils import invalid_paths
from tests.mock_filesystem import FileSystem as fs
from tests.mock_filesystem import PathMock


def test_should_parse_config_special_characters_extra():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[special_characters]\nextra = "- "\n')

    config = parse_config(Path(config_file.name))

    assert config.special_characters["extra"] == "- "

    Path(config_file.name).unlink()


def test_should_find_empty_directories():
    path = PathMock("/", file_system=fs([fs.D("a"), fs.D("b", [fs.F("c"), fs.D("d")])]))

    ctx = CTX(DEFAULT_CONFIG, FS.windows)
    invalids = list(invalid_paths(path, ctx, checks=Check.EMPTY))

    assert invalids == [PathDiagnostic(Check.EMPTY, Path("/b/d")), PathDiagnostic(Check.EMPTY, Path("/a"))]


def test_should_convert_permission_denied_error_to_diagnostic():
    path = PathMock("/", file_system=fs([fs.D("a"), fs.D("b", mode=0o000)]))

    ctx = CTX(DEFAULT_CONFIG, FS.windows)
    invalids = list(invalid_paths(path, ctx, checks=Check.NO_CHECK))

    assert len(invalids) == 1
    assert invalids[0].kind == Action.ERROR
    assert invalids[0].path == Path("/b")
    assert type(invalids[0].error) is PermissionError
    assert invalids[0].error.filename == "/b"


def test_should_rename_file_with_dots():
    path = PathMock("/", file_system=fs([fs.F("file.path.dots.txt")]))

    config = Config(
        windows={"special_characters": r"<>:/\\|?*", "max_path_length": 255},
        special_characters={"extra": ".", "replacement": "_"},
        rename=[],
        exclude=[],
    )
    ctx = CTX(config, FS.windows)
    diagnostics = list(_rename(path, ctx, Check.CHARACTERS, Counter()))

    assert len(diagnostics) == 1
    assert diagnostics[0].kind == Check.CHARACTERS
    assert diagnostics[0].path == Path("/file.path.dots.txt")
    assert diagnostics[0].new_path == Path("/file_path_dots.txt")
