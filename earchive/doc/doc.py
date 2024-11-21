from typing import Literal, final

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.theme import Theme

from earchive.doc.check import check_doc
from earchive.doc.utils import Language


@final
class DocHighlighter(RegexHighlighter):
    base_style = "doc."
    highlights = [r"(?P<option>((?<!\w)[-\+]\w+)|(--[\w-]+))", r"(?P<code_block>`.*?`)", r"(?P<argument><[\w\s]+?>)"]


doc_theme = Theme({"doc.option": "bold green1", "doc.code_block": "italic cyan", "doc.argument": "underline"})
doc_highlighter = DocHighlighter()

_console = Console(theme=doc_theme)


def print_doc(which: Literal["check"], lang: Language = Language.en):
    with _console.pager(styles=True):
        if which == "check":
            _console.print(check_doc(lang))

        else:
            raise RuntimeError("Could not find documentation")  # pyright: ignore[reportUnreachable]
