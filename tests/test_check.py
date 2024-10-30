from pathlib import Path
from tempfile import NamedTemporaryFile

from earchive.check.check import Counter, _rename
from earchive.check.names import Action, Check, PathDiagnostic
from earchive.check.config import FS, Config, parse_config, HEADER
from earchive.check.utils import invalid_paths
from tests.mock_filesystem import FileSystem as fs
from tests.mock_filesystem import PathMock

DEFAULT_CONFIG = {
    HEADER.CHECK: {
        HEADER.CHECK_RUN: Check.NO_CHECK,
        HEADER.CHECK_FILE_SYSTEM: FS.WINDOWS,
        HEADER.CHECK_BASE_PATH_LENGTH: 0,
        HEADER.CHECK_CHARACTERS: dict(extra="", replacement="_"),
    },
    HEADER.FILE_SYSTEMS: {FS.WINDOWS: dict(special_characters=r"<>:/\\|?*", max_path_length=255)},
    HEADER.RENAME: [],
    HEADER.EXCLUDE: [],
}


def test_config_should_get_max_path_length():
    config = parse_config(None, FS.WINDOWS, None, None)

    assert config.get_max_path_length() == 255


def test_should_parse_config_special_characters_extra():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[check.characters]\nextra = "- "\n')

    config = parse_config(Path(config_file.name), FS.WINDOWS, None, None)

    assert config.check.characters.extra == "- "

    Path(config_file.name).unlink()


def test_should_parse_checks():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b"[check]\nrun = CHARACTERS LENGTH\n")

    config = parse_config(Path(config_file.name), FS.WINDOWS, None, None)

    assert config.check.run == Check.CHARACTERS | Check.LENGTH

    Path(config_file.name).unlink()


def test_should_find_empty_directories():
    path = PathMock("/", file_system=fs([fs.D("a"), fs.D("b", [fs.F("c"), fs.D("d")])]))

    invalids = list(invalid_paths(path, Config.from_dict(DEFAULT_CONFIG), checks=Check.EMPTY))

    assert invalids == [PathDiagnostic(Check.EMPTY, Path("/b/d")), PathDiagnostic(Check.EMPTY, Path("/a"))]


def test_should_convert_permission_denied_error_to_diagnostic():
    path = PathMock("/", file_system=fs([fs.D("a"), fs.D("b", mode=0o000)]))

    invalids = list(invalid_paths(path, Config.from_dict(DEFAULT_CONFIG), checks=Check.NO_CHECK))

    assert len(invalids) == 1
    assert invalids[0].kind == Action.ERROR
    assert invalids[0].path == Path("/b")
    assert type(invalids[0].error) is PermissionError
    assert invalids[0].error.filename == "/b"


def test_should_rename_file_with_dots():
    path = PathMock("/", file_system=fs([fs.F("file.path.dots.txt")]))

    config = Config.from_dict(
        DEFAULT_CONFIG
        | {
            HEADER.CHECK: {
                HEADER.CHECK_RUN: Check.CHARACTERS,
                HEADER.CHECK_FILE_SYSTEM: FS.WINDOWS,
                HEADER.CHECK_BASE_PATH_LENGTH: 0,
                HEADER.CHECK_CHARACTERS: {"extra": ".", "replacement": "_"},
            }
        }
    )
    diagnostics = list(_rename(path, config, Counter()))

    assert len(diagnostics) == 1
    assert diagnostics[0].kind == Check.CHARACTERS
    assert diagnostics[0].path == Path("/file.path.dots.txt")
    assert diagnostics[0].new_path == Path("/file_path_dots.txt")
