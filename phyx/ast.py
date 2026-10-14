"""Syntax tree for φyrx programs."""

from __future__ import annotations

from dataclasses import dataclass, field

from .vocabulary import Verb


# ---------------------------------------------------------------- expressions
@dataclass
class Expr:
    line: int = field(default=0, kw_only=True)


@dataclass
class Literal(Expr):
    value: object


@dataclass
class Name(Expr):
    name: str


@dataclass
class Call(Expr):
    """Built-in verb applied to the objects that precede it."""

    verb: Verb
    args: list[Expr]


@dataclass
class UserCall(Expr):
    """A user-defined ability (``ťe`` sentence) applied to its objects."""

    name: str
    args: list[Expr]


@dataclass
class Assign(Expr):
    """``value target ţə''`` — put value into target."""

    target: Expr  # Name or Call(tapq)
    value: Expr
    const: bool = False


@dataclass
class Return(Expr):
    value: Expr | None


@dataclass
class Break(Expr):
    pass


@dataclass
class Continue(Expr):
    pass


# ----------------------------------------------------------------- statements
@dataclass
class Stmt:
    line: int = field(default=0, kw_only=True)


@dataclass
class ExprStmt(Stmt):
    exprs: list[Expr]


@dataclass
class Print(Stmt):
    """``!`` exclamatory sentence."""

    exprs: list[Expr]


@dataclass
class Input(Stmt):
    """``?`` interrogative sentence: ask, store the answer in ``target``."""

    prompt: list[Expr]
    target: Expr


@dataclass
class If(Stmt):
    cond: Expr
    body: list[Stmt]
    negate: bool = False  # ``bu`` / ``əx`` — unless
    orelse: list[Stmt] | None = None
    chained: bool = False  # produced by ``qit-ba`` (else-if); qit attaches to it


@dataclass
class While(Stmt):
    cond: Expr
    body: list[Stmt]


@dataclass
class For(Stmt):
    var: str
    iterable: Expr
    body: list[Stmt]


@dataclass
class FuncDef(Stmt):
    name: str
    params: list[str]
    body: list[Stmt]


@dataclass
class Assert(Stmt):
    cond: Expr
    message: Expr | None


@dataclass
class Try(Stmt):
    body: list[Stmt]
    handler: list[Stmt] | None = None


@dataclass
class Else(Stmt):
    """Transient: a ``qit`` sentence waiting to be attached to the sentence
    before it.  Never survives parsing."""

    body: list[Stmt]
    is_try_handler: bool = False
