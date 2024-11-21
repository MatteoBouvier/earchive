from collections.abc import Callable, Iterator
from contextlib import contextmanager
import re

from rich.text import Text

from earchive.doc.utils import Language
from earchive.doc.utils import SectionBody as B
from earchive.doc.utils import SectionHeader as H
from earchive.doc.utils import SectionParagraph as P
from earchive.doc.utils import IndentedLine as I
from earchive.doc.utils import NL

import importlib

OS = importlib.import_module("earchive.utils.os").OS
FS = importlib.import_module("earchive.utils.fs").FS
ASCII = importlib.import_module("earchive.commands.check.config.names").ASCII
COLLISION = importlib.import_module("earchive.names").COLLISION
OutputKind = importlib.import_module("earchive.commands.check.names").OutputKind
Check = importlib.import_module("earchive.commands.check.names").Check

_TRANSLATION: dict[str, dict[Language, str | Text]] = {
    "name": {Language.en: "name", Language.fr: "nom"},
    "description": {
        Language.en: "check for invalid file paths on a target file system and fix them",
        Language.fr: "Identifier les chemins de fichiers invalides sur un système de fichiers cible et les corriger",
    },
    "long description": {
        Language.en: "Check performs checks on a file or directory <filename> to find file path that would be invalid on a target file system. This is usefull to identify issues before copying files from one file system to another.",
        Language.fr: "Check analyse un fichier ou un dossier <filename> et identifie les chemins qui seraient invalides sur un système de fichiers cible. Ceci permet d'identifier des erreurs potentielles avant de copier une arborescence d'un système de fichiers à un autre.",
    },
    "help": {
        Language.en: I("Display a short description of this command with a summary of its options.", n_indent=2),
        Language.fr: I("Affiche une courte description de cette commande et un résumé des options.", n_indent=2),
    },
    "doc": {
        Language.en: Text.assemble(
            I("Display the full command documentation.", n_indent=2),
            I("Select the language in [enum]Language[/], default is EN.", n_indent=2),
        ),
        Language.fr: Text.assemble(
            I("Affiche la documentation complète.", n_indent=2),
            I("La langue peut être choisie parmi [enum]Language[/], EN par défaut.", n_indent=2),
        ),
    },
    "destination": {
        Language.en: Text.assemble(
            I("Provide a destination path to which <filename> would be copied.", n_indent=2),
            I("- The maximum path length is shortened by the length of <dest_path>", n_indent=2),
            I("- The target file system and operating system can be automatically infered.", n_indent=2),
        ),
        Language.fr: Text.assemble(
            I("Spécifie un chemin de destination dans lequel <filename> serait copié.", n_indent=2),
            I("- La longueur maximale des chemins est raccourcie de la longueur de <dest_path>", n_indent=2),
            I(
                "- Les système de fichiers et système d'exploitation cible peuvent être déduits automcatiquement",
                n_indent=2,
            ),
        ),
    },
    "config": {
        Language.en: I("Provide a [link]configuration[/] TOML file.", n_indent=2),
        Language.fr: I("Spécifie un fichier de [link]configuration[/] au format TOML.", n_indent=2),
    },
    "make config": {
        Language.en: I("Print the current configuration as TOML format.", n_indent=2),
        Language.fr: I("Affiche les options de configuration courantes au format TOML.", n_indent=2),
    },
    "options": {
        Language.en: Text.assemble(
            I("Set [link]configuration[/] option values from the cli.", n_indent=2),
            I("<option>                            <value>                       description", n_indent=2),
            I("os                                  [enum]OS[/]               target operating system", n_indent=2),
            I("fs                                  [enum]FS[/]  target file system", n_indent=2),
            I(
                "base_path_length                    positive integer              path length offset (usually computed when using --destination: length of the destination path)",
                n_indent=2,
            ),
            I(
                "max_path_length                     positive integer              maximum valid path length",
                n_indent=2,
            ),
            I(
                "max_name_length                     positive integer              maximum valid file name length",
                n_indent=2,
            ),
            I(
                "characters:extra-invalid            characters                    characters that should be considered invalid, added to those defined by the target file system",
                n_indent=2,
            ),
            I(
                "characters:replacement              character(s)                  replacement for invalid characters",
                n_indent=2,
            ),
            I(
                "characters:ascii                    [enum]ASCII[/]     restriction level for characters to be considered as valid",
                n_indent=2,
            ),
            I(
                "rename[-noaccent][-nocase]:pattern  replacement                   renaming rule, can be repeated for defining multiple rules",
                n_indent=2,
            ),
            NL,
            I("See section [link]renaming rules[/] for details on using the `replace` option.", n_indent=2),
            I("For option `characters:ascii`, the following restrictions apply:", n_indent=2),
            I("- STRICT   only letters, digits and underscores are valid", n_indent=2),
            I(
                r"""- PRINT    same as `STRICT`, with additional punctuation characters !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""",
                n_indent=2,
            ),
            I("- ACCENTS  same as `PRINT`, with additional accented letters", n_indent=2),
            I("- NO       no restriction, all characters are allowed", n_indent=2),
        ),
        Language.fr: Text.assemble(
            I("Définit la valeur des options de [link]configuration[/] depuis la CLI.", n_indent=2),
            I("<option>                            <value>                       description", n_indent=2),
            I("os                                  [enum]OS[/]               système d'exploitation cible", n_indent=2),
            I("fs                                  [enum]FS[/]  système de fichiers cible", n_indent=2),
            I(
                "base_path_length                    entier positif                décalage de la longueur des chemins de fichiers (généralement calculé par --destination comme la longueur du chemin de destination)",
                n_indent=2,
            ),
            I(
                "max_path_length                     entier positif                longueur maximale des chemins de fichiers",
                n_indent=2,
            ),
            I(
                "max_name_length                     entier positif                longueur maximale des noms de fichiers",
                n_indent=2,
            ),
            I(
                "characters:extra-invalid            caractères                    caractères considérés comme invalides, ajoutés à ceux définis par le système de fichiers cible",
                n_indent=2,
            ),
            I(
                "characters:replacement              caractère(s)                  remplacement pour les caractères invalides",
                n_indent=2,
            ),
            I(
                "characters:ascii                    [enum]ASCII[/]     niveau de réstriction pour la définition des caractères valides",
                n_indent=2,
            ),
            I(
                "rename[-noaccent][-nocase]:pattern  remplacement                  règle de renommage, peut être répété pour définir plusieures règles",
                n_indent=2,
            ),
            NL,
            I(
                "Voir section [link]règles de renommage[/] pour les détails sur l'utilisation de l'option `replace`.",
                n_indent=2,
            ),
            I("Pour l'option `characters:ascii`, les restrictions suivantes s'appliquent :", n_indent=2),
            I("- STRICT   uniquement les lettres, chiffres et tirets bas sont valides", n_indent=2),
            I(
                r"""- PRINT    comme `STRICT`, avec l'ajout des caractères de ponctuation !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""",
                n_indent=2,
            ),
            I("- ACCENTS  comme `PRINT`, avec l'ajout des lettres accentuées", n_indent=2),
            I("- NO       aucune restriction, tous les caractères sont valides", n_indent=2),
        ),
    },
    "Options": {
        Language.en: Text.assemble(
            I(
                "Set behavior [link]configuration[/] option values from the cli. These options control the general behavior of the commad.",
                n_indent=2,
            ),
            I("<option>                            <value>                       description", n_indent=2),
            I(
                "collision                           [enum]COLLISION[/]              how to treat file name collisions when renaming",
                n_indent=2,
            ),
            I(
                "dry-run                             boolean|positive integer      perform dry-run, not actually modifying file names",
                n_indent=2,
            ),
            NL,
            I("For option `behavior:collision`, the following is done:", n_indent=2),
            I("- SKIP       do not rename file", n_indent=2),
            I(
                "- INCREMENT  add `(<nb>)` to the end of the file name, where <nb> is the next smallest available number in the directory",
                n_indent=2,
            ),
        ),
        Language.fr: Text.assemble(
            I(
                "Définit la valeur des options de [link]configuration[/] du comportement général de la commande depuis la CLI.",
                n_indent=2,
            ),
            I("<option>                            <value>                       description", n_indent=2),
            I(
                "collision                           [enum]COLLISION[/]              comment gérer les collisions de noms de fichiers pendant le renommage",
                n_indent=2,
            ),
            I(
                "dry-run                             booléen|entier positif        réaliser une répétition, sans réellement modifier les noms de fichiers",
                n_indent=2,
            ),
            NL,
            I(
                "Pour l'option `behavior:collision`, les actions suivantes sont effectuées en cas de collision :",
                n_indent=2,
            ),
            I("- SKIP       ne pas renommer le fichier", n_indent=2),
            I(
                "- INCREMENT  ajouter `(<nb>)` à la fin du nom de fichier, où <nb> est le plus petit nombre disponible dans le dossier",
                n_indent=2,
            ),
        ),
    },
    "output format": {
        Language.en: Text.assemble(
            I("Select an output <format>, can be [enum]OutputKind[/].", n_indent=2),
            I("- silent   only prints the number of invalid paths", n_indent=2),
            I("- cli      is more user-friendly and uses colors to clearly point at invalid path portions", n_indent=2),
            I(
                "- unfixed  same as `cli`, but shows only paths that could not be fixed (only valid when using --fix)",
                n_indent=2,
            ),
            I("- csv      is easier to parse and to store", n_indent=2),
            NL,
            I(
                "For writing the csv output directly to a file, you can specify a path as '--output csv=<path>'.",
                n_indent=2,
            ),
        ),
        Language.fr: Text.assemble(
            I("Sélectionne un <format> de sortie, parmi [enum]OutputKind[/].", n_indent=2),
            I("- silent   affiche uniquement le nombre de chemins invalides", n_indent=2),
            I(
                "- cli      affiche des informations détaillées et en couleurs pour indiquer les portions invalides des chemins",
                n_indent=2,
            ),
            I(
                "- unfixed  comme `cli`, mais n'affiche que les chemins qui n'ont pas pu être corrigés (uniquement valide avec --fix)",
                n_indent=2,
            ),
            I("- csv      affichage pour le stockage ou l'analyse par des outils tiers", n_indent=2),
            NL,
            I(
                "Pour écrire au format csv directement dans un fichier de sortie, il est possible d'en spécifier le chemin avec '--output csv=<chemin>'.",
                n_indent=2,
            ),
        ),
    },
    "exclude": {
        Language.en: I(
            "A path in <filename> to ignore during checks. Can be repeated to define multiple ignored paths.",
            n_indent=2,
        ),
        Language.fr: I(
            "Un chemin dans <filename> à ignorer pendant l'analyse. Peut être répété pour définir plusieurs chemins à ignorer.",
            n_indent=2,
        ),
    },
    "fix": {
        Language.en: Text.assemble(
            "Fix invalid paths in <filename> to comply with rules on the target operating system and file system.\n",
            I(
                "First, invalid characters are replaced with a replacement character, _ (underscore) by default.",
                n_indent=2,
            ),
            I(
                "Then, files and directories are renamed according to rules defined in the [link]configuration[/]. If all checks are disabled, this is the only operation performed.",
                n_indent=2,
            ),
            I("Finally, empty directories are removed and path lengths are checked.", n_indent=2),
        ),
        Language.fr: Text.assemble(
            "Corrige les chemins invalides dans <filename> pour les conformer aux règles des système de fichiers et système d'exploitation cible.\n",
            I(
                "D'abord, les caractères invalides sont remplacés par le(s) caractère(s) de remplacement, _ (tiret bas) par défaut.",
                n_indent=2,
            ),
            I(
                "Ensuite, les fichiers et dossiers sont renommés selon les règles de renommage definies dans la [link]configuration[/]. Si toutes les vérifications sont désactivées, ceci est la seule opération effectuée.",
                n_indent=2,
            ),
            I(
                "Enfin, les dossiers vides sont supprimés et la longueur des chemins de fichiers est vérifiée.",
                n_indent=2,
            ),
        ),
    },
    "all": {Language.en: "Run all available checks.\n", Language.fr: "Effectue toutes les vérifications.\n"},
    "check empty": {
        Language.en: I("Check for (or remove) empty directories recursively.", n_indent=2),
        Language.fr: I("Vérifie l'absence (ou supprime) des dossiers vides de façon récursive.", n_indent=2),
    },
    "check invalid": {
        Language.en: I(
            "Check for invalid characters in file paths. Active by default. In --fix mode, invalid characters are replaced by a replacement string defined in the [link]configuration[/] or by an underscore by default.",
            n_indent=2,
        ),
        Language.fr: I(
            "Vérifie les caractères invalides dans les chemins de fichiers. Actif par défaut. Dans le mode --fix, les caractères invalides sont remplacés par le(s) charactère(s) de remplacement defini(s) dans la [link]configuration[/] ou par un tiret bas par défaut.",
            n_indent=2,
        ),
    },
    "check length": {
        Language.en: I("Check for path length exceeding the file system's limite. Active by default.", n_indent=2),
        Language.fr: I("Vérifie la longueur des chemins de fichiers. Actif par défaut.", n_indent=2),
    },
    "description conclusion": {
        Language.en: Text.assemble(
            "By default, checks for invalid characters and path lenghts are performed, as if using `earchive check -i -l` options.\n",
            I(
                "-e, -i and -l options individually select checks to be run, i.e. `earchive check -e` will ONLY run checks for empty directories.",
            ),
            I(
                "Individual checks may be disabled with the corresponding capital letter options -E (--no-check-empty-dirs), -I (--no-check-invalid-characters) and -L (--no-check-path-length).",
            ),
        ),
        Language.fr: Text.assemble(
            "Les vérifications des caractères invalides et de la longueur des chemins de fichiers sont effectuées par défaut. Ceci équivaut à utiliser les options `earchive check -i -l`.\n",
            I(
                "Les options -e, -i et -l sélectionnent individuellement les vérifications à effectuer : `earchive check -e` vérifiera uniquement l'absence des dossiers vides."
            ),
            I(
                "Les vérifications peuvent être désactivées individuellement en utilisant les options avec lettres majuscules -E (--no-check-empty-dirs), -I (--no-check-invalid-characters) et -L (--no-check-path-length)."
            ),
        ),
    },
    "configuration": {
        Language.en: "Configuration options may be written to a TOML file and passed through the --config option. The default configuration is:",
        Language.fr: "Les options de configuration peuvent être écrites dans un fichier au format TOML et passées avec l'option --config. La configuration par défaut est :",
    },
    "configuration behavior": {
        Language.en: "Section [behavior] allows to define general behavior options. See -O for details.\n",
        Language.fr: "La section [behavior] permet de configurer le comportement général de la commande. Voir -O pour les détails des options.\n",
    },
    "configuration check": {
        Language.en: Text.assemble(
            "Section [check] allows to define -o options :\n",
            I("- run               list of checks to perform, can be one or more in [enum]Check[/]"),
            I(
                "- base_path_length  in case <file name> needs to be copied to a directory, that directory's path length to subtract from the target file system's max path length"
            ),
            I("- operating_system  a target operating system in [enum]OS[/]"),
            I("- file_system       a target file system in [enum]FS[/]"),
            I("- max_path_length   maximum path length"),
            I("- max_name_length   maximum file name length"),
        ),
        Language.fr: Text.assemble(
            "La section [check] permet de définir les options -o :\n",
            I("- run               liste de vérifications à effectuer, une ou plusieurs parmi [enum]Check[/]"),
            I(
                "- base_path_length  dans le cas où <filename> devrait être copié dans un dossier de destination, la longueur du chemin de ce dossier, à soustraire de la longueur maximale de chemin autorisée par le système de fichiers cible."
            ),
            I("- operating_system  le système d'exploitation cible parmi [enum]OS[/]"),
            I("- file_system       le système de fichiers cible parmi [enum]FS[/]"),
            I("- max_path_length   longueur maximale des chemins de fichiers"),
            I("- max_name_length   longueur maximale des noms de fichiers"),
        ),
    },
    "configuration check characters": {
        Language.en: Text.assemble(
            "Section [check.characters] allows to define -o options relative to the CHARACTERS check:\n",
            I("- extra_invalid  characters to consider invalid if found in file paths"),
            I("- replacement    replacement character(s) for invalid characters"),
            I("- ascii          restriction levels for valid characters"),
        ),
        Language.fr: Text.assemble(
            "La section [check.characters] permet de définir les options -o relatives à la vérification des caractères invalides :\n",
            I("- extra_invalid  caractères à considérer comme invalides dans un chemin de fichier"),
            I("- replacement    caractère(s) de replacement pour les caractères invalides"),
            I("- ascii          niveau de restriction pour les caractères valides"),
        ),
    },
    "configuration replace": {
        Language.en: "Section [replace] allows to define renaming rules to apply to file paths (one rule per line).\n",
        Language.fr: "La section [replace] permet de définir les règles de renommage à appliquer aux chemins de fichiers (une règle par ligne).\n",
    },
    "configuration exclude": {
        Language.en: "Section [exclude] allows to define a list of paths to exclude from the analysis (one path per line). Paths can be absolute or relative to the command's execution directory.\n",
        Language.fr: "La section [exclude] permet de définir une liste de chemins à exclude de l'analyse (un chemin par ligne). Les chemin peuvent être absolus ou relatifs au dossier d'execution.\n",
    },
    "renaming rules": {Language.en: "renaming rules", Language.fr: "règles de renommage"},
    "renaming format": {
        Language.en: Text.assemble(
            "A renaming rule follows the format: `<pattern> = <replacement> [NO_CASE] [NO_ACCENT]`, where <pattern> is a regex string to match in paths and <replacement> is a regular string to use as replacement for the matched pattern.\n",
            I(
                "Otional flags NO_CASE and NO_ACCENT indicate that pattern matching should be insensitive to case and accents respectively."
            ),
        ),
        Language.fr: Text.assemble(
            "Une règle de renommage est définie à l'aide du format suivant : `<pattern> = <remplacement> [NO_CASE] [NO_ACCENT]`, où <pattern> est une expression régulière à identifier dans un chemin de fichier et <remplacement> est une chaine de caractères à insérer à la place du texte identifié par <pattern>.\n",
            I(
                "Les marqueurs optionels NO_CASE et NO_ACCENT indiquent respectivement que le <pattern> à identifier est insensible à la casse et aux accents."
            ),
        ),
    },
    "renaming example": {
        Language.en: "Example: `(_){2,} = _` matches multiple consecutive underscores and replaces them by a single underscore.\n",
        Language.fr: "Exemple : `(_){2,} = _` identifie de multiples tirets bas consécutifs et les remplace par un unique tiret bas.\n",
    },
    "renaming output": {
        Language.en: Text.assemble(
            "In --output formats, pattern flags (if any) are represented after a '⎥' character, as:\n",
            I("Hʰ for case insensitive"),
            I("^  for accent insensitive"),
        ),
        Language.fr: Text.assemble(
            "Dans les formats de sortie (--output), les marqueurs optionels utilisés sont représentés après un caractère '⎥' par :\n",
            I("Hʰ pour l'insensibilité à la casse"),
            I("^  pour l'insensibilité aux accents"),
        ),
    },
}


@contextmanager
def locale(lang: Language) -> Iterator[Callable[[str], str | Text]]:
    def get_translation(string: str) -> str | Text:
        return _TRANSLATION[string][lang]

    yield get_translation


def check_doc(lang: Language) -> Text:
    with locale(lang) as _:
        doc = Text.assemble(
            Text("EArchive check\n\n"),
            B(H(_("name")), P("check -", _("description"))),
            B(
                H("synopsis"),
                P("earchive check -h | --help"),
                P("earchive check --doc [[enum]Language[/]]"),
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
                       [-eEiIlL]"""),
            ),
            B(H("description"), P(_("long description"))),
            B(
                H("options"),
                P("-h | --help\n", _("help")),
                P("--doc [[enum]Language[/]]\n", _("doc")),
                P("--destination <dest_path>\n", _("destination")),
                P("--config <config_path>\n", _("config")),
                P("--make-config\n", _("make config")),
                P("-o <option>=<value>\n", _("options")),
                P("-O <behavior_option>=<value>\n", _("Options")),
                P("--output <format>\n", _("output format")),
                P("--exclude <excluded_path>\n", _("exclude")),
                P("--fix  ", _("fix")),
                P("--all  ", _("all")),
                P("-e | --check-empty-dirs\n", _("check empty")),
                P("-i | --check-invalid-characters\n", _("check invalid")),
                P("-l | --check-path-length\n", _("check length")),
                P(_("description conclusion")),
            ),
            B(
                H("configuration"),
                P(_("configuration")),
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
                P(_("configuration behavior")),
                P(_("configuration check")),
                P(_("configuration check characters")),
                P(_("configuration replace")),
                P(_("configuration exclude")),
            ),
            B(
                H(_("renaming rules")),
                P(_("renaming format")),
                P(_("renaming example")),
                P(_("renaming output")),
            ),
        )

        with_links = re.sub(r"\\\[link\](.*)\\\[/\]", r"[bold blue]\1[/bold blue]", doc.markup)
        with_enums = re.sub(
            r"\\\[enum\](.*)\\\[/\]",
            lambda m: f"[{'|'.join(str(member).upper() for member in eval(m.group(1)).__members__ if member != "AUTO")}]",
            with_links,
        )
        return Text.from_markup(with_enums)
