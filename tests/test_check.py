from pathlib import Path
from tempfile import NamedTemporaryFile
from earchive.check.parse_config import parse_config


def test_should_parse_config_special_characters_extra():
    with NamedTemporaryFile(delete=False) as config_file:
        config_file.write(b'[special_characters]\nextra = "- "\n')

    config = parse_config(Path(config_file.name))

    assert config.special_characters["extra"] == "- "

    Path(config_file.name).unlink()
