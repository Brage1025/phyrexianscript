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

from .errors import PhyrexianError, format_error
from .lexer import tokenize, transliterate
from .parser import parse
from .interpreter import Interpreter, run_source
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

__version__ = "1.6.3"
LANGUAGE = "φyrx"
LANGUAGE_ALIASES = ("PhyrxScript", "PhyrexianScript")
