from __future__ import annotations

import os
import re
from itertools import chain
from pathlib import Path
from typing import Literal

from rich.console import Console, ConsoleOptions, RenderResult
from rich.text import Text

from earchive.check.names import CTX, Action, Check, OutputKind, PathDiagnostic
from earchive.check.parse_config import RegexPattern

console = Console(force_terminal=True, legacy_windows=False)

ERROR_STYLE = "bold red"
SUCCESS_STYLE = "bold green"
RENAME_STYLE = "bold magenta"


def _repr_regex_pattern(pattern: RegexPattern) -> str:
    flags = f"{'H\u02b0' if pattern.match.flags & re.IGNORECASE else ''}{'' if pattern.accent_sensitive else '^'}"
    if flags:
        flags = f"\u23a5{flags}"

    return f"{pattern.match.pattern}{flags}"


def _repr_matches(file_name: str, matches: list[re.Match[str]], new_path: Path | None) -> tuple[Text, list[Text]]:
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

    if new_path is not None:
        txt_path.append((f"\t==> {new_path.name}", SUCCESS_STYLE))

    return Text.assemble(*txt_path), [Text.assemble(*txt_under)]


def _repr_renames(
    file_name: str, patterns: list[tuple[RegexPattern, str]], new_path: Path | None
) -> tuple[Text, list[Text]]:
    first_p, first_new_name = patterns[0]

    txt_path: list[str | tuple[str, str]] = ["/", (file_name, RENAME_STYLE)]
    txt_under_list: list[list[str]] = [
        [" ", "~" * len(file_name), f" {_repr_regex_pattern(first_p)} -> {first_new_name}"]
    ]

    for p, new_name in patterns[1:]:
        match_repr = [" ", " " * (len(file_name)), f" {_repr_regex_pattern(p)} -> {new_name}"]
        txt_under_list.append(match_repr)

    if new_path is not None:
        txt_path.append((f"\t==> {new_path.name}", SUCCESS_STYLE))

    return Text.assemble(*txt_path), [Text.assemble(*txt_under, style=RENAME_STYLE) for txt_under in txt_under_list]


def _repr_too_long(file_name: str, path_len: int, max_len: int) -> tuple[Text, list[Text]]:
    no_color_len = max(0, len(file_name) - path_len + max_len)

    txt_path = ("/", file_name[:no_color_len], (file_name[no_color_len:], ERROR_STYLE))
    txt_under = (
        " ",
        " " * no_color_len,
        ("~" * (path_len - max_len) + f" path is too long ({path_len} > {max_len})", ERROR_STYLE),
    )

    return Text.assemble(*txt_path), [Text.assemble(*txt_under)]


class Grid:
    def __init__(self, ctx: CTX, kind: OutputKind, mode: Literal["check", "rename"]) -> None:
        self.ctx = ctx
        self.kind = kind
        self.mode = mode

        self.rows: list[PathDiagnostic] = []
        self.console_width = int(os.popen("stty size", "r").read().split()[1])

    def _clamp(self, txt: Text, max_width: int) -> tuple[Text, int]:
        if len(txt) > max_width:
            txt.align("left", max_width)
            txt.append("…")

            return txt, max_width + 1

        return txt, len(txt)

    def _cli_repr(self) -> RenderResult:
        diagnostic_repr = {
            Check.CHARACTERS: "BADCHAR ",
            Check.LENGTH: "LENGTH  ",
            Check.EMPTY: "EMPTY   ",
            Action.RENAME: "RENAME  ",
        }

        for row in self.rows:
            match row:
                case PathDiagnostic(Check.CHARACTERS, path, matches=list(matches), new_path=new_path):
                    repr_above, repr_under_list = _repr_matches(path.name, matches, new_path)

                case PathDiagnostic(Action.RENAME, path, patterns=list(patterns), new_path=Path() as new_path):
                    repr_above, repr_under_list = _repr_renames(path.name, patterns, new_path)

                case PathDiagnostic(Check.LENGTH, path):
                    max_path_len = self.ctx.config.get_max_path_length(self.ctx.fs)
                    repr_above, repr_under_list = _repr_too_long(path.name, len(str(path)), max_path_len)

                case PathDiagnostic(Check.EMPTY, path):
                    error_repr = f"{path.name} ~ directory contains no files"
                    repr_above = Text.assemble("/", (error_repr, ERROR_STYLE))
                    if self.mode == "rename":
                        repr_above.append((Text("\t==> DELETED", SUCCESS_STYLE)))

                    repr_under_list = []

                case _:
                    raise RuntimeError("Found invalid kind", row)

            right_offset = max(len(r) for r in chain([repr_above], repr_under_list))
            path_max_width = self.console_width - 9 - right_offset
            root, left_offset = self._clamp(Text(str(path.parent)), path_max_width)

            yield Text.assemble(diagnostic_repr[row.kind], root, repr_above)
            for repr_under in repr_under_list:
                yield Text.assemble("        ", " " * left_offset, repr_under)

    def _csv_repr(self) -> RenderResult:
        max_path_len = self.ctx.config.get_max_path_length(self.ctx.fs)
        header = "Error;Description;Reason;File_path;File_name"
        if self.mode == "rename":
            header += ";File_new_name"

        yield header

        for row in self.rows:
            match row:
                case PathDiagnostic(Check.CHARACTERS, path, matches=list(matches), new_path=new_path):
                    repr_matches = ",".join((f"{match.group()}@{match.start()}" for match in matches))
                    text = f"BADCHAR;Found invalid characters;{repr_matches};{str(path.parent)};{path.name}"

                    if new_path is not None:
                        text += f";{new_path.name}"

                case PathDiagnostic(Action.RENAME, path, patterns=list(patterns), new_path=Path() as new_name):
                    repr_matches = ",".join((_repr_regex_pattern(pattern) for (pattern, _) in patterns))
                    text = (
                        f"RENAME;Matched renaming pattern;{repr_matches};{str(path.parent)};{path.name};{new_name.name}"
                    )

                case PathDiagnostic(Check.LENGTH, path):
                    text = f"LENGTH;Path is too long;{len(str(path))} > {max_path_len};{str(path.parent)};{path.name}"

                    if self.mode == "rename":
                        text += ";"

                case PathDiagnostic(Check.EMPTY, path):
                    text = f"EMPTY;Directory contains no files;;{str(path.parent)};{path.name}"

                    if self.mode == "rename":
                        text += ";DELETED"

                case _:
                    raise RuntimeError("Found invalid kind", row)

            yield Text(text)

    def __rich_console__(self, _console: Console, _options: ConsoleOptions) -> RenderResult:
        if self.kind == OutputKind.cli:
            yield from self._cli_repr()

        elif self.kind == OutputKind.csv:
            yield from self._csv_repr()

    def add_row(self, row: PathDiagnostic) -> None:
        if self.kind != OutputKind.silent:
            self.rows.append(row)
