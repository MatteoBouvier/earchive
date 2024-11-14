import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from earchive.commands.check.check import Counter, rename
from earchive.commands.check.config import Config, parse_config
from earchive.commands.check.config.config import CliConfig
from earchive.commands.check.config.names import ASCII, CHECK_CHARACTERS_CONFIG, CHECK_CONFIG, ConfigDict
from earchive.commands.check.names import (
    Check,
    PathCharactersReplaceDiagnostic,
    PathEmptyDiagnostic,
    PathErrorDiagnostic,
)
from earchive.commands.check.utils import invalid_paths
from earchive.utils.fs import FS
from earchive.utils.os import OS
from tests.mock_filesystem import FileSystem as fs
from tests.mock_filesystem import PathMock


def DEFAULT_CONFIG(path: PathMock) -> ConfigDict:
    return ConfigDict(
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
        exclude=[],
    )


cli_cfg = CliConfig.from_dict({"fs": FS.NTFS_win32, "os": OS.WINDOWS})


def test_config_should_get_max_path_length():
    config = parse_config(None, cli_cfg, Path(""), None, None, [])

    config.check.max_path_length


def test_should_parse_config_special_characters_extra():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[check.characters]\nextra_invalid = "- "\n')

    config = parse_config(Path(config_file.name), cli_cfg, Path(""), None, None, [])

    assert config.check.characters.extra_invalid.pattern == "- "

    Path(config_file.name).unlink()


def test_should_parse_checks():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[check]\nrun = ["CHARACTERS", "LENGTH"]\n')

    config = parse_config(Path(config_file.name), cli_cfg, Path(""), None, None, [])

    assert config.check.run == Check.CHARACTERS | Check.LENGTH

    Path(config_file.name).unlink()


def test_should_find_empty_directories():
    path = PathMock("/", file_system=fs([fs.D("a"), fs.D("b", [fs.F("c"), fs.D("d")])]))

    invalids = list(invalid_paths(Config.from_dict(DEFAULT_CONFIG(path)), checks=Check.EMPTY))

    assert invalids == [PathEmptyDiagnostic(Path("/b/d")), PathEmptyDiagnostic(Path("/a"))]


def test_should_convert_permission_denied_error_to_diagnostic():
    path = PathMock("/", file_system=fs([fs.D("a"), fs.D("b", mode=0o000)]))

    invalids = list(invalid_paths(Config.from_dict(DEFAULT_CONFIG(path)), checks=Check.NO_CHECK))

    assert len(invalids) == 1
    assert isinstance(invalids[0], PathErrorDiagnostic)
    assert invalids[0].path == Path("/b")
    assert type(invalids[0].error) is PermissionError
    assert invalids[0].error.filename == "/b"


def test_should_rename_file_with_dots():
    path = PathMock("/", file_system=fs([fs.F("file.path.dots.txt")]))

    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b"""[check]
run = ["CHARACTERS"]

[check.characters]
extra_invalid = "."
replacement = "_"
""")

    config = parse_config(Path(config_file.name), cli_cfg, path, None, None, [])

    diagnostics = list(rename(config, Counter()))

    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], PathCharactersReplaceDiagnostic)
    assert diagnostics[0].path == Path("/file.path.dots.txt")
    assert diagnostics[0].new_path == Path("/file_path_dots.txt")

    Path(config_file.name).unlink()
