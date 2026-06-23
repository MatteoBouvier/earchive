import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from earchive.commands.check.config import Config, parse_config
from earchive.commands.check.config.config import CliConfig
from earchive.commands.check.config.parse import _update_config_from_file  # pyright: ignore[reportPrivateUsage]
from earchive.commands.check.config.names import (
    ASCII,
    BEHAVIOR_CONFIG,
    CHECK_CHARACTERS_CONFIG,
    CHECK_CONFIG,
    ConfigDict,
)
from earchive.commands.check.names import (
    Check,
    PathCharactersReplaceDiagnostic,
    PathEmptyDiagnostic,
    PathErrorDiagnostic,
)
from earchive.commands.check.utils import Counter, fix_invalid_paths, invalid_paths
from earchive.names import COLLISION
from earchive.utils.fs import FS
from earchive.utils.os import OS
from earchive.utils.path import FastPath
from earchive.utils.progress import NoBar
from tests.mock_filesystem import FileSystem as fs
from tests.mock_filesystem import PathMock


def DEFAULT_CONFIG(path: PathMock) -> ConfigDict:
    return ConfigDict(
        behavior=BEHAVIOR_CONFIG(collision=COLLISION.INCREMENT, dry_run=False),
        check=CHECK_CONFIG(
            run=Check.NO_CHECK,
            path=path,
            operating_system=OS.WINDOWS,
            file_system=FS.NTFS_win32,
            base_path_length=0,
            max_path_length=260,
            max_name_length=255,
            characters=CHECK_CHARACTERS_CONFIG(extra_invalid=re.compile(""), replacement="_", ascii=ASCII.NO),
        ),
        rename=[],
        exclude=set(),
    )


cli_cfg = CliConfig.from_dict({"fs": FS.NTFS_win32, "os": OS.WINDOWS})


def test_config_should_get_max_path_length():
    config = parse_config(None, cli_cfg, Path("."), None, None, set())

    config.check.max_path_length


def test_should_parse_config_special_characters_extra():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[check.characters]\nextra_invalid = "- "\n')

    config = parse_config(Path(config_file.name), cli_cfg, Path("."), None, None, set())

    assert config.check.characters.extra_invalid.pattern == "- "

    Path(config_file.name).unlink()


def test_should_parse_checks():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[check]\nrun = ["CHARACTERS", "LENGTH"]\n')

    config = parse_config(Path(config_file.name), cli_cfg, Path("."), None, None, set())

    assert config.check.run == Check.CHARACTERS | Check.LENGTH

    Path(config_file.name).unlink()


def test_should_find_empty_directories():
    path = PathMock(absolute=True, file_system=fs([fs.D("a"), fs.D("b", [fs.F("c"), fs.D("d")])]))

    invalids = list(invalid_paths(Config.from_dict(DEFAULT_CONFIG(path)), checks=Check.EMPTY))

    assert invalids == [
        PathEmptyDiagnostic(FastPath.from_str("/b/d", OS.LINUX)),
        PathEmptyDiagnostic(FastPath.from_str("/a", OS.LINUX)),
    ]


def test_should_convert_permission_denied_error_to_diagnostic():
    path = PathMock(absolute=True, file_system=fs([fs.D("a"), fs.D("b", mode=0o000)]))

    invalids = list(invalid_paths(Config.from_dict(DEFAULT_CONFIG(path)), checks=Check.NO_CHECK))

    assert len(invalids) == 1
    assert isinstance(invalids[0], PathErrorDiagnostic)
    assert invalids[0].path == FastPath.from_str("/b", OS.LINUX)
    assert type(invalids[0].error) is PermissionError
    assert invalids[0].error.filename == "/b"


def test_should_rename_file_with_dots():
    path = PathMock(absolute=True, file_system=fs([fs.F("file.path.dots.txt")]))

    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b"""[check]
run = ["CHARACTERS"]

[check.characters]
extra_invalid = "."
replacement = "_"
""")

    config = DEFAULT_CONFIG(path)
    _update_config_from_file(config, Path(config_file.name))
    config = Config.from_dict(config)

    diagnostics = list(fix_invalid_paths(config, NoBar, Counter()))

    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], PathCharactersReplaceDiagnostic)
    assert diagnostics[0].path == FastPath.from_str("/file.path.dots.txt", OS.LINUX)
    assert diagnostics[0].new_path == FastPath.from_str("/file_path_dots.txt", OS.LINUX)

    Path(config_file.name).unlink()


def test_rename_should_avoid_name_collision():
    path = PathMock(absolute=True, file_system=fs([fs.F("b?"), fs.D("b_", [fs.F("c>test.txt"), fs.F("c_test.txt")])]))

    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b"""[check]
run = ["CHARACTERS"]
""")

    config = DEFAULT_CONFIG(path)
    _update_config_from_file(config, Path(config_file.name))
    config = Config.from_dict(config)

    diagnostics = list(fix_invalid_paths(config, NoBar, Counter()))

    assert len(diagnostics) == 2
    assert isinstance(diagnostics[0], PathCharactersReplaceDiagnostic)
    assert isinstance(diagnostics[1], PathCharactersReplaceDiagnostic)
    assert diagnostics[0].path == FastPath.from_str("/b_/c>test.txt", OS.LINUX)
    assert diagnostics[0].new_path == FastPath.from_str("/b_/c_test(1).txt", OS.LINUX)
    assert diagnostics[1].path == FastPath.from_str("/b?", OS.LINUX)
    assert diagnostics[1].new_path == FastPath.from_str("/b_(1)", OS.LINUX)
