"""Error types. ``ɬšeɴazv`` is Phyrexian for *mistake*."""

from __future__ import annotations


class PhyrexianError(Exception):
    """Base class for every error raised by the toolchain.

    An error answers three questions, in this order:

    1. what broke (``message``)
    2. where (``line`` / ``col`` / ``filename``, plus the caret)
    3. what to do next (``hint``) and how we got here (``frames``)
    """

    kind = "ɬšeɴazv"

    def __init__(
        self,
        message: str,
        line: int | None = None,
        col: int | None = None,
        hint: str | None = None,
        frames: list[str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.frames: list[str] = list(frames or [])
        self.filename: str | None = None
        self.source: str | None = None

    def __str__(self) -> str:  # pragma: no cover - formatting only
        where = ""
        if self.line is not None:
            where = f" (line {self.line}" + (f", col {self.col}" if self.col is not None else "") + ")"
        return f"{self.kind}{where}: {self.message}"


class LexError(PhyrexianError):
    kind = "ɬšeɴazv [symbols]"


class ParseError(PhyrexianError):
    kind = "ɬšeɴazv [grammar]"


class RuntimeFault(PhyrexianError):
    kind = "ɬšeɴazv [runtime]"


class UserMistake(RuntimeFault):
    """Raised by the ``ɬšeɴazv`` verb from inside a program."""

    kind = "ɬšeɴazv [program]"

    def __init__(self, value, line: int | None = None):
        super().__init__(str(value), line)
        self.value = value


def format_error(err: PhyrexianError, source: str | None = None) -> str:
    """Human-readable fault: kind, location, the offending line, a caret, hint, stack."""
    header = str(err)
    if err.filename:
        header = f"{err.filename}: {header}"
    parts = [header]
    src = err.source if err.source is not None else source
    if src and err.line is not None:
        lines = src.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        i = err.line - 1
        if 0 <= i < len(lines):
            text = lines[i]
            parts.append(f"  {err.line:>4} | {text}")
            if err.col is not None and err.col >= 1:
                parts.append(f"       | {' ' * (err.col - 1)}^")
    if err.frames:
        chain = " → ".join(err.frames)
        parts.append(f"  in abilities: {chain}")
    if err.hint:
        parts.append(f"  hint: {err.hint}")
    return "\n".join(parts)
