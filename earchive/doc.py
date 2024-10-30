from typing import Literal

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.text import Text
from rich.theme import Theme


class DocHighlighter(RegexHighlighter):
    base_style = "doc."
    highlights = [r"(?P<option>((?<!\w)[-\+]\w)|(--[\w-]+))", r"(?P<code_block>`.*?`)", r"(?P<argument><.+?>)"]


doc_theme = Theme({"doc.option": "bold green1", "doc.code_block": "italic cyan", "doc.argument": "underline"})
doc_highlighter = DocHighlighter()

_console = Console(theme=doc_theme)


def print_doc(which: Literal["check"]):
    with _console.pager(styles=True):
        if which == "check":
            _console.print(check_doc)

        else:
            raise RuntimeError("Could not find documentation")


def _SectionBody(header: Text, *body: Text) -> Text:
    return Text.assemble(header, *body, "\n")


def _SectionHeader(text: str) -> Text:
    return Text(text.upper() + "\n", "bold blue")


def _SectionParagraph(*text: str | Text) -> Text:
    return Text.assemble("\t", *(doc_highlighter(t + " ") for t in text), "\n")


def _Link(text: str) -> Text:
    return Text(text, "bold blue")


B, H, P = _SectionBody, _SectionHeader, _SectionParagraph


check_doc = Text.assemble(
    Text("EArchive check\n\n"),
    B(H("name"), P("check - check for invalid file paths on a target file system and fix them")),
    B(
        H("synopsis"),
        P("earchive check -h | --help"),
        P("earchive check --doc"),
        P(r"""earchive check [<filename>]
                           [--fs <file system>]
                           [--destination <dest_path>]
                           [--config <config_path>]
                           [--output <format>]
                           [--fix]
                           [--check-all | -A]
                           [-eEiIlL]
"""),
    ),
    B(
        H("description"),
        P(
            "Check performs checks on a file or directory <filename> to find file names that would be invalid on a target <file_system>.",
            "This is usefull to identify issues before copying files from one file system to another.",
        ),
    ),
    B(
        H("options"),
        P("-h or --help", "\n\t\tDisplay a short description of this command with a summary of its options.\n"),
        P("--doc\tDisplay the full command documentation.\n"),
        P(
            "--fs <file_system>",
            "\n\t\tSelect the target file system for the checks. <file_system> can be [windows|auto].\n",
            "\t\tWhen using 'auto', the '--destination' option should provide a path on a target file system : its type will be infered for <file system>.\n",
        ),
        P(
            "--destination <dest_path>",
            "\n\t\tProvide a destination path to which <filename> would be copied.\n",
            "\t\t- The maximum path length is shortened by the length of <dest_path>\n",
            "\t\t- The target <file_system> can be automatically infered.\n",
        ),
        P("--config <config_path>", "\n\t\tProvide a", _Link("configuration"), "file.\n"),
        P(
            "--output <format>",
            "\n\t\tSelect an output <format. <format> can be [silent|cli|csv].\n",
            "\t\t- silent only prints the number of invalid paths.\n",
            "\t\t- cli is more user-friendly and uses colors to clearly point at invalid path portions.\n",
            "\t\t- csv is easier to parse and to store.\n",
            "\t\tFor writing the csv output directly to a file, you can specify a path as 'csv=<path>'.\n",
        ),
        P(
            "--fix\tFix invalid paths in <filename> to comply with rules on the target <file_system>.",
            "\n\t\tFirst, invalid characters are replaced with a replacement character, _ (underscore) by default."
            "\n\t\tThen, files and directories are renamed according to rules defined in the",
            _Link("configuration"),
            "file. If all checks are disabled, this is the only operation performed.",
            "\n\t\tFinally, empty directories are removed and path lengths are checked.\n",
        ),
        P(
            "-A or --check-all",
            "\n\t\tRun all available checks.\n",
        ),
        P("-e or --check-empty-dirs", "\n\t\tCheck for (or remove) empty directories recursively.\n"),
        P(
            "-i or --check-invalid-characters",
            "\n\t\tCheck for invalid characters in file paths. Active by default.",
            "In",
            _Link("fix"),
            "mode, invalid characters are replaced by a replacement string defined in the",
            _Link("configuration"),
            "file or by an underscore by default.\n",
        ),
        P(
            "-l or --check-path-length",
            "\n\t\tCheck for path length exceeding the file system's limite. Active by default.\n",
        ),
        P(
            "By default, checks for invalid characters and path lenghts are performed, as if using `earchive check -i -l` options.",
            "-e, -i and -l options individually select checks to be run, i.e. `earchive check -e` will ONLY run checks for empty directories.",
            "Individual checks may be disabled with the corresponding capital letter options -E (--no-check-empty-dirs), -I (--no-check-invalid-characters) and -L (--no-check-path-length).",
        ),
    ),
    B(
        H("configuration"),
        P(
            "Configuration options must be written to a file and passed through the -c option. The default configuration is :",
        ),
        P(
            """
[check]
run = CHARACTERS LENGTH
file_system = windows
base_path_length = 0

[check.characters]
extra = ""
replacement = _

[file_systems.windows]
special_characters = <>:/\\|?*
max_path_length = 255

[rename]

[exclude]
""",
        ),
        P(
            "Section [check] allows to define:\n"
            "\t- 'run' : checks to perform, can one or more in [CHARACTERS|LENGTH|EMPTY].\n",
            "\t- 'file_system' : a target file system.\n",
            "\t- 'base_path_length' : in case <filename> needs to be copied to a directory, that directory's path length to subtract from the target file system's max path length.\n\n",
            "\tThese values may be overridden by cli options '--fs', '--destination' and '-eEiIlLA' if specified.\n\n",
        ),
        P(
            "Section [check.characters] allows to define:"
            "\n\t- 'extra' : characters to consider invalid if found in file paths during -i checks.",
            "\n\t- 'replacement' : a replacement string for invalid characters.\n\n",
        ),
        P(
            "Sections [file_system.<FS>] allows to define, for an individual file system <FS>:"
            "\n\t- 'special_characters' : characters to consider invalid if found in file paths during -i checks.",
            "\n\t- 'max_path_leng' : the file system's max path length.\n\n",
        ),
        P(
            "Section [replace] allows to define renaming rules to apply to file paths (one rule per line).\n",
        ),
        P(
            "Section [exclude] allows to define a list of paths to exclude from the analysis (one path per line). Paths can be absolute or relative to the command's execution directory.\n"
        ),
    ),
    B(
        H("renaming rules"),
        P(
            "A renaming rule follows the format : `<pattern> = <replacement> [NO_CASE] [NO_ACCENT]` where <pattern> is a regex string to match in paths and <replacement> is a regular string to use as replacement for the matched pattern.\n",
            "\tOptional flags NO_CASE and NO_ACCENT indicate that pattern matching should be insensitive to case and accents respectively.\n",
        ),
        P(
            "Example: `(_){2,} = _` matches multiple consecutive underscores and replaces them by a single underscore.\n",
        ),
        P(
            "In csv and cli",
            _Link("output"),
            "formats, pattern flags (if any) are reprsented after a '⎥' character, as:\n",
            "\t- Hʰ for case insensitive\n",
            "\t- ^  for accent insensitive\n",
        ),
    ),
)
