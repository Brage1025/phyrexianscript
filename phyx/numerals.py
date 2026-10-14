"""Hexadecimal digits: Arabic ``0–9a–f`` and Basilica Mathematical Monospace.

Tutorial chapter 1: Phyrexian counts in sixteen. Phyrexian Regular draws
Arabic numerals on the connecting line. Basilica draws the same sixteen
values with Unicode Mathematical Monospace ``0–9`` and ``A–F``. Those
glyphs are the same numeral syntax, not a second one.
"""

from __future__ import annotations

# U+1D7F6 MATHEMATICAL MONOSPACE DIGIT ZERO … NINE
# U+1D670 MATHEMATICAL MONOSPACE CAPITAL A … F
# U+1D68A MATHEMATICAL MONOSPACE SMALL A … F
_MONO_DIGIT = "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"  # 0-9
_MONO_UPPER = "𝙰𝙱𝙲𝙳𝙴𝙵"  # A-F
_MONO_LOWER = "𝚊𝚋𝚌𝚍𝚎𝚏"  # a-f

BASILICA_TO_ASCII: dict[str, str] = {}
for _i, _ch in enumerate(_MONO_DIGIT):
    BASILICA_TO_ASCII[_ch] = str(_i)
for _i, _ch in enumerate(_MONO_UPPER):
    BASILICA_TO_ASCII[_ch] = "ABCDEF"[_i]
for _i, _ch in enumerate(_MONO_LOWER):
    BASILICA_TO_ASCII[_ch] = "abcdef"[_i]

ASCII_HEX = frozenset("0123456789abcdefABCDEF")
BASILICA_DIGITS = frozenset(BASILICA_TO_ASCII)
ASCII_DIGIT = frozenset("0123456789")


def hex_digit(ch: str) -> str | None:
    """ASCII hex character this glyph contributes, or None."""
    if ch in ASCII_HEX:
        return ch
    return BASILICA_TO_ASCII.get(ch)


def is_numeral_start(ch: str) -> bool:
    """True if ``ch`` may begin a hexadecimal numeral.

    ASCII ``a–f`` do not: they are letters (the name ``a``, the constant
    prefix of many words). Basilica ``𝙰–𝙵`` are digit glyphs and do.
    """
    return ch in ASCII_DIGIT or ch in BASILICA_DIGITS


def normalize_hex(text: str) -> str | None:
    """Basilica + Arabic hex → ASCII hex, or None if a character is not a digit."""
    out: list[str] = []
    for ch in text:
        d = hex_digit(ch)
        if d is None:
            return None
        out.append(d)
    return "".join(out) if out else None
