"""φyrx (PhyrxScript / PhyrexianScript) — a programming language written in Phyrexian.

Vocabulary, orthography and grammar follow the community Phyrexian
Dictionary (https://fxbuson.github.io/PhyrexianDictionary/):

* sentences start with ``^`` / ``!`` / ``?`` and end with ``.`` or ``:``
* words are separated by ``-`` (or a line break), phrases by ``,``
* the verb always comes last (SOV), so expressions are postfix
* every phrase opens with a mood/tense marker which selects the statement
* numbers are hexadecimal (Arabic or Basilica Mathematical Monospace)
* verbs may take chapter-3 person inflection; tense stays on the mood marker
* text is read vertically: symbols top-to-bottom, lines left-to-right
"""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .errors import PhyrexianError, format_error
from .interpreter import Interpreter, run_source
from .lexer import tokenize, transliterate
from .parser import parse
from .repl import Repl, is_complete

__all__ = [
    "PhyrexianError",
    "format_error",
    "tokenize",
    "transliterate",
    "parse",
    "Interpreter",
    "run_source",
    "Repl",
    "is_complete",
    "LANGUAGE",
    "LANGUAGE_ALIASES",
]

def _distribution_version() -> str:
    """Installed metadata, else ``pyproject.toml``, else a marked placeholder."""
    try:
        return version("phyx")
    except PackageNotFoundError:
        pass
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with pyproject.open("rb") as handle:
            found = tomllib.load(handle)["project"]["version"]
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return "0+unknown"
    if not isinstance(found, str):
        return "0+unknown"
    return found


__version__ = _distribution_version()
LANGUAGE = "φyrx"
LANGUAGE_ALIASES = ("PhyrxScript", "PhyrexianScript")
