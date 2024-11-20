from enum import Enum
from typing import Literal, final

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.text import Text
from rich.theme import Theme

from earchive.commands.check.config.names import ASCII
from earchive.commands.check.names import Check, OutputKind
from earchive.names import COLLISION
from earchive.utils.fs import FS
from earchive.utils.os import OS


@final
class DocHighlighter(RegexHighlighter):
    base_style = "doc."
    highlights = [r"(?P<option>((?<!\w)[-\+]\w+)|(--[\w-]+))", r"(?P<code_block>`.*?`)", r"(?P<argument><[\w\s]+?>)"]


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


def _EnumList(enum: type[Enum]) -> str:
    return f"[{'|'.join(m for m in enum.__members__ if m != "AUTO")}]"


B, H, P = _SectionBody, _SectionHeader, _SectionParagraph


check_doc = Text.assemble(
    Text("EArchive check\n\n"),
    B(H("name"), P("check - check for invalid file paths on a target file system and fix them")),
    B(
        H("synopsis"),
        P("earchive check -h | --help"),
        P("earchive check --doc"),
        P(r"""earchive check [<filename>]
                           [--destination <dest_path>]
                           [--config <config_path>]
                           [--make-config]
                           [-o <option>=<value>]
                           [-O <behavior_option>=<value>]
                           [--output <format>]
                           [--exclude <excluded_path> [--exclude <excluded_path> ...]]
                           [--fix]
                           [--all]
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
        # P(
        #     "--fs <file_system>",
        #     "\n\t\tSelect the target file system for the checks. <file_system> can be [windows|auto].\n",
        #     "\t\tWhen using 'auto', the '--destination' option should provide a path on a target file system : its type will be infered for <file system>.\n",
        # ),
        P(
            "--destination <dest_path>",
            "\n\t\tProvide a destination path to which <filename> would be copied.\n",
            "\t\t- The maximum path length is shortened by the length of <dest_path>\n",
            "\t\t- The target file system and operating system can be automatically infered.\n",
        ),
        P("--config <config_path>", "\n\t\tProvide a", _Link("configuration"), "TOML file.\n"),
        P("--make-config", "\n\t\tPrint the current configuration as TOML format.\n"),
        P(
            "-o <option>=<value>",
            "\n\t\tSet",
            _Link("configuration"),
            "option values from the cli.\n",
            "\t\t<option>                            <value>                       description\n",
            "\t\tos                                 ",
            _EnumList(OS),
            "              target operating system\n",
            "\t\tfs                                 ",
            _EnumList(FS),
            " target file system\n",
            "\t\tbase_path_length                    positive integer              path length offset (usually computed when using --destination: length of the destination path)\n",
            "\t\tmax_path_length                     positive integer              maximum valid path length\n",
            "\t\tmax_name_length                     positive integer              maximum valid file name length\n",
            "\t\tcharacters:extra-invalid            characters                    characters that should be considered invalid, added to those defined by the target file system\n",
            "\t\tcharacters:replacement              character(s)                  replacement for invalid characters\n",
            "\t\tcharacters:ascii                   ",
            _EnumList(ASCII),
            "    restriction levels for characters to be considered as valid\n",
            "\t\trename[-noaccent][-nocase]:pattern  replacement                   renaming rule, can be repeated for defining multiple rules\n",
            "\n\t\tSee section",
            _Link("renaming rules"),
            "for details on using the `replace` option.\n",
            "\t\tFor option `characters:ascii`, the following restrictions apply:\n",
            "\t\t- STRICT   only letters, digits and underscores are valid\n",
            "\t\t- PRINT    same as STRICT, with additional punctuation characters ",
            r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""",
            "\n",
            "\t\t- ACCENTS  same as PRINT, with additional accented letters\n",
            "\t\t- NO       no restriction, all characters are allowed\n",
        ),
        P(
            "-O <behavior_option>=<value>",
            "\n\t\tSet behavior",
            _Link("configuration"),
            "option values from the cli. These options control the general behavior of the commad.\n",
            "\t\t<option>                            <value>                       description\n",
            "\t\tcollision                          ",
            _EnumList(COLLISION),
            "             how to treat file name collisions when renaming\n",
            "\t\tdry-run                             boolean|positive integer      perform dry-run, not actually modifying file names\n",
            "\n\t\tFor option `behavior:collision`, the following is done:\n",
            "\t\t- SKIP       do not rename file\n",
            "\t\t- INCREMENT  add `(<nb>)` to the end of the file name, where <nb> is the next smallest available number in the directory\n",
        ),
        P(
            "--output <format>",
            "\n\t\tSelect an output <format. <format> can be",
            _EnumList(OutputKind),
            ".\n",
            "\t\t- silent   only prints the number of invalid paths.\n",
            "\t\t- cli      is more user-friendly and uses colors to clearly point at invalid path portions.\n",
            "\t\t- unfixed  same as `cli`, but shows only paths that could not be fixed (only valid when using --fix).\n",
            "\t\t- csv      is easier to parse and to store.\n",
            "\t\tFor writing the csv output directly to a file, you can specify a path as 'csv=<path>'.\n",
        ),
        P(
            "--exclude <excluded_path>",
            "\n\t\tPath in <filename> to ignore during checks. Can be repeated to define multiple ignored paths.\n",
        ),
        P(
            "--fix\tFix invalid paths in <filename> to comply with rules on the target operating system and file system.",
            "\n\t\tFirst, invalid characters are replaced with a replacement character, _ (underscore) by default.",
            "\n\t\tThen, files and directories are renamed according to rules defined in the",
            _Link("configuration"),
            ". If all checks are disabled, this is the only operation performed.",
            "\n\t\tFinally, empty directories are removed and path lengths are checked.\n",
        ),
        P(
            "--all\tRun all available checks.\n",
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
            "Configuration options may be written to a TOML file and passed through the --config option. The default configuration is :",
        ),
        P(
            """
[behavior]
collision = "increment"
dry_run = false

[check]
run = ["CHARACTERS", "LENGTH"]
base_path_length = 0

[check.characters]
extra_invalid = ""
replacement = "_"
ascii = "no"

[rename]

[exclude]

""",
        ),
        P("Section [behavior] allows to define general behavior options. See -O for details.\n"),
        P(
            "Section [check] allows to define -o options\n",
            "\t- 'run' : list of checks to perform, can be one or more in ",
            _EnumList(Check),
            "\n",
            "\t- 'base_path_length' : in case <file name> needs to be copied to a directory, that directory's path length to subtract from the target file system's max path length\n",
            "\t- 'operating_system' : a target operating system\n",
            "\t- 'file_system' : a target file system\n",
            "\t- 'max_path_length' : maximum path length\n",
            "\t- 'max_name_length' : maximum file name length\n",
        ),
        P(
            "Section [check.characters] allows to define -o options relative to the CHARACTERS check\n",
            "\t- 'extra_invalid' : characters to consider invalid if found in file paths during -i checks\n",
            "\t- 'replacement' : replacement character(s) for invalid characters\n",
            "\t- 'ascii' : restriction levels for valid characters\n",
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
