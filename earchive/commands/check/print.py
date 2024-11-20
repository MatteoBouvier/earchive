from __future__ import annotations

import itertools as it
import re
import shutil
from typing import Literal, NamedTuple, final

from rich.console import Console, RenderResult
from rich.text import Text

from earchive.commands.check.config import Config
from earchive.commands.check.config.substitution import RegexPattern
from earchive.commands.check.names import (
    Diagnostic,
    OutputKind,
    PathCharactersDiagnostic,
    PathCharactersReplaceDiagnostic,
    PathDiagnostic,
    PathEmptyDiagnostic,
    PathErrorDiagnostic,
    PathFilenameLengthDiagnostic,
    PathInvalidNameDiagnostic,
    PathLengthDiagnostic,
    PathRenameDiagnostic,
)
from earchive.utils.path import FastPath
from earchive.utils.progress import Bar

console = Console(force_terminal=True, legacy_windows=False)
console_err = Console(force_terminal=True, legacy_windows=False, stderr=True)

ERROR_STYLE = "bold red"
SUCCESS_STYLE = "bold green"
RENAME_STYLE = "bold magenta"


def _repr_regex_pattern(pattern: RegexPattern) -> str:
    flags = f"{'H\u02b0' if pattern.match.flags & re.IGNORECASE else ''}{'' if pattern.accent_sensitive else '^'}"
    if flags:
        flags = f"\u23a5{flags}"

    return f"{pattern.match.pattern}{flags}"


def _repr_matches(file_name: str, matches: list[re.Match[str]], new_path: FastPath | None) -> tuple[Text, list[Text]]:
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
    file_name: str, patterns: list[tuple[RegexPattern, str]], new_path: FastPath | None
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


def _repr_too_long(
    file_name: str, path_len: int, max_len: int, part: Literal["path", "filename"]
) -> tuple[Text, list[Text]]:
    no_color_len = max(0, len(file_name) - path_len + max_len)

    txt_path = ("/", file_name[:no_color_len], (file_name[no_color_len:], ERROR_STYLE))
    txt_under = (
        " ",
        " " * no_color_len,
        ("~" * min(len(file_name), path_len - max_len) + f" {part} is too long ({path_len} > {max_len})", ERROR_STYLE),
    )

    return Text.assemble(*txt_path), [Text.assemble(*txt_under)]


class CheckRepr(NamedTuple):
    string: str
    desc: str


@final
class Grid:
    def __init__(self, config: Config, kind: OutputKind, mode: Literal["check", "fix"]) -> None:
        self.config = config
        self.kind = kind
        self.mode = mode

        self.rows: list[PathDiagnostic] = []
        self.console_width = shutil.get_terminal_size().columns

        self.diagnostic_repr = {
            Diagnostic.CHARACTERS: CheckRepr("BADCHAR", "Found invalid characters"),
            Diagnostic.INVALID: CheckRepr("INVALID", "File name is invalid or reserved"),
            Diagnostic.RENAME_INVALID: CheckRepr("RENAME", "Matched invalid characters"),
            Diagnostic.RENAME_MATCH: CheckRepr("RENAME", "Matched renaming pattern"),
            Diagnostic.LENGTH_PATH: CheckRepr("LENGTH", "Path is too long"),
            Diagnostic.LENGTH_NAME: CheckRepr("LENGTH", "File name is too long"),
            Diagnostic.EMPTY: CheckRepr("EMPTY", "Directory contains no files"),
            Diagnostic.ERROR: CheckRepr("ERROR", "Encountered error while cheking"),
        }

    def _clamp(self, txt: Text, max_width: int) -> tuple[Text, int]:
        if len(txt) > max_width:
            txt.align("left", max_width)
            txt.append("…")

            return txt, max_width + 1

        return txt, len(txt)

    def _cli_repr(self) -> RenderResult:
        for row in self.rows:
            match row:
                case PathCharactersReplaceDiagnostic(FastPath() as path, FastPath() as new_path, matches=list(matches)):
                    repr_above, repr_under_list = _repr_matches(path.name, matches, new_path)

                case PathCharactersDiagnostic(FastPath() as path, matches=list(matches)):
                    repr_above, repr_under_list = _repr_matches(path.name, matches, None)

                case PathInvalidNameDiagnostic(FastPath() as path):
                    repr_above = Text.assemble("/", (f"{path.name} ~ name is invalid", ERROR_STYLE))
                    repr_under_list = []

                case PathRenameDiagnostic(FastPath() as path, FastPath() as new_path, patterns=list(patterns)):
                    repr_above, repr_under_list = _repr_renames(path.name, patterns, new_path)

                case PathLengthDiagnostic(FastPath() as path):
                    repr_above, repr_under_list = _repr_too_long(
                        path.name,
                        len(path),
                        self.config.check.max_path_length,
                        part="path",
                    )

                case PathFilenameLengthDiagnostic(FastPath() as path):
                    repr_above, repr_under_list = _repr_too_long(
                        path.name, len(path.name), self.config.check.max_name_length, part="filename"
                    )

                case PathEmptyDiagnostic(path):
                    error_repr = f"{path.name} ~ directory contains no files"
                    repr_above = Text.assemble("/", (error_repr, ERROR_STYLE))
                    if self.mode == "fix":
                        repr_above.append((Text("\t==> DELETED", SUCCESS_STYLE)))

                    repr_under_list = []

                case PathErrorDiagnostic(FastPath() as path, error=OSError() as err):
                    repr_above = f"{path.name} ~ {err.errno}, {err.strerror}"
                    repr_under_list = []

                case _:
                    raise RuntimeError("Found invalid kind", row)

            right_offset = max(len(r) for r in it.chain([repr_above], repr_under_list))
            path_max_width = self.console_width - 9 - right_offset
            root, left_offset = self._clamp(Text(str(path.parent)), path_max_width)

            yield Text.assemble("{:<8}".format(self.diagnostic_repr[row.kind].string), root, repr_above)
            for repr_under in repr_under_list:
                yield Text.assemble("        ", " " * left_offset, repr_under)

    def _csv_repr(self) -> RenderResult:
        header = "Kind;Description;Reason;File_path;File_name"
        if self.mode == "fix":
            header += ";File_new_name"

        yield header

        for row in self.rows:
            match row:
                case PathCharactersReplaceDiagnostic(FastPath() as path, FastPath() as new_path, matches=list(matches)):
                    reason = ",".join((f"{match.group()}@{match.start()}" for match in matches))
                    new_name = new_path.name

                case PathCharactersDiagnostic(FastPath() as path, matches=list(matches)):
                    reason = ",".join((f"{match.group()}@{match.start()}" for match in matches))
                    new_name = ""

                case PathInvalidNameDiagnostic(FastPath() as path):
                    reason = ""
                    new_name = ""

                case PathRenameDiagnostic(FastPath() as path, FastPath() as new_path, patterns=list(patterns)):
                    reason = ",".join((_repr_regex_pattern(pattern) for (pattern, _) in patterns))
                    new_name = new_path.name

                case PathLengthDiagnostic(FastPath() as path):
                    reason = f"{len(path)} > {self.config.check.max_path_length}"
                    new_name = ""

                case PathFilenameLengthDiagnostic(FastPath() as path):
                    reason = f"{len(path.name)} > {self.config.check.max_name_length}"
                    new_name = ""

                case PathEmptyDiagnostic(path):
                    reason = ""
                    new_name = "DELETED" if self.mode == "fix" else ""

                case PathErrorDiagnostic(FastPath() as path, error=OSError() as err):
                    reason = f"{err.errno}:{err.strerror}"
                    new_name = ""

                case _:
                    raise RuntimeError("Found invalid kind", row)

            dia_repr = self.diagnostic_repr[row.kind]
            row_text = f"{dia_repr.string};{dia_repr.desc};{reason};{str(row.path.parent)};{row.path.name}"

            if self.mode == "fix":
                row_text += f";{new_name}"

            yield row_text

    def print(self) -> None:
        if self.kind in (OutputKind.cli, OutputKind.unfixed):
            console.print(*it.islice(self._cli_repr(), 10_000), sep="\n")

            if len(self.rows) > 10_000:
                console.print(f"... and {len(self.rows) - 10_000} invalid paths not shown")

        elif self.kind == OutputKind.csv:
            if self.kind.path_ is None:
                console.no_color = True
                console.print(*self._csv_repr(), sep="\n")
                console.no_color = False

            else:
                progress: Bar = Bar(description="saving ...", multiplier=100, total=len(self.rows), percent=True)
                with open(self.kind.path_, mode="w") as file:
                    for lines in progress(it.batched(self._csv_repr(), n=100)):
                        file.writelines("%s\n" % line for line in lines)

        else:
            return

    def _skip_row(self, diagnostic: PathDiagnostic) -> bool:
        return self.kind == OutputKind.silent or (
            self.kind == OutputKind.unfixed
            and self.mode == "fix"
            and not isinstance(
                diagnostic,
                (
                    PathCharactersDiagnostic,
                    PathInvalidNameDiagnostic,
                    PathFilenameLengthDiagnostic,
                    PathLengthDiagnostic,
                    PathErrorDiagnostic,
                ),
            )
        )

    def add_row(self, row: PathDiagnostic) -> None:
        if not self._skip_row(row):
            self.rows.append(row)
