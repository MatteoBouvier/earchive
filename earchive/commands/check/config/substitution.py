import re
import unicodedata
from dataclasses import dataclass
from typing import override

_ACCENTS = re.compile(r"[\u0300-\u036f]")  # all accents (unicode combining diacritical marks)


@dataclass(frozen=True, repr=False)
class RegexPattern:
    match: re.Pattern[str]
    replacement: str
    accent_sensitive: bool

    @override
    def __repr__(self) -> str:
        return f"RegexPattern<{self.match.pattern} -> {self.replacement}, ignore-case: {bool(self.match.flags & re.IGNORECASE)}, ignore-accents: {not self.accent_sensitive}>"

    def normalize(self, string: str) -> str:
        if self.accent_sensitive:
            return string

        # remove all accents from string
        return _ACCENTS.sub("", unicodedata.normalize("NFD", string))
