"""Vertical reading flow.

Phyrexian is read *vertically*: symbols top-to-bottom along a line, and lines
left-to-right (tutorial, chapter 1).  A ``.phyx`` file stores each such line as
one text row, which is convenient for editors.  These helpers convert between
that storage form and a true vertical layout (``.vphyx``) where every source
line is a column of characters::

    ^xe-5-x-ţə''.          ^ ! ^
    !x.                    x x '
    ^'u-1-k-ţə''.    <->   e . u
                           -   -
                           5   1
                           ...

Every Phyrexian letter is a single code point (text is NFC-normalised), so
columns are exactly one character wide and are separated by ``gap`` blank
columns.
"""

from __future__ import annotations

import unicodedata


def to_vertical(source: str, gap: int = 1) -> str:
    """Horizontal (one line per row) → vertical (one line per column)."""
    source = unicodedata.normalize("NFC", source.lstrip("\ufeff"))
    lines = [ln.rstrip("\r").expandtabs(4) for ln in source.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    height = max((len(ln) for ln in lines), default=0)
    pad = " " * gap
    rows: list[str] = []
    for r in range(height):
        cells = [(ln[r] if r < len(ln) else " ") for ln in lines]
        rows.append(pad.join(cells).rstrip())
    return "\n".join(rows) + ("\n" if rows else "")


def from_vertical(text: str, gap: int = 1) -> str:
    """Vertical (one line per column) → horizontal (one line per row)."""
    text = unicodedata.normalize("NFC", text.lstrip("\ufeff"))
    rows = [ln.rstrip("\r") for ln in text.split("\n")]
    while rows and rows[-1] == "":
        rows.pop()
    width = max((len(r) for r in rows), default=0)
    step = 1 + gap
    n_cols = (width + step - 1) // step
    lines: list[str] = []
    for c in range(n_cols):
        x = c * step
        chars = []
        for row in rows:
            chars.append(row[x] if x < len(row) else " ")
            # anything in the gap columns is a layout error
            for g in range(1, step):
                if x + g < len(row) and row[x + g] != " ":
                    raise ValueError(
                        f"vertical layout: character {row[x + g]!r} sits between columns "
                        f"(row {rows.index(row) + 1}, position {x + g + 1}); columns must be "
                        f"{gap} space{'s' if gap != 1 else ''} apart"
                    )
        lines.append("".join(chars).rstrip())
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")
