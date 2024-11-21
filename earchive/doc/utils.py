from enum import StrEnum, auto
from typing import final

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.text import Text
from rich.theme import Theme


class Language(StrEnum):
    en = auto()
    fr = auto()


@final
class DocHighlighter(RegexHighlighter):
    base_style = "doc."
    highlights = [r"(?P<option>((?<!\w)[-\+]\w+)|(--[\w-]+))", r"(?P<code_block>`.*?`)", r"(?P<argument><[\w\s]+?>)"]


doc_theme = Theme({"doc.option": "bold green1", "doc.code_block": "italic cyan", "doc.argument": "underline"})
doc_highlighter = DocHighlighter()

_console = Console(theme=doc_theme)


def SectionBody(header: Text, *body: Text) -> Text:
    return Text.assemble(header, *body, "\n")


def SectionHeader(text: str | Text) -> Text:
    if isinstance(text, Text):
        return Text(text.plain.upper() + "\n", style="bold blue")
    return Text(text.upper() + "\n", style="bold blue")


def SectionParagraph(*text: str | Text) -> Text:
    return Text.assemble("\t", *(doc_highlighter(t + " ") for t in text), "\n")


def IndentedLine(*text: str | Text, n_indent: int = 1) -> Text:
    return Text.assemble("\t" * n_indent, *text, "\n")


NL = "\n"
