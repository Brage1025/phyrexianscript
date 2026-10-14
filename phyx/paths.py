"""Where ``bukð``, ``brøtjt`` and ``mɴyrx`` look on disk.

``bukð`` (cast) searches: the file that is casting, the working
directory, ``PHYX_PATH``, then the shipped standard library
(``phyx/lib``). A name without a suffix is tried as ``.phyx`` then
``.vphyx``.

``brøtjt`` (research) is a *read*. It searches the same places except
the standard library — herds are programs, not notes. The path is used
as written (no suffix guessing). Absolute paths are used as written.

``mɴyrx`` (spread) is a *write*. It never searches. A relative path is
resolved against the file that contains the sentence (the working
directory in the REPL). That keeps a short name from writing into
``phyx/lib`` or the first ``PHYX_PATH`` entry.
"""

from __future__ import annotations

import os
from pathlib import Path

SUFFIXES = (".phyx", ".vphyx")


def stdlib_dir() -> Path:
    return Path(__file__).resolve().parent / "lib"


def search_dirs(base_dir: Path | str | None, *, include_stdlib: bool = True) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []

    def add(p: Path) -> None:
        try:
            key = p.resolve()
        except OSError:
            key = p
        if key in seen:
            return
        seen.add(key)
        out.append(p)

    if base_dir is not None:
        add(Path(base_dir))
    add(Path.cwd())
    for part in os.environ.get("PHYX_PATH", "").split(os.pathsep):
        if part.strip():
            add(Path(part.strip()))
    if include_stdlib:
        add(stdlib_dir())
    return out


def note_search_dirs(base_dir: Path | str | None) -> list[Path]:
    """Directories ``brøtjt`` searches. No ``phyx/lib``."""
    return search_dirs(base_dir, include_stdlib=False)


def resolve_cast(path_str: str, base_dir: Path | str | None) -> Path | None:
    """Return the file ``bukð`` should run, or ``None`` if it is not found."""
    raw = Path(path_str)
    if raw.is_absolute():
        return raw if raw.is_file() else None
    names = [path_str]
    if raw.suffix.lower() not in SUFFIXES:
        names.extend(path_str + s for s in SUFFIXES)
    for folder in search_dirs(base_dir):
        for name in names:
            cand = folder / name
            try:
                if cand.is_file():
                    return cand.resolve()
            except OSError:
                continue
    return None


def resolve_note(path_str: str, base_dir: Path | str | None) -> Path | None:
    """Return the UTF-8 note ``brøtjt`` should read, or ``None``."""
    raw = Path(path_str)
    if raw.is_absolute():
        return raw if raw.is_file() else None
    for folder in note_search_dirs(base_dir):
        cand = folder / raw
        try:
            if cand.is_file():
                return cand.resolve()
        except OSError:
            continue
    return None


def resolve_spread(path_str: str, base_dir: Path | str | None) -> Path:
    """Path ``mɴyrx`` writes. Relative names stay next to the program."""
    raw = Path(path_str)
    if raw.is_absolute():
        return raw
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    return root / raw


def cast_hint(path_str: str, base_dir: Path | str | None) -> str:
    places = ", ".join(str(p) for p in search_dirs(base_dir))
    return (
        f"bukð looked for '{path_str}' in: {places}. "
        "python -m phyx lib    lists the standard herds."
    )


def note_hint(path_str: str, base_dir: Path | str | None) -> str:
    places = ", ".join(str(p) for p in note_search_dirs(base_dir))
    return (
        f"brøtjt looked for '{path_str}' in: {places}. "
        "mɴyrx writes next to the program, not along this search."
    )
