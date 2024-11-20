from collections.abc import Generator
from dataclasses import dataclass
from itertools import chain

import earchive.errors as err
from earchive.commands.check.config import Config
from earchive.commands.check.config.substitution import RegexPattern
from earchive.commands.check.names import (
    Check,
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
from earchive.utils.progress import Bar, NoBar


@dataclass
class Counter:
    value: int = 0


def plural(value: int) -> str:
    return "" if value == 1 else "s"


def _is_excluded(path: FastPath, config: Config) -> bool:
    if not len(config.exclude):
        return False

    return any(parent in config.exclude for parent in chain([path], path.parents))


def _check_valid_file(path: FastPath, config: Config, checks: Check) -> Generator[PathDiagnostic, None, None]:
    if Check.CHARACTERS in checks:
        if len(match := config.invalid_characters.finditer(path.stem)):
            yield PathCharactersDiagnostic(path, matches=match)

        if config.invalid_names.match(path.stem):
            yield PathInvalidNameDiagnostic(path)

    if Check.LENGTH in checks:
        if len(path.name) > config.check.max_name_length:
            yield PathFilenameLengthDiagnostic(path)

        if len(path) > config.check.max_path_length:
            yield PathLengthDiagnostic(path)


def _check_valid_dir(
    path: FastPath, is_empty: bool, config: Config, checks: Check
) -> Generator[PathDiagnostic, None, None]:
    if Check.EMPTY in checks and is_empty:
        yield PathEmptyDiagnostic(path)

    yield from _check_valid_file(path, config, checks)


def invalid_paths(
    config: Config, checks: Check | None = None, progress: Bar = NoBar
) -> Generator[PathDiagnostic, None, None]:
    _empty_dirs: set[FastPath] = set()
    errors: list[PathDiagnostic] = []

    def on_error(err: OSError) -> None:
        errors.append(PathErrorDiagnostic(FastPath.from_str(err.filename, config.check.operating_system), error=err))

    if checks is None:
        checks = config.check.run

    paths = config.check.path.walk(top_down=False, on_error=on_error)
    progress.maxiters = config.behavior.dry_run

    with progress:
        for root, dirs, files in paths:
            for file in progress.iter(filter(lambda f: not _is_excluded(f, config), map(lambda f: root / f, files))):
                yield from _check_valid_file(file, config, checks)

            for dir in progress.iter(filter(lambda d: not _is_excluded(d, config), map(lambda d: root / d, dirs))):
                yield from _check_valid_dir(dir, dir in _empty_dirs, config, checks)

            if not len(files) and all(root / dir in _empty_dirs for dir in dirs):
                _empty_dirs.add(root)

            if progress.has_reached_maxiters:
                break

        yield from errors


def _rename_if_match(file_path: FastPath, config: Config) -> PathDiagnostic | None:
    new_name = file_path.name
    matched_patterns: list[tuple[RegexPattern, str]] = []

    for pattern in config.rename:
        new_name, nsubs = pattern.match.subn(pattern.replacement, pattern.normalize(new_name))

        if nsubs:
            matched_patterns.append((pattern, new_name))

    if len(matched_patterns):
        success, new_path = file_path.rename(
            file_path.parent / new_name, config.behavior.collision, not config.behavior.dry_run
        )

        if success:
            return PathRenameDiagnostic(file_path, new_path, patterns=matched_patterns)

        else:
            return PathErrorDiagnostic(file_path, error=err.cannot_overwrite(file_path.str()))


def _fix_invalid_file(
    file_path: FastPath, config: Config, repl: bytearray, counter: Counter
) -> Generator[PathDiagnostic, None, None]:
    if Check.CHARACTERS in config.check.run:
        if len(matches := config.invalid_characters.finditer(file_path.stem)):
            new_stem = bytearray(file_path.stem, encoding="utf-8")

            for match in matches:
                new_stem[match.start() : match.start() + len(bytearray(match.group(0), "utf-8"))] = repl

            success, new_file_path = file_path.rename(
                file_path.with_stem(new_stem.decode()), config.behavior.collision, not config.behavior.dry_run
            )

            if success:
                old_file_path, file_path = file_path, new_file_path
                yield PathCharactersReplaceDiagnostic(old_file_path, file_path, matches=matches)

            else:
                counter.value += 1
                yield PathCharactersDiagnostic(file_path, matches=matches)

        if config.invalid_names.match(file_path.stem):
            counter.value += 1
            yield PathInvalidNameDiagnostic(file_path)

    rename_data = _rename_if_match(file_path, config)
    if rename_data is not None:
        yield rename_data

    if Check.LENGTH in config.check.run:
        if len(file_path.name) > config.check.max_name_length:
            counter.value += 1
            yield PathFilenameLengthDiagnostic(file_path)

        if len(file_path) > config.check.max_path_length:
            counter.value += 1
            yield PathLengthDiagnostic(file_path)


def _fix_invalid_dir(
    dir_path: FastPath, is_empty: bool, config: Config, repl: bytearray, counter: Counter
) -> Generator[PathDiagnostic, None, None]:
    if Check.EMPTY in config.check.run and is_empty:
        if not config.behavior.dry_run:
            dir_path.rmdir()

        yield PathEmptyDiagnostic(dir_path)
        return

    yield from _fix_invalid_file(dir_path, config, repl, counter)


def fix_invalid_paths(config: Config, progress: Bar, counter: Counter) -> Generator[PathDiagnostic, None, None]:
    _empty_dirs: set[FastPath] = set()
    errors: list[PathDiagnostic] = []

    def on_error(err: OSError) -> None:
        errors.append(PathErrorDiagnostic(FastPath.from_str(err.filename, config.check.operating_system), error=err))

    repl = bytearray(config.check.characters.replacement, encoding="utf-8")

    paths = config.check.path.walk(top_down=False, on_error=on_error)
    progress.maxiters = config.behavior.dry_run

    with progress:
        for root, dirs, files in paths:
            for file_path in progress.iter(
                filter(lambda f: not _is_excluded(f, config), map(lambda f: root / f, files))
            ):
                yield from _fix_invalid_file(file_path, config, repl, counter)

            for dir in progress.iter(filter(lambda d: not _is_excluded(d, config), map(lambda d: root / d, dirs))):
                yield from _fix_invalid_dir(dir, dir in _empty_dirs, config, repl, counter)

            if not len(files) and all(root / dir in _empty_dirs for dir in dirs):
                _empty_dirs.add(root)

            if progress.has_reached_maxiters:
                break

        yield from errors
