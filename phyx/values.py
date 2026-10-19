"""Runtime values and how they are written back out in Phyrexian.

Values are plain Python objects: ``int`` (numbers), ``str`` (text), ``bool``
(truth), ``None`` (void), ``list`` and ``dict`` (book).  Numbers are shown in
hexadecimal, exactly as they are written in source, so output can be pasted
back into a program.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .errors import RuntimeFault
from .hints import hint_for_unknown
from .numerals import normalize_hex
from .vocabulary import TYPE_WORDS

if TYPE_CHECKING:  # pragma: no cover
    from . import ast


@dataclass
class Ability:
    """A user-defined verb (``ťe`` sentence)."""

    name: str
    params: list[str]
    body: list["ast.Stmt"] = field(default_factory=list)
    closure: "Env | None" = None
    impl: object = None  # compiled Python callable (interp, *args)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ability {self.name}/{len(self.params)}>"


@dataclass
class Env:
    vars: dict[str, object] = field(default_factory=dict)
    consts: set[str] = field(default_factory=set)
    parent: "Env | None" = None

    def lookup(self, name: str) -> object:
        env: Env | None = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise RuntimeFault(
            f"unknown word '{name}'",
            hint=hint_for_unknown(name),
        )

    def assign(self, name: str, value: object, const: bool = False) -> None:
        if const:
            if name in self.vars:
                raise RuntimeFault(f"'{name}' already has a value here and cannot be fixed in the past ('u)")
            self.vars[name] = value
            self.consts.add(name)
            return
        env: Env | None = self
        while env is not None:
            if name in env.vars:
                if name in env.consts:
                    raise RuntimeFault(f"'{name}' was fixed in the past ('u) and cannot change")
                env.vars[name] = value
                return
            env = env.parent
        self.vars[name] = value


# ------------------------------------------------------------------ helpers
def is_number(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def truthy(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v != 0
    if isinstance(v, (str, list, dict)):
        return len(v) != 0
    if isinstance(v, Ability):
        return True
    return True


def kind_of(v: object) -> str:
    if v is None:
        return "void"
    if isinstance(v, bool):
        return "truth"
    if isinstance(v, int):
        return "number"
    if isinstance(v, str):
        return "text"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "book"
    if isinstance(v, Ability):
        return "ability"
    return type(v).__name__  # pragma: no cover


def type_word(v: object) -> str:
    return TYPE_WORDS.get(kind_of(v), kind_of(v))


def values_equal(a: object, b: object) -> bool:
    try:
        return _values_equal(a, b)
    except RecursionError:
        raise _deep_value() from None


def _values_equal(a: object, b: object) -> bool:
    if kind_of(a) != kind_of(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(_values_equal(x, y) for x, y in zip(a, b))  # type: ignore[arg-type]
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_values_equal(a[k], b[k]) for k in a)  # type: ignore[index]
    return a == b


def _deep_value() -> RuntimeFault:
    return RuntimeFault(
        "this value is nested too deeply",
        hint="a list or book this deep cannot be shown or compared",
    )


def format_number(n: int) -> str:
    digits = format(abs(n), "x")
    if digits[0] not in "0123456789":
        digits = "0" + digits
    return ("əx" if n < 0 else "") + digits


def to_text(v: object) -> str:
    """How a value looks when spoken (``!`` / ``pihš``)."""
    if isinstance(v, str):
        return v
    return to_source(v)


def to_source(v: object) -> str:
    """How a value is written in a program (``krepg``, and items inside lists)."""
    try:
        return _to_source(v)
    except RecursionError:
        raise _deep_value() from None


def _to_source(v: object) -> str:
    if v is None:
        return "əixiww"
    if isinstance(v, bool):
        return "əxbytp" if v else "bytp"
    if isinstance(v, int):
        return format_number(v)
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(v, list):
        parts = [_to_source(x) for x in v] + [format_number(len(v)), "ťewn"]
        return "-".join(parts)
    if isinstance(v, dict):
        parts: list[str] = []
        for k, val in v.items():
            parts.append(_to_source(k))
            parts.append(_to_source(val))
        parts += [format_number(len(v)), "tekt"]
        return "-".join(parts)
    if isinstance(v, Ability):
        return f"naķm{v.name}"  # dictionary: naķm + verb = "one that works as"
    return repr(v)  # pragma: no cover


def parse_number_text(text: str) -> int:
    s = text.strip()
    neg = False
    if s.startswith("əx"):
        neg = True
        s = s[2:]
    elif s.startswith("-"):
        neg = True
        s = s[1:]
    ascii_hex = normalize_hex(s)
    if ascii_hex is None:
        raise RuntimeFault(f"{text!r} is not a hexadecimal numeral")
    n = int(ascii_hex, 16)
    return -n if neg else n
