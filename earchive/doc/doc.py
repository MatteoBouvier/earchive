from typing import Literal

from rich.console import Console

from earchive.doc.check import check_doc
from earchive.doc.utils import Language, doc_theme


_console = Console(theme=doc_theme)


def print_doc(which: Literal["check"], lang: Language = Language.en) -> None:
    with _console.pager(styles=True):
        if which == "check":
            _console.print(check_doc(lang))

        else:
            raise RuntimeError("Could not find documentation")  # pyright: ignore[reportUnreachable]
