"""Canonical layout for a φyrx text: indent of four, ``-`` between words.

Comments (``^rukx``) and the shebang are kept.  The formatter does not
invent sentences; it only rewrites punctuation and spacing of what is there.
"""

from __future__ import annotations

from .errors import nesting_fault
from .lexer import tokenize
from .values import format_number, to_source


def _round4(n: int) -> int:
    if n <= 0:
        return 0
    return (n + 3) // 4 * 4


def _indent_width(line: str) -> int:
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        elif ch == "\t":
            n = (n // 4 + 1) * 4
        else:
            break
    return n


def _join_tokens(group) -> str:
    chunks: list[str] = []
    last_was_atom = False
    for tok in group:
        if tok.kind == "SEP":
            continue
        if tok.kind == "START":
            chunks.append(str(tok.value))
            last_was_atom = False
            continue
        if tok.kind == "COMMA":
            chunks.append(",")
            last_was_atom = False
            continue
        if tok.kind == "END":
            chunks.append(".")
            last_was_atom = False
            continue
        if tok.kind == "COLON":
            chunks.append(":")
            last_was_atom = False
            continue
        if tok.kind == "NUMBER":
            piece = format_number(int(tok.value))
        elif tok.kind == "STRING":
            piece = to_source(tok.value)
        else:
            piece = str(tok.value)
        if last_was_atom:
            chunks.append("-")
        chunks.append(piece)
        last_was_atom = True
    return "".join(chunks)


def format_source(source: str) -> str:
    """Return ``source`` with canonical separators and 4-space indents."""
    try:
        return _format_source(source)
    except RecursionError as err:
        raise nesting_fault(err) from None


def _format_source(source: str) -> str:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    toks = tokenize(source)
    by_line: dict[int, list] = {}
    for tok in toks:
        if tok.kind == "EOF":
            continue
        by_line.setdefault(tok.line, []).append(tok)

    out: list[str] = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue
        if stripped.startswith("#!") or stripped.startswith("^rukx"):
            out.append(" " * _round4(_indent_width(line)) + stripped)
            continue
        group = by_line.get(i)
        if not group:
            out.append(line.rstrip())
            continue
        indent = _round4(group[0].indent)
        out.append(" " * indent + _join_tokens(group))
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + ("\n" if out else "")
