"""Tokenizer for φyrx source.

The written symbols of Phyrexian fall into three groups (tutorial, chapter 1):

* **punctuation** — ``^`` ``?`` ``!`` ``"`` start a sentence, ``.`` and ``:``
  end one, ``-`` separates words and ``,`` separates words/phrases.  A word
  separator is dropped at a line break, so a newline is a separator too.
* **vowels** — ``i y e a ɒ o ø u ə``
* **consonants** — ``m n ŋ ɴ s š z ž ɬ ɮ l r č ǆ w j ẅ ' h p f π φ b v t θ ť ţ
  d ð k x ǩ ķ g ɣ q χ ǧ ǥ ɢ ʁ``

Numbers are **hexadecimal**. Phyrexian Regular draws Arabic digits on the
connecting line; Basilica draws the same sixteen values as Mathematical
Monospace glyphs. Both tokenise as one numeral syntax: ``10`` is sixteen,
``0ff`` is 255.  A literal must start with a digit (Arabic ``0–9`` or a
Basilica glyph, including ``𝙰–𝙵``); ``əx`` glued onto a numeral makes it
negative: ``əx1a``.  A ``#!`` line at the very start of the file is a
shebang and is ignored.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .errors import LexError, nesting_fault
from .numerals import hex_digit, is_numeral_start, normalize_hex

VOWELS = "iyeaɒoøuə"
CONSONANTS = "mnŋɴsšzžɬɮlrčǆwjẅ'hpfπφbvtθťţdðkxǩķgɣqχǧǥɢʁ"
ALPHABET = VOWELS + CONSONANTS

PUNCTUATION = {
    "^": "START",
    "?": "START",
    "!": "START",
    ".": "END",
    ":": "COLON",
    "-": "SEP",
    ",": "COMMA",
}

COMMENT_WORD = "rukx"  # "note": ``^rukx ...`` is a comment up to end of line
NEGATIVE_PREFIX = "əx"


@dataclass(frozen=True)
class Token:
    kind: str  # START | WORD | NUMBER | STRING | SEP | COMMA | END | COLON | EOF
    value: object
    line: int
    col: int
    indent: int  # indentation (in spaces) of the line this token sits on

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.kind}({self.value!r}@{self.line}:{self.col})"


def is_letter(ch: str) -> bool:
    """Any Phyrexian letter.  We are lenient and also accept other Unicode
    letters (and combining marks) so transliterated or borrowed names work."""
    if ch in ALPHABET:
        return True
    if ch.isalpha():
        return True
    return unicodedata.category(ch).startswith("M")


# --------------------------------------------------------------------------
# ASCII transliteration
# --------------------------------------------------------------------------
# Typing ``θ`` or ``ɢ`` on a regular keyboard is painful.  In ASCII mode an
# upper-case letter (or upper-case digraph) stands for the "special" letter it
# most resembles.  Lower-case text is left untouched, so plain letters such as
# ``t`` + ``h`` never get merged by accident.
TRANSLIT: dict[str, str] = {
    # vowels
    "A": "ɒ", "O": "ø", "E": "ə",
    # sibilants / affricates / glides
    "S": "š", "Z": "ž", "C": "č", "J": "ǆ", "W": "ẅ",
    # laterals and nasals
    "LH": "ɬ", "LZ": "ɮ", "NG": "ŋ", "NN": "ɴ",
    # dental fricatives
    "TH": "θ", "DH": "ð",
    # metallic consonants: single capital = clanked (plosive),
    # capital + H = sliced (aspirated)
    "P": "π", "PH": "φ",
    "T": "ť", "TT": "ţ",
    "K": "ǩ", "KH": "ķ",
    "GG": "ǧ", "GH": "ǥ",
    # back consonants
    "G": "ɣ", "X": "χ", "Q": "ɢ", "R": "ʁ",
}
REVERSE_TRANSLIT: dict[str, str] = {}
for _k, _v in TRANSLIT.items():
    REVERSE_TRANSLIT.setdefault(_v, _k)


def transliterate(text: str) -> str:
    """Convert ASCII-friendly spelling into proper Phyrexian letters.

    String literals (``"..."``) are copied verbatim."""
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        two = text[i : i + 2]
        if two in TRANSLIT:
            out.append(TRANSLIT[two])
            i += 2
            continue
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def untransliterate(text: str) -> str:
    """Inverse of :func:`transliterate` (special letters → ASCII capitals)."""
    return "".join(REVERSE_TRANSLIT.get(ch, ch) for ch in text)


# --------------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------------
def _indent_of(line: str) -> int:
    width = 0
    for ch in line:
        if ch == " ":
            width += 1
        elif ch == "\t":
            width += 4 - (width % 4)
        else:
            break
    return width


def tokenize(source: str, ascii_mode: bool = False) -> list[Token]:
    try:
        return _tokenize(source, ascii_mode)
    except RecursionError as err:
        raise nesting_fault(err) from None


def _tokenize(source: str, ascii_mode: bool = False) -> list[Token]:
    source = unicodedata.normalize("NFC", source.lstrip("\ufeff"))
    if source.startswith("#!"):
        nl = source.find("\n")
        source = "\n" if nl < 0 else "\n" + source[nl + 1 :]
    if ascii_mode:
        source = transliterate(source)

    tokens: list[Token] = []
    lines = source.split("\n")
    for line_no, raw in enumerate(lines, start=1):
        line = raw.rstrip("\r")
        indent = _indent_of(line)
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            col = i + 1

            if ch.isspace():
                i += 1
                continue

            if ch in PUNCTUATION:
                tokens.append(Token(PUNCTUATION[ch], ch, line_no, col, indent))
                i += 1
                continue

            if ch == '"':
                j = i + 1
                buf: list[str] = []
                while j < n and line[j] != '"':
                    if line[j] == "\\" and j + 1 < n:
                        esc = line[j + 1]
                        buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, "\\" + esc))
                        j += 2
                        continue
                    buf.append(line[j])
                    j += 1
                if j >= n:
                    raise LexError("quoted sentence never closes (missing \")", line_no, col)
                tokens.append(Token("STRING", "".join(buf), line_no, col, indent))
                i = j + 1
                continue

            if is_numeral_start(ch):
                j = i + 1
                while j < n and hex_digit(line[j]) is not None:
                    j += 1
                raw = line[i:j]
                ascii_hex = normalize_hex(raw)
                if ascii_hex is None:  # pragma: no cover
                    raise LexError(f"numeral {raw!r} is not hexadecimal", line_no, col)
                if j < n and is_letter(line[j]) and hex_digit(line[j]) is None:
                    raise LexError(
                        f"numeral {raw!r} runs straight into a word; separate them with -",
                        line_no, col,
                    )
                tokens.append(Token("NUMBER", int(ascii_hex, 16), line_no, col, indent))
                i = j
                continue

            if is_letter(ch):
                j = i + 1
                while j < n and is_letter(line[j]):
                    j += 1
                word = line[i:j]
                if j < n and is_numeral_start(line[j]):
                    if word == NEGATIVE_PREFIX:
                        k = j + 1
                        while k < n and hex_digit(line[k]) is not None:
                            k += 1
                        raw = line[j:k]
                        ascii_hex = normalize_hex(raw)
                        if ascii_hex is None:  # pragma: no cover
                            raise LexError(f"numeral {raw!r} is not hexadecimal", line_no, col)
                        if k < n and is_letter(line[k]) and hex_digit(line[k]) is None:
                            raise LexError(
                                f"numeral {raw!r} runs straight into a word; separate them with -",
                                line_no, col,
                            )
                        tokens.append(Token("NUMBER", -int(ascii_hex, 16), line_no, col, indent))
                        i = k
                        continue
                    raise LexError(
                        f"word {word!r} runs straight into a numeral; separate them with -",
                        line_no, col,
                    )
                # ``^rukx`` — a note.  Everything to the end of the line is ignored.
                if word == COMMENT_WORD and tokens and tokens[-1].kind == "START" \
                        and tokens[-1].line == line_no:
                    tokens.pop()
                    i = n
                    continue
                tokens.append(Token("WORD", word, line_no, col, indent))
                i = j
                continue

            raise LexError(f"unknown symbol {ch!r}", line_no, col)

    last_line = len(lines)
    tokens.append(Token("EOF", None, last_line, len(lines[-1]) + 1, 0))
    return tokens
