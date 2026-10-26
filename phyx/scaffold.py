"""``phyx new NAME`` — a shebang program and a sibling ``test_*.phyx``."""

from __future__ import annotations

import re
from pathlib import Path

from .conjugation import lemma_of
from .lexer import untransliterate
from .vocabulary import RESERVED

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_PROGRAM = """\
#! /usr/bin/env phyx
^rukx  {name} — a φyrx program.

^ťe-n-{name}:
    ^lo-n-'iţpənn.

!5-{name}.
"""

_TEST = """\
^rukx  Tests {name}.
^lo-"{filename}"-bukð.
^ǩaπa-5-{name}-5-ǆ'ynpp.
"""


def create(name: str, *, ascii_mode: bool = False, directory: Path | str | None = None) -> tuple[Path, Path]:
    """Write ``NAME.phyx`` and ``test_NAME.phyx``. Refuse to overwrite."""
    raw = name.strip()
    if raw.lower().endswith(".phyx") or raw.lower().endswith(".vphyx"):
        raw = Path(raw).stem
    if not _NAME.fullmatch(raw):
        raise ValueError("NAME must be letters, digits, and underscore (so it can be a ťe and a file on every OS)")
    if raw in RESERVED or lemma_of(raw) is not None:
        raise ValueError(f"'{raw}' is a word of the language and cannot name an ability")
    folder = Path(directory) if directory is not None else Path.cwd()
    program = folder / f"{raw}.phyx"
    test = folder / f"test_{raw}.phyx"
    if program.exists() or test.exists():
        existing = program if program.exists() else test
        err = FileExistsError(str(existing))
        err.filename = str(existing)
        raise err
    prog_text = _PROGRAM.format(name=raw)
    test_text = _TEST.format(name=raw, filename=program.name)
    if ascii_mode:
        prog_text = untransliterate(prog_text)
        test_text = untransliterate(test_text)
    program.write_text(prog_text, encoding="utf-8", newline="\n")
    test.write_text(test_text, encoding="utf-8", newline="\n")
    return program, test
