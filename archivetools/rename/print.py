from __future__ import annotations
import os
import re
from pathlib import Path
from typing import NamedTuple

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text

from archivetools.rename.names import CTX, INVALID_PATH_DATA, Check

console = Console()

ERROR_STYLE = "bold red"
SUCCESS_STYLE = "bold green"


class Grid:
    def __init__(self, ctx: CTX) -> None:
        self.ctx = ctx
        self.rows: list[INVALID_PATH_DATA] = []
        self.console_width = int(os.popen("stty size", "r").read().split()[1])

    @staticmethod
    def _repr_matches(file_name: str, matches: list[re.Match[str]]) -> tuple[Text, Text]:
        txt_path: list[str | tuple[str, str]] = ["/"]
        txt_under: list[str | tuple[str, str]] = [" "]
        last_offset = 0

        for m in matches:
            txt_path.append(file_name[last_offset : m.start()])
            txt_under.append(("~" * (m.start() - last_offset), ERROR_STYLE))

            last_offset = m.end()

            txt_path.append((file_name[m.start() : m.end()], ERROR_STYLE))
            txt_under.append(("^", ERROR_STYLE))

        txt_path.append(file_name[last_offset:])
        txt_under.append(("~" * (len(file_name) - last_offset) + " invalid characters", ERROR_STYLE))

        return Text.assemble(*txt_path), Text.assemble(*txt_under)

    @staticmethod
    def _repr_too_long(file_name: str, path_len: int, max_len: int) -> tuple[Text, Text]:
        no_color_len = max(0, len(file_name) - path_len + max_len)

        txt_path = ("/", file_name[:no_color_len], (file_name[no_color_len:], ERROR_STYLE))
        txt_under = (
            " ",
            " " * no_color_len,
            ("~" * (path_len - max_len) + f" path is too long ({path_len} > {max_len})", ERROR_STYLE),
        )

        return Text.assemble(*txt_path), Text.assemble(*txt_under)

    def clamp(self, txt: Text, max_width: int) -> tuple[Text, int]:
        if len(txt) > max_width:
            txt.align("left", max_width)
            txt.append("…")

            return txt, max_width + 1

        return txt, len(txt)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        for row in self.rows:
            match row:
                case Check.CHARACTERS, path, matches:
                    path_max_width = self.console_width - 9 - len(path.name)
                    repr_above, repr_under = self._repr_matches(path.name, matches)

                    root, offset = self.clamp(Text(str(path.parent)), path_max_width)

                    yield Text.assemble("[E:INV] ", root, repr_above)
                    yield Text.assemble("        ", " " * offset, repr_under)

                case Check.LENGTH, path:
                    max_path_len = self.ctx.config.get_max_path_length(self.ctx.os)
                    repr_above, repr_under = self._repr_too_long(path.name, len(str(path)), max_path_len)

                    path_max_width = self.console_width - 9 - len(repr_under)
                    root, offset = self.clamp(Text(str(path.parent)), path_max_width)

                    yield Text.assemble("[E:LEN] ", root, repr_above)
                    yield Text.assemble("        ", " " * offset, repr_under)

                case Check.EMPTY, path:
                    error_repr = f"/{path.name}/∅ directory contains no files"
                    path_max_width = self.console_width - 9 - len(error_repr)

                    root, _ = self.clamp(Text(str(path.parent)), path_max_width)

                    yield Text.assemble("[E:EMP] ", root, (error_repr, ERROR_STYLE))

                case _:
                    raise RuntimeError("Found invalid kind")

    def add_row(self, row: INVALID_PATH_DATA) -> None:
        self.rows.append(row)
