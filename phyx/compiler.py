"""Compile φyrx to CPython and run it on the host eval loop.

A tree-walker in Python cannot match CPython: every `+` is a method call and
an AST node.  Translating sentences into Python (nested ``def``, ``while``,
integer ``+``) lets the same C eval loop that runs Python run φyrx.  That is
the same architecture CPython itself uses (source → bytecode → PVM), just
with Phyrexian as the source language.

Python's own operators run only when both objects are numbers.  Otherwise a
helper raises ``RuntimeFault``.  ``əx`` uses ``truthy()``, not Python ``not``.

Semantics that are not Python — ``'u`` constants, ``ɬšeɴazv`` messages,
dynamic REPL bindings — go through a few helpers on the interpreter.
"""

from __future__ import annotations

import keyword
import os
import sys
import traceback
from dataclasses import dataclass, field

from . import ast
from .builtins import IMPLS, _hashable, _kinds, put_into
from .errors import RuntimeFault, UserMistake, nesting_fault
from .hints import hint_for_unknown
from .limits import memory_fault, repeat_sequence, take_turns
from .values import Ability, bare_key, to_text, truthy, values_equal
from .vocabulary import BLAME_WORD, GET_WORD

_DUMP = os.environ.get("PHYX_DUMP")


# ------------------------------------------------------------------ helpers used by generated code
def _add(a, b, line=0):
    try:
        ta, tb = type(a), type(b)
        if ta is int and tb is int:
            return a + b
        if ta is str and tb is str:
            return a + b
        if ta is list and tb is list:
            return a + b
    except MemoryError:
        raise memory_fault(line) from None
    raise RuntimeFault(
        f"cannot add {_kinds(a, b)}",
        line,
        hint="babg adds two numbers, two texts, or two lists",
    )


def _sub(a, b, line=0):
    # One object at a time, in order: the tree-walker names only the first
    # value that is not a number.
    if type(a) is not int:
        raise RuntimeFault(f"'mɒɣg' needs a number, got {_kinds(a)}", line)
    if type(b) is not int:
        raise RuntimeFault(f"'mɒɣg' needs a number, got {_kinds(b)}", line)
    return a - b


def _mul(a, b, line=0):
    ta, tb = type(a), type(b)
    if ta is int and tb is int:
        return a * b
    if ta in (str, list) and tb is int:
        return repeat_sequence(a, b, "tøwp (times)", line)
    raise RuntimeFault(f"cannot multiply {_kinds(a, b)}", line)


def _div(a, b, line=0):
    if type(a) is not int:
        raise RuntimeFault(f"'χɬkevk' needs a number, got {_kinds(a)}", line)
    if type(b) is not int:
        raise RuntimeFault(f"'χɬkevk' needs a number, got {_kinds(b)}", line)
    if b == 0:
        raise RuntimeFault(
            "nothing can be distributed into zero parts",
            line,
            hint="χɬkevk is floor division; the second object is the number of parts and cannot be 0",
        )
    return a // b


def _mod(a, b, line=0):
    if type(a) is not int:
        raise RuntimeFault(f"'geft' needs a number, got {_kinds(a)}", line)
    if type(b) is not int:
        raise RuntimeFault(f"'geft' needs a number, got {_kinds(b)}", line)
    if b == 0:
        raise RuntimeFault("nothing remains when dividing by zero", line)
    return a % b


def _twice(a, line=0):
    if type(a) is not int:
        raise RuntimeFault(f"'ķus'ər' needs a number, got {_kinds(a)}", line)
    return a * 2


def _half(a, line=0):
    if type(a) is not int:
        raise RuntimeFault(f"'əxķus'ər' needs a number, got {_kinds(a)}", line)
    return a // 2


def _pow(a, b, line=0):
    if type(a) is not int:
        raise RuntimeFault(f"'lu'f' needs a number, got {_kinds(a)}", line)
    if type(b) is not int:
        raise RuntimeFault(f"'lu'f' needs a number, got {_kinds(b)}", line)
    if b < 0:
        raise RuntimeFault("lu'f (energize) cannot raise to a negative power", line)
    if b > 10_000:
        raise RuntimeFault("lu'f (energize): the exponent is too great", line)
    return a ** b


def _eq(a, b, line=0):
    try:
        return values_equal(a, b)
    except RuntimeFault as err:
        if err.line is None and line:
            err.line = line
        raise


def _lt(a, b, line=0):
    if type(a) is int and type(b) is int:
        return a < b
    if type(a) is str and type(b) is str:
        return a < b
    raise RuntimeFault(f"'grmɒɣg' cannot order {_kinds(a, b)}", line)


def _gt(a, b, line=0):
    if type(a) is int and type(b) is int:
        return a > b
    if type(a) is str and type(b) is str:
        return a > b
    raise RuntimeFault(f"'korxgr' cannot order {_kinds(a, b)}", line)


def _not(a, line=0):
    _ = line
    return not truthy(a)


def _and(a, b, line=0):
    _ = line
    return truthy(a) and truthy(b)


def _or(a, b, line=0):
    _ = line
    return truthy(a) or truthy(b)


def _choose(c, a, b, line=0):
    _ = line
    return a if truthy(c) else b


def _range(n, line=0):
    if type(n) is not int:
        raise RuntimeFault(f"'ronɣ' needs a number, got {_kinds(n)}", line)
    return take_turns(n, line)


def _walk(coll, line=0):
    if isinstance(coll, dict):
        return [bare_key(k) for k in coll]
    if isinstance(coll, (list, str)):
        return list(coll)
    raise RuntimeFault(f"aχəw' (each) cannot walk through {to_text(coll)}", line)


def _put_at(coll, key, value, line=0):
    try:
        put_into(coll, key, value)
    except RuntimeFault as err:
        if err.line is None:
            err.line = line
        raise
    return value


def _mkbook(parts, line=0):
    book = {}
    for i in range(0, len(parts), 2):
        try:
            k = _hashable(parts[i], "tekt")
        except RuntimeFault as err:
            if err.line is None:
                err.line = line
            raise
        book[k] = parts[i + 1]
    return book


def _verb(interp, word, args, line=0):
    impl = IMPLS.get(word)
    if impl is None:  # pragma: no cover
        raise RuntimeFault(f"the verb '{word}' has no implementation", line)
    try:
        return impl(interp, args)
    except RuntimeFault as err:
        if err.line is None:
            err.line = line
        raise


_BIN = {
    "babg": "_add",
    "mɒɣg": "_sub",
    "tøwp": "_mul",
    "χɬkevk": "_div",
    "geft": "_mod",
    "lu'f": "_pow",
    "ǆ'ynpp": "_eq",
    "grmɒɣg": "_lt",
    "korxgr": "_gt",
    "xə": "_and",
    "ðə": "_or",
}
_UNARY = {
    "ķus'ər": "_twice",
    "əxķus'ər": "_half",
    "əx": "_not",
}

# verbs compiled without touching the interpreter object
_INLINE_VERBS = set(_BIN) | set(_UNARY) | {"ʁšθakɴ", "ťewn", "tekt", "ronɣ"}

# These return a number whenever they return. The guarded form rejects every
# other kind, so a later operator can treat the result as a number.
_INT_ONLY_BIN = frozenset({"mɒɣg", "χɬkevk", "geft", "lu'f"})
_INT_ONLY_UNARY = frozenset({"ķus'ər", "əxķus'ər"})
# babg / tøwp return a number when both objects are already numbers.
# They can also join text or repeat a list, so the arguments decide.
_INT_IF_INT_BIN = frozenset({"babg", "tøwp"})
_PLAIN_BIN = {
    "babg": "+",
    "mɒɣg": "-",
    "tøwp": "*",
    "grmɒɣg": "<",
    "korxgr": ">",
    "ǆ'ynpp": "==",
}


def _provably_int(expr: ast.Expr) -> bool:
    """True when ``expr`` yields a number or raises ``RuntimeFault``.

    An integer literal is a number (a truth literal is not: ``bool`` is its
    own kind). A name is not a number, because a parameter or variable can
    hold any kind. ``mɒɣg``, ``χɬkevk``, ``geft``, ``lu'f``, ``ķus'ər`` and
    ``əxķus'ər`` return a number whenever they return. ``babg`` and ``tøwp``
    do too when both of their objects do.
    """
    if isinstance(expr, ast.Literal) and type(expr.value) is int:
        return True
    if not isinstance(expr, ast.Call):
        return False
    word = expr.verb.word
    args = expr.args
    if word in _INT_ONLY_BIN and len(args) == 2:
        return True
    if word in _INT_ONLY_UNARY and len(args) == 1:
        return True
    if word in _INT_IF_INT_BIN and len(args) == 2:
        return _provably_int(args[0]) and _provably_int(args[1])
    return False


def _is_reused_atom(expr: ast.Expr, py: str) -> bool:
    """True when mentioning ``py`` twice evaluates it once.

    A literal has no effect. A name that compiled to one identifier is a
    load of a local. Anything else (a call, ``_rt.load(...)``) must be
    bound before a guard mentions it again.
    """
    if py.isidentifier():
        return True
    return isinstance(expr, ast.Literal)


def _repeated_operands(word: str, args: list[ast.Expr]) -> list[bool]:
    """True when the compiled form of ``word`` mentions that operand twice.

    A second mention is a second evaluation unless the operand is an atom
    or has already been stored in a temporary.
    """
    n = len(args)
    if word in ("xə", "ðə", "əx", "ǆ'ynpp"):
        return [False] * n
    if word in ("ķus'ər", "əxķus'ər") and n == 1 and _provably_int(args[0]):
        return [False]
    if (
        word in _PLAIN_BIN
        and n == 2
        and _provably_int(args[0])
        and _provably_int(args[1])
    ):
        return [False, False]
    if word in _BIN or word in ("ķus'ər", "əxķus'ər"):
        return [True] * n
    return [False] * n


def _literal_text(value: object) -> str:
    """Python spelling of a φyrx literal.

    ``-2 ** 2`` is ``-(2 ** 2)`` in Python. A negative number is parenthesised
    so every operator, including ``lu'f``, sees the negative value.
    """
    if type(value) is int and value < 0:
        return f"({value})"
    return repr(value)


def _fix_here(consts, seen, name, value, const, line):
    """Bind a local ``'u``, or reject a later assignment of that local.

    ``consts`` holds names fixed in this ability. ``seen`` holds names
    already bound here, including a plain assignment before ``'u``.
    """
    if const and name in seen:
        raise RuntimeFault(
            f"'{name}' already has a value here and cannot be fixed in the past ('u)",
            line,
        )
    if name in consts:
        raise RuntimeFault(
            f"'{name}' was fixed in the past ('u) and cannot change",
            line,
        )
    if const:
        consts.add(name)
    seen.add(name)
    return value


def _load_dyn(locs, boxes, gvars, name, line):
    """Read a name that may be local, outer, or not bound yet."""
    if locs is not None and name in locs:
        return locs[name]
    for box in boxes:
        if name in box:
            return box[name]
    if gvars is not None and name in gvars:
        return gvars[name]
    raise RuntimeFault(
        f"unknown word '{name}'",
        line,
        hint=hint_for_unknown(name),
    )


def _store_dyn(locs, boxes, gvars, consts, k, name, value, const, line):
    """Rebind an existing binding, or create a local when none exists yet.

    ``locs`` is this ability's own bindings. ``boxes`` are enclosing
    bindings, nearest first. ``gvars`` is the persistent module environment.
    """
    if locs is not None and name in locs:
        if const or (k is not None and name in k):
            if const:
                raise RuntimeFault(
                    f"'{name}' already has a value here and cannot be fixed in the past ('u)",
                    line,
                )
            raise RuntimeFault(
                f"'{name}' was fixed in the past ('u) and cannot change",
                line,
            )
        locs[name] = value
        return value
    for box in boxes:
        if name in box:
            if const:
                raise RuntimeFault(
                    f"'{name}' already has a value here and cannot be fixed in the past ('u)",
                    line,
                )
            if (consts is not None and name in consts) or (k is not None and name in k):
                raise RuntimeFault(
                    f"'{name}' was fixed in the past ('u) and cannot change",
                    line,
                )
            box[name] = value
            return value
    if gvars is not None and name in gvars:
        if const:
            raise RuntimeFault(
                f"'{name}' already has a value here and cannot be fixed in the past ('u)",
                line,
            )
        if consts is not None and name in consts:
            raise RuntimeFault(
                f"'{name}' was fixed in the past ('u) and cannot change",
                line,
            )
        gvars[name] = value
        return value
    if locs is None:
        raise RuntimeFault(
            f"unknown word '{name}'",
            line,
            hint=hint_for_unknown(name),
        )
    if const and k is not None:
        k.add(name)
    locs[name] = value
    return value


def _is_emitted_literal(py: str) -> bool:
    if py in ("True", "False", "None"):
        return True
    body = py[1:-1] if len(py) >= 2 and py[0] == "(" and py[-1] == ")" else py
    if body.lstrip("-").isdigit():
        return True
    return len(py) >= 2 and py[0] == py[-1] and py[0] in "'\""

_NS_NAMES = {
    "_add": _add,
    "_sub": _sub,
    "_mul": _mul,
    "_div": _div,
    "_mod": _mod,
    "_twice": _twice,
    "_half": _half,
    "_pow": _pow,
    "_eq": _eq,
    "_lt": _lt,
    "_gt": _gt,
    "_not": _not,
    "_and": _and,
    "_or": _or,
    "_choose": _choose,
    "_range": _range,
    "_walk": _walk,
    "_memory_fault": memory_fault,
    "_put_at": _put_at,
    "_mkbook": _mkbook,
    "_verb": _verb,
    "_load_dyn": _load_dyn,
    "_store_dyn": _store_dyn,
    "_fix_here": _fix_here,
    "Ability": Ability,
    "truthy": truthy,
    "to_text": to_text,
    "RuntimeFault": RuntimeFault,
    "UserMistake": UserMistake,
}


def _has_assign(expr: ast.Expr) -> bool:
    if isinstance(expr, ast.Assign):
        return True
    if isinstance(expr, ast.Call):
        return any(_has_assign(a) for a in expr.args)
    if isinstance(expr, ast.UserCall):
        return any(_has_assign(a) for a in expr.args)
    if isinstance(expr, ast.Return) and expr.value is not None:
        return _has_assign(expr.value)
    return False


def _attach_python_frames(err: RuntimeFault, ns: dict, tb=None) -> None:
    names = ns.get("__phyx_names") or {}
    frames: list[str] = []
    for fr in traceback.extract_tb(tb if tb is not None else err.__traceback__):
        phyx = names.get(fr.name)
        if phyx:
            frames.append(phyx)
    if frames and not err.frames:
        err.frames = frames


def py_id(name: str) -> str:
    if name.isidentifier() and not keyword.iskeyword(name) and not name.startswith("_a_"):
        return name
    return "_n_" + "".join(f"{ord(c):x}" for c in name)


def fn_id(name: str) -> str:
    return "_a_" + py_id(name)


@dataclass
class Scope:
    kind: str  # "module" | "func"
    persist: bool = False
    parent: Scope | None = None
    params: set[str] = field(default_factory=set)
    locals_: set[str] = field(default_factory=set)
    funs: dict[str, ast.FuncDef] = field(default_factory=dict)
    nonlocals: set[str] = field(default_factory=set)
    const_names: set[str] = field(default_factory=set)
    calls: set[str] = field(default_factory=set)
    needs_rt: bool = False
    # Names of this scope that a nested ability assigns. They live in ``box``
    # so the ability can see whether the assignment has run yet.
    captured: set[str] = field(default_factory=set)
    # Names this scope stores with a runtime "rebind or create local" check.
    dyn: set[str] = field(default_factory=set)
    box: str | None = None
    locs_name: str | None = None
    needs_locs: bool = False
    # Abilities defined directly in this block. Nested ones are not hoisted.
    hoisted: set[str] = field(default_factory=set)
    # Runtime sets for a local 'u (function scopes only).
    const_set: str | None = None
    seen_set: str | None = None
    # 'u of a name that already exists further out. The local appears when
    # 'u runs, so a read before that still sees the outer binding. The slot
    # name is unique to this scope so a nested ability can read it.
    late_const: set[str] = field(default_factory=set)
    late_slot: dict[str, str] = field(default_factory=dict)

    def bound(self) -> set[str]:
        return set(self.params) | set(self.locals_) | set(self.funs)

    def find(self, name: str) -> Scope | None:
        s: Scope | None = self
        while s is not None:
            if name in s.params or name in s.locals_ or name in s.funs:
                return s
            s = s.parent
        return None


class Emitter:
    def __init__(self, persist: bool):
        self.persist = persist
        self.lines: list[str] = []
        self.indent = 0
        self.n = 0
        self.const_anywhere: set[str] = set()
        self.ability_names: dict[str, str] = {}
        self.box_n = 0

    def emit(self, line: str = "") -> None:
        if line == "":
            self.lines.append("")
            return
        self.lines.append("    " * self.indent + line)

    def tmp(self) -> str:
        self.n += 1
        return f"_t{self.n}"

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"

    # -------------------------------------------------------------- analysis
    def analyze_block(self, stmts: list[ast.Stmt], scope: Scope, hoist: bool) -> None:
        if hoist:
            for stmt in stmts:
                if isinstance(stmt, ast.FuncDef):
                    scope.funs[stmt.name] = stmt
                    scope.hoisted.add(stmt.name)
        # Names assigned in this scope, including inside ba / baxuφ / aχəw' /
        # the tried body, before any ability body is analysed.
        self.collect_assigned(stmts, scope)
        for stmt in stmts:
            self.analyze_stmt(stmt, scope)

    def collect_assigned(self, stmts: list[ast.Stmt], scope: Scope) -> None:
        for stmt in stmts:
            self._collect_stmt(stmt, scope)

    def _collect_stmt(self, stmt: ast.Stmt, scope: Scope) -> None:
        if isinstance(stmt, ast.FuncDef):
            return
        if isinstance(stmt, ast.ExprStmt):
            for e in stmt.exprs:
                self._collect_expr(e, scope)
        elif isinstance(stmt, ast.Print):
            for e in stmt.exprs:
                self._collect_expr(e, scope)
        elif isinstance(stmt, ast.Input):
            for e in stmt.prompt:
                self._collect_expr(e, scope)
            self._collect_target(stmt.target, scope)
        elif isinstance(stmt, ast.If):
            self._collect_expr(stmt.cond, scope)
            self.collect_assigned(stmt.body, scope)
            if stmt.orelse:
                self.collect_assigned(stmt.orelse, scope)
        elif isinstance(stmt, ast.While):
            self._collect_expr(stmt.cond, scope)
            self.collect_assigned(stmt.body, scope)
        elif isinstance(stmt, ast.For):
            self._collect_expr(stmt.iterable, scope)
            self.note_store(stmt.var, scope, const=False)
            self.collect_assigned(stmt.body, scope)
        elif isinstance(stmt, ast.Assert):
            self._collect_expr(stmt.cond, scope)
            if stmt.message is not None:
                self._collect_expr(stmt.message, scope)
        elif isinstance(stmt, ast.Try):
            # The tried body and the handler share this scope.
            self.collect_assigned(stmt.body, scope)
            if stmt.handler:
                self.note_store(BLAME_WORD, scope, const=False)
                self.collect_assigned(stmt.handler, scope)

    def _collect_expr(self, expr: ast.Expr, scope: Scope) -> None:
        if isinstance(expr, ast.Assign):
            self._collect_expr(expr.value, scope)
            self._collect_target(expr.target, scope, const=expr.const)
        elif isinstance(expr, ast.Call):
            for a in expr.args:
                self._collect_expr(a, scope)
        elif isinstance(expr, ast.UserCall):
            for a in expr.args:
                self._collect_expr(a, scope)
        elif isinstance(expr, ast.Return) and expr.value is not None:
            self._collect_expr(expr.value, scope)

    def _collect_target(self, target: ast.Expr, scope: Scope, const: bool = False) -> None:
        if isinstance(target, ast.Name):
            self.note_store(target.name, scope, const)
            return
        if isinstance(target, ast.Call):
            for a in target.args:
                self._collect_expr(a, scope)

    def analyze_stmt(self, stmt: ast.Stmt, scope: Scope) -> None:
        if isinstance(stmt, ast.FuncDef):
            scope.funs[stmt.name] = stmt
            child = Scope(kind="func", persist=False, parent=scope, params=set(stmt.params))
            self.analyze_block(stmt.body, child, hoist=False)
            stmt._phyx_scope = child  # type: ignore[attr-defined]
            return
        if isinstance(stmt, ast.ExprStmt):
            for e in stmt.exprs:
                self.analyze_expr(e, scope)
        elif isinstance(stmt, ast.Print):
            scope.needs_rt = True
            for e in stmt.exprs:
                self.analyze_expr(e, scope)
        elif isinstance(stmt, ast.Input):
            scope.needs_rt = True
            for e in stmt.prompt:
                self.analyze_expr(e, scope)
            self.analyze_store_target(stmt.target, scope)
        elif isinstance(stmt, ast.If):
            self.analyze_expr(stmt.cond, scope)
            self.analyze_block(stmt.body, scope, hoist=False)
            if stmt.orelse:
                self.analyze_block(stmt.orelse, scope, hoist=False)
        elif isinstance(stmt, ast.While):
            self.analyze_expr(stmt.cond, scope)
            self.analyze_block(stmt.body, scope, hoist=False)
        elif isinstance(stmt, ast.For):
            self.analyze_expr(stmt.iterable, scope)
            self.note_store(stmt.var, scope, const=False)
            self.analyze_block(stmt.body, scope, hoist=False)
        elif isinstance(stmt, ast.Assert):
            self.analyze_expr(stmt.cond, scope)
            if stmt.message is not None:
                self.analyze_expr(stmt.message, scope)
        elif isinstance(stmt, ast.Try):
            self.analyze_block(stmt.body, scope, hoist=False)
            if stmt.handler:
                self.note_store(BLAME_WORD, scope, const=False)
                self.analyze_block(stmt.handler, scope, hoist=False)

    def analyze_expr(self, expr: ast.Expr, scope: Scope) -> None:
        if isinstance(expr, (ast.Literal, ast.Break, ast.Continue)):
            return
        if isinstance(expr, ast.Name):
            found = scope.find(expr.name)
            if found is None:
                scope.needs_rt = True
            elif found.kind == "module" and found.persist and expr.name not in found.funs:
                scope.needs_rt = True
            return
        if isinstance(expr, ast.Call):
            if expr.verb.word not in _INLINE_VERBS:
                scope.needs_rt = True
            for a in expr.args:
                self.analyze_expr(a, scope)
            return
        if isinstance(expr, ast.UserCall):
            scope.calls.add(expr.name)
            for a in expr.args:
                self.analyze_expr(a, scope)
            return
        if isinstance(expr, ast.Assign):
            self.analyze_expr(expr.value, scope)
            self.analyze_store_target(expr.target, scope, const=expr.const)
            return
        if isinstance(expr, ast.Return):
            if expr.value is not None:
                self.analyze_expr(expr.value, scope)

    def analyze_store_target(self, target: ast.Expr, scope: Scope, const: bool = False) -> None:
        if isinstance(target, ast.Name):
            self.note_store(target.name, scope, const)
            return
        if isinstance(target, ast.Call):
            for a in target.args:
                self.analyze_expr(a, scope)

    def note_store(self, name: str, scope: Scope, const: bool) -> None:
        if const:
            scope.const_names.add(name)
            self.const_anywhere.add(name)
            scope.needs_rt = True
            if name in scope.params or name in scope.funs:
                return
            # 'u binds in the running scope when it runs. It does not walk
            # outward, and it must not hide an outer binding from a read
            # that happens before it.
            if scope.kind == "func" and self._outer_has(scope, name):
                scope.late_const.add(name)
                return
            scope.locals_.add(name)
            return
        if name in scope.params or name in scope.funs:
            return
        found = scope.parent.find(name) if scope.parent is not None else None
        if found is not None and name in found.funs:
            if not (found.kind == "module" and self.persist):
                scope.nonlocals.add(name)
            return
        if found is not None:
            if name in found.params:
                scope.nonlocals.add(name)
                return
            if self.persist and found.kind == "module":
                scope.dyn.add(name)
                scope.needs_locs = True
                scope.needs_rt = True
                return
            if self.persist and found.kind == "func" and name in found.locals_:
                scope.dyn.add(name)
                scope.needs_locs = True
                scope.needs_rt = True
                return
            # The outer assignment may not have run yet. Remember the name so
            # the store can rebind it when it exists, and create a local when
            # it does not.
            found.captured.add(name)
            scope.dyn.add(name)
            scope.needs_locs = True
            if name in self.const_anywhere:
                scope.needs_rt = True
            return
        if name in scope.locals_:
            return
        if scope.kind == "module" and self.persist:
            scope.locals_.add(name)
            return
        if self.persist and scope.kind == "func":
            scope.locals_.add(name)
            scope.dyn.add(name)
            scope.needs_locs = True
            scope.needs_rt = True
            return
        scope.locals_.add(name)

    def _all_funcs(self, scope: Scope, out: list) -> None:
        for stmt in scope.funs.values():
            child = getattr(stmt, "_phyx_scope", None)
            if child is not None:
                out.append((stmt, child))
                self._all_funcs(child, out)

    def _propagate_rt(self, module: Scope) -> None:
        """If f calls g and g needs the interpreter, f does too."""
        funcs: list[tuple[ast.FuncDef, Scope]] = []
        self._all_funcs(module, funcs)
        changed = True
        while changed:
            changed = False
            for _stmt, child in funcs:
                if child.needs_rt:
                    continue
                for name in child.calls:
                    target = child.find(name)
                    if target is None or name not in target.funs:
                        child.needs_rt = True
                        changed = True
                        break
                    ts = getattr(target.funs[name], "_phyx_scope", None)
                    if ts is not None and ts.needs_rt:
                        child.needs_rt = True
                        changed = True
                        break

    def _prepare(self, scope: Scope) -> None:
        if scope.captured:
            self.box_n += 1
            scope.box = f"_e{self.box_n}"
        if scope.needs_locs:
            self.box_n += 1
            scope.locs_name = f"_l{self.box_n}"
        if scope.late_const:
            for name in sorted(scope.late_const):
                self.box_n += 1
                scope.late_slot[name] = f"_u{self.box_n}"
        tracked = scope.const_names - scope.params - set(scope.funs)
        if scope.kind == "func" and tracked:
            self.box_n += 1
            scope.const_set = f"_c{self.box_n}"
            self.box_n += 1
            scope.seen_set = f"_s{self.box_n}"
        for stmt in scope.funs.values():
            child = getattr(stmt, "_phyx_scope", None)
            if child is not None:
                self._prepare(child)

    def _chain(self, scope: Scope) -> list[str]:
        """Enclosing binding dicts, nearest first."""
        chain: list[str] = []
        s = scope.parent
        while s is not None:
            if s.locs_name:
                chain.append(s.locs_name)
            if s.box:
                chain.append(s.box)
            s = s.parent
        return chain

    def _tuple(self, items: list[str]) -> str:
        if not items:
            return "()"
        if len(items) == 1:
            return f"({items[0]},)"
        return "(" + ", ".join(items) + ")"

    def _dyn_load(self, scope: Scope, name: str, line: int) -> str:
        gvars = "_rt.globals.vars" if self.persist and scope.kind == "func" else "None"
        locs = scope.locs_name or "None"
        return (
            f"_load_dyn({locs}, {self._tuple(self._chain(scope))}, "
            f"{gvars}, {name!r}, {line})"
        )

    def _dyn_store(self, scope: Scope, name: str, val: str, const: bool, line: int) -> str:
        gvars = "_rt.globals.vars" if self.persist and scope.kind == "func" else "None"
        consts = "_rt.globals.consts" if scope.needs_rt or self.persist else "None"
        locs = scope.locs_name or "None"
        k = self._owner_const_set(scope, name)
        return self.bind(
            f"_store_dyn({locs}, {self._tuple(self._chain(scope))}, "
            f"{gvars}, {consts}, {k}, {name!r}, {val}, {const}, {line})"
        )

    def _owner_const_set(self, scope: Scope, name: str) -> str:
        owner = scope.find(name)
        if owner is not None and owner.const_set and name in owner.const_names:
            return owner.const_set
        return "None"

    def _always_bound(self, scope: Scope) -> set[str]:
        """Names that exist for the whole time this scope can run."""
        names: set[str] = set()
        s: Scope | None = scope
        while s is not None:
            if s.kind == "func":
                names |= s.params
            else:
                names |= s.hoisted
            s = s.parent
        return names

    def _outer_has(self, scope: Scope, name: str) -> bool:
        """True when a binding of ``name`` exists outside ``scope``."""
        if scope.parent is not None and scope.parent.find(name) is not None:
            return True
        s = scope.parent
        while s is not None:
            if name in s.late_const:
                return True
            s = s.parent
        return False

    def _closer_late(self, scope: Scope, name: str, found: Scope | None) -> Scope | None:
        """The nearest ``'u`` slot that is inside ``found`` (or anywhere, if none)."""
        s: Scope | None = scope
        while s is not None and s is not found:
            if name in s.late_const:
                return s
            s = s.parent
        return None

    def _outer_dynamic(self, name: str, scope: Scope, found: Scope | None) -> bool:
        if name in scope.dyn:
            return True
        if found is None or found is scope:
            return False
        if name in found.params or name in found.funs:
            return False
        return name in found.captured or name in found.dyn

    # -------------------------------------------------------------- emit
    def compile_program(self, program: list[ast.Stmt]) -> None:
        module = Scope(kind="module", persist=self.persist)
        self.analyze_block(program, module, hoist=True)
        self._propagate_rt(module)
        self._prepare(module)
        self._mark_program(program, module)
        self.emit("def __phyx_run(_rt):")
        self.indent += 1
        if module.box:
            self.emit(f"{module.box} = {{}}")
        if not program:
            self.emit("return")
        else:
            self.emit_block(program, module, hoist=True, in_ability=False, loop_depth=0)
        self.indent -= 1
        self.emit(f"__phyx_names = {self.ability_names!r}")

    def emit_block(
        self,
        stmts: list[ast.Stmt],
        scope: Scope,
        hoist: bool,
        in_ability: bool,
        loop_depth: int,
    ) -> None:
        if hoist:
            funs = [s for s in stmts if isinstance(s, ast.FuncDef)]
            rest = [s for s in stmts if not isinstance(s, ast.FuncDef)]
            for fn in funs:
                self.emit_func(fn, scope)
            if not rest and not funs:
                self.emit("pass")
                return
            mark = len(self.lines)
            for stmt in rest:
                self.emit_stmt(stmt, scope, in_ability, loop_depth)
            if rest and len(self.lines) == mark:
                self.emit("pass")
            return
        if not stmts:
            self.emit("pass")
            return
        mark = len(self.lines)
        for stmt in stmts:
            self.emit_stmt(stmt, scope, in_ability, loop_depth)
        if len(self.lines) == mark:
            self.emit("pass")

    def emit_func(self, stmt: ast.FuncDef, outer: Scope) -> None:
        child: Scope = getattr(stmt, "_phyx_scope", None) or Scope(
            kind="func", parent=outer, params=set(stmt.params)
        )
        user_params = [py_id(p) for p in stmt.params]
        if child.needs_rt:
            params = ", ".join(["_rt"] + user_params)
        else:
            params = ", ".join(user_params)
        self.ability_names[fn_id(stmt.name)] = stmt.name
        self.emit(f"def {fn_id(stmt.name)}({params}):")
        self.indent += 1
        if child.nonlocals:
            names = ", ".join(py_id(n) for n in sorted(child.nonlocals))
            self.emit(f"nonlocal {names}")
        if child.box:
            self.emit(f"{child.box} = {{}}")
        if child.locs_name:
            self.emit(f"{child.locs_name} = {{}}")
        if child.const_set:
            self.emit(f"{child.const_set} = set()")
            self.emit(f"{child.seen_set} = set()")
        if not stmt.body:
            self.emit("return None")
        else:
            self.emit_block(stmt.body, child, hoist=False, in_ability=True, loop_depth=0)
        self.indent -= 1
        impl = fn_id(stmt.name)
        if not child.needs_rt:
            wrap = fn_id(stmt.name) + "_w"
            inner_args = ", ".join(user_params)
            if user_params:
                self.emit(f"def {wrap}(_rt, {inner_args}):")
                self.indent += 1
                self.emit(f"return {fn_id(stmt.name)}({inner_args})")
            else:
                self.emit(f"def {wrap}(_rt):")
                self.indent += 1
                self.emit(f"return {fn_id(stmt.name)}()")
            self.indent -= 1
            impl = wrap
        py = py_id(stmt.name)
        args = ", ".join(repr(p) for p in stmt.params)
        self.emit(
            f"{py} = Ability({stmt.name!r}, [{args}], [], None, {impl})"
        )
        if outer.kind == "module":
            self.emit(f"_rt.export_ability({stmt.name!r}, {py})")

    def emit_stmt(self, stmt: ast.Stmt, scope: Scope, in_ability: bool, loop_depth: int) -> None:
        if isinstance(stmt, ast.FuncDef):
            self.emit_func(stmt, scope)
            return
        if isinstance(stmt, ast.ExprStmt):
            for e in stmt.exprs:
                self.emit_expr_as_stmt(e, scope, in_ability, loop_depth)
            return
        if isinstance(stmt, ast.Print):
            if not stmt.exprs:
                self.emit('_rt.write("\\n")')
                return
            parts = self._in_order(stmt.exprs, scope, True, [False] * len(stmt.exprs))
            self.emit(f"_rt.speak_values([{', '.join(parts)}], {stmt.line})")
            return
        if isinstance(stmt, ast.Input):
            if stmt.prompt:
                bits = self._in_order(stmt.prompt, scope, True, [False] * len(stmt.prompt))
                prompt = f'" ".join(to_text(_v) for _v in ({", ".join(bits)},))'
            else:
                prompt = '""'
            val = f"_rt.read_line({prompt})"
            self.store(stmt.target, val, scope, const=False, line=stmt.line)
            return
        if isinstance(stmt, ast.If):
            cond = self.expr(stmt.cond, scope, bind=False)
            if stmt.negate:
                self.emit(f"if not ({cond}):")
            else:
                self.emit(f"if {cond}:")
            self.indent += 1
            self.emit_block(stmt.body, scope, False, in_ability, loop_depth)
            self.indent -= 1
            if stmt.orelse is not None:
                self.emit("else:")
                self.indent += 1
                self.emit_block(stmt.orelse, scope, False, in_ability, loop_depth)
                self.indent -= 1
            return
        if isinstance(stmt, ast.While):
            # A guard that mentions a call twice would bind it. That binding
            # has to sit inside the loop, so try the condition once: if it
            # needed statements, throw them away and emit them each turn.
            mark = len(self.lines)
            cond = self.expr(stmt.cond, scope, bind=False)
            if len(self.lines) == mark:
                self.emit(f"while {cond}:")
                self.indent += 1
                self.emit_block(stmt.body, scope, False, in_ability, loop_depth + 1)
                self.indent -= 1
                return
            del self.lines[mark:]
            self.emit("while True:")
            self.indent += 1
            cond = self.expr(stmt.cond, scope, bind=False)
            self.emit(f"if not ({cond}):")
            self.indent += 1
            self.emit("break")
            self.indent -= 1
            self.emit_block(stmt.body, scope, False, in_ability, loop_depth + 1)
            self.indent -= 1
            return
        if isinstance(stmt, ast.For):
            it = self.tmp()
            xs = self.expr(stmt.iterable, scope)
            self.emit(f"for {it} in _walk({xs}, {stmt.line}):")
            self.indent += 1
            self.store_name(stmt.var, it, scope, const=False, line=stmt.line)
            self.emit_block(stmt.body, scope, False, in_ability, loop_depth + 1)
            self.indent -= 1
            return
        if isinstance(stmt, ast.Assert):
            msg = ""
            if stmt.message is not None:
                m = self.expr(stmt.message, scope)
                msg = f" + ': ' + to_text({m})"
            cond = self.expr(stmt.cond, scope, bind=False)
            self.emit(f"if not ({cond}):")
            self.indent += 1
            self.emit(
                f"raise RuntimeFault('ǩaπa (must) was not satisfied'{msg}, {stmt.line})"
            )
            self.indent -= 1
            return
        if isinstance(stmt, ast.Try):
            self.emit("try:")
            self.indent += 1
            self.emit("try:")
            self.indent += 1
            self.emit_block(stmt.body, scope, False, in_ability, loop_depth)
            self.indent -= 1
            self.emit("except MemoryError:")
            self.indent += 1
            self.emit(f"raise _memory_fault({stmt.line})")
            self.indent -= 1
            self.indent -= 1
            self.emit("except RuntimeFault as _err:")
            self.indent += 1
            if stmt.handler is None:
                self.emit("pass")
            else:
                blame = "(_err.value if isinstance(_err, UserMistake) else _err.message)"
                self.store_name(BLAME_WORD, blame, scope, False, stmt.line)
                self.emit_block(stmt.handler, scope, False, in_ability, loop_depth)
            self.indent -= 1
            return
        raise RuntimeFault(f"unknown sentence {type(stmt).__name__}", stmt.line)  # pragma: no cover

    def emit_expr_as_stmt(self, expr: ast.Expr, scope: Scope, in_ability: bool, loop_depth: int) -> None:
        if isinstance(expr, ast.Return):
            if not in_ability:
                self.emit(
                    f"raise RuntimeFault(\"'iţpənn (return) used outside of an ability\", {expr.line})"
                )
                return
            if expr.value is None:
                self.emit("return None")
            else:
                self.emit(f"return {self.expr(expr.value, scope, bind=False)}")
            return
        if isinstance(expr, ast.Break):
            if loop_depth <= 0:
                self.emit(
                    f"raise RuntimeFault('lups (stop) used outside of a loop', {expr.line})"
                )
            else:
                self.emit("break")
            return
        if isinstance(expr, ast.Continue):
            if loop_depth <= 0:
                self.emit(
                    f"raise RuntimeFault('ɢnagɮ (next) used outside of a loop', {expr.line})"
                )
            else:
                self.emit("continue")
            return
        if isinstance(expr, ast.Assign):
            self.store(
                expr.target,
                self.expr(expr.value, scope),
                scope,
                expr.const,
                expr.line,
            )
            return
        py = self.expr(expr, scope, bind=False)
        self.emit(py)

    def bind(self, py: str) -> str:
        t = self.tmp()
        self.emit(f"{t} = {py}")
        return t

    def maybe_bind(self, py: str, bind: bool) -> str:
        if bind:
            return self.bind(py)
        return py

    def expr(self, expr: ast.Expr, scope: Scope, bind: bool = True) -> str:
        """Emit any required statements; return a Python expression.

        ``bind=True`` (default) forces an atom (temp name or literal) so the
        result can be reused.  ``bind=False`` keeps a nested expression when
        each object is used once.  A guard that would mention a call twice
        names it first, so the call runs once.
        """
        if isinstance(expr, ast.Literal):
            return _literal_text(expr.value)
        if isinstance(expr, ast.Name):
            return self.load(
                expr.name,
                scope,
                expr.line,
                proven=getattr(expr, "_phyx_proven", False),
            )
        if isinstance(expr, ast.Call):
            return self.emit_call(expr, scope, bind=bind)
        if isinstance(expr, ast.UserCall):
            child_bind = bind or _has_assign(expr)
            args = self._in_order(
                expr.args, scope, child_bind, [False] * len(expr.args)
            )
            arglist = ", ".join(args)
            found = scope.find(expr.name)
            if found is not None and expr.name in found.funs:
                target = found.funs[expr.name]
                ts = getattr(target, "_phyx_scope", None)
                if ts is not None and not ts.needs_rt:
                    call = f"{fn_id(expr.name)}({arglist})" if arglist else f"{fn_id(expr.name)}()"
                else:
                    call = f"{fn_id(expr.name)}(_rt{', ' + arglist if arglist else ''})"
            else:
                listed = f"[{arglist}]" if args else "[]"
                call = f"_rt.invoke({expr.name!r}, {listed}, {expr.line})"
            return self.maybe_bind(call, bind)
        if isinstance(expr, ast.Assign):
            return self.store(
                expr.target,
                self.expr(expr.value, scope),
                scope,
                expr.const,
                expr.line,
            )
        if isinstance(expr, ast.Return):
            raise RuntimeFault("'iţpənn (return) used outside of an ability", expr.line)
        if isinstance(expr, (ast.Break, ast.Continue)):
            raise RuntimeFault("lups (stop) used outside of a loop", expr.line)
        raise RuntimeFault(f"unknown expression {type(expr).__name__}", expr.line)  # pragma: no cover

    def _capture(self, node: ast.Expr, scope: Scope, bind: bool) -> tuple[str, list[str]]:
        mark = len(self.lines)
        py = self.expr(node, scope, bind=bind)
        lines = self.lines[mark:]
        del self.lines[mark:]
        return py, lines

    def _in_order(
        self,
        nodes: list[ast.Expr],
        scope: Scope,
        bind: bool,
        repeat: list[bool],
    ) -> list[str]:
        """Evaluate ``nodes`` left to right.

        When a later operand needs statements (its own, or a temporary
        because a guard mentions it twice), every earlier operand that is
        not a literal is copied into a temporary first.
        """
        captured = [self._capture(node, scope, bind) for node in nodes]
        return self._commit(nodes, captured, repeat)

    def _commit(
        self,
        nodes: list[ast.Expr],
        captured: list[tuple[str, list[str]]],
        repeat: list[bool],
    ) -> list[str]:
        emits = [
            bool(lines) or (repeat[i] and not _is_reused_atom(node, py))
            for i, (node, (py, lines)) in enumerate(zip(nodes, captured, strict=False))
        ]
        pys: list[str] = []
        for i, (node, (py, lines)) in enumerate(zip(nodes, captured, strict=False)):
            later = any(emits[j] for j in range(i + 1, len(emits)))
            self.lines.extend(lines)
            if later and not isinstance(node, ast.Literal):
                py = self.bind(py)
            elif repeat[i] and not _is_reused_atom(node, py):
                py = self.bind(py)
            pys.append(py)
        return pys

    def emit_call(self, expr: ast.Call, scope: Scope, bind: bool = True) -> str:
        word = expr.verb.word
        line = expr.line
        guarded = (word in _BIN and len(expr.args) == 2) or (
            word in _UNARY and len(expr.args) == 1
        )
        repeat = _repeated_operands(word, expr.args) if guarded else [False] * len(expr.args)
        args = self._in_order(expr.args, scope, bind, repeat)
        if word in _BIN and len(args) == 2:
            return self._int_binop(
                word, expr.args[0], expr.args[1], args[0], args[1], line, bind=bind
            )
        if word in _UNARY and len(args) == 1:
            return self._int_unop(word, expr.args[0], args[0], line, bind=bind)
        if word == "ʁšθakɴ" and len(args) == 3:
            return self.maybe_bind(f"_choose({args[0]}, {args[1]}, {args[2]}, {line})", bind)
        if word == "ťewn":
            return self.maybe_bind("[" + ", ".join(args) + "]", bind)
        if word == "tekt":
            return self.maybe_bind(f"_mkbook([{', '.join(args)}], {line})", bind)
        if word == "ronɣ" and len(args) == 1:
            return self.maybe_bind(f"_range({args[0]}, {line})", bind)
        joined = ", ".join(args)
        return self.maybe_bind(f"_verb(_rt, {word!r}, [{joined}], {line})", bind)

    def _int_binop(
        self,
        word: str,
        a_expr: ast.Expr,
        b_expr: ast.Expr,
        a: str,
        b: str,
        line: int,
        bind: bool = True,
    ) -> str:
        """Number ops. Python's operator only when both values are numbers.

        Division, remainder and power keep the zero and range checks even
        then. The type test is left out only when both objects are provably
        numbers; a name never is.
        """
        both_int = _provably_int(a_expr) and _provably_int(b_expr)
        helper = _BIN[word]
        if word in ("xə", "ðə"):
            expr = f"{helper}({a}, {b}, {line})"
        elif word == "ǆ'ynpp" and not both_int:
            # Python `1 == True`. Kinds differ, so equality goes through values_equal.
            expr = f"_eq({a}, {b}, {line})"
        elif both_int and word in _PLAIN_BIN:
            expr = f"({a} {_PLAIN_BIN[word]} {b})"
        else:
            # Operands that a guard mentions twice were stored by ``_in_order``.
            types = f"type({a}) is int and type({b}) is int"
            if word == "χɬkevk":
                guard = b if both_int else f"{types} and {b}"
                expr = f"({a} // {b} if {guard} else _div({a}, {b}, {line}))"
            elif word == "geft":
                guard = b if both_int else f"{types} and {b}"
                expr = f"({a} % {b} if {guard} else _mod({a}, {b}, {line}))"
            elif word == "lu'f":
                span = f"0 <= {b} <= 10000"
                guard = span if both_int else f"{types} and {span}"
                expr = f"({a} ** {b} if {guard} else _pow({a}, {b}, {line}))"
            else:
                # Ordering uses the same guard: `0 < True` is not a φyrx comparison.
                expr = f"({a} {_PLAIN_BIN[word]} {b} if {types} else {helper}({a}, {b}, {line}))"
        return self.maybe_bind(expr, bind)

    def _int_unop(
        self, word: str, a_expr: ast.Expr, a: str, line: int, bind: bool = True
    ) -> str:
        if word == "əx":
            # Python `not` is not φyrx truth. `_not` calls truthy().
            expr = f"_not({a}, {line})"
        elif word in ("ķus'ər", "əxķus'ər"):
            op = "*" if word == "ķus'ər" else "//"
            helper = "_twice" if word == "ķus'ər" else "_half"
            if _provably_int(a_expr):
                expr = f"({a} {op} 2)"
            else:
                expr = f"({a} {op} 2 if type({a}) is int else {helper}({a}, {line}))"
        else:
            expr = f"{_UNARY[word]}({a}, {line})"
        return self.maybe_bind(expr, bind)

    def load(self, name: str, scope: Scope, line: int, proven: bool = False) -> str:
        found = scope.find(name)
        late = self._closer_late(scope, name, found)
        if late is not None:
            return self._load_late(name, late, line)
        if self._outer_dynamic(name, scope, found):
            return self._dyn_load(scope, name, line)
        if found is None:
            return f"_rt.load({name!r}, {line})"
        if found.kind == "module" and found.persist and name not in found.funs:
            return f"_rt.load({name!r}, {line})"
        if found is scope and name in scope.captured:
            return f"_load_dyn(None, ({scope.box},), None, {name!r}, {line})"
        py = py_id(name)
        if proven:
            return py
        return self._checked_load(py, name, line)

    def _checked_load(self, py: str, name: str, line: int) -> str:
        """A Python local the analysis cannot prove is bound before this read."""
        tmp = self.tmp()
        hint = hint_for_unknown(name)
        self.emit("try:")
        self.indent += 1
        self.emit(f"{tmp} = {py}")
        self.indent -= 1
        # A local read raises UnboundLocalError. A free variable that the
        # enclosing scope has not bound yet raises NameError (3.14+).
        self.emit("except NameError:")
        self.indent += 1
        self.emit(
            f"raise RuntimeFault({f'unknown word {name!r}'!r}, {line}, hint={hint!r})"
        )
        self.indent -= 1
        return tmp

    def _load_late(self, name: str, late: Scope, line: int) -> str:
        """Read a ``'u`` local, or the binding outside it when ``'u`` has not run."""
        tmp = self.tmp()
        slot = late.late_slot[name]
        self.emit("try:")
        self.indent += 1
        self.emit(f"{tmp} = {slot}")
        self.indent -= 1
        self.emit("except NameError:")
        self.indent += 1
        outer = late.parent
        if outer is None:  # pragma: no cover - 'u shadows something outside this scope
            hint = hint_for_unknown(name)
            self.emit(
                f"raise RuntimeFault({f'unknown word {name!r}'!r}, {line}, hint={hint!r})"
            )
            self.emit(f"{tmp} = None")
        else:
            loaded = self.load(name, outer, line)
            self.emit(f"{tmp} = {loaded}")
        self.indent -= 1
        return tmp

    def _late_plain_scopes(self, scope: Scope, name: str) -> list[Scope]:
        """``'u`` slots a plain assignment must see, nearest first.

        A slot that does not exist yet is skipped: the assignment walks
        onward. A slot that exists was fixed, so the assignment faults.
        The walk stops at a parameter or ability, which is always bound.
        """
        found: list[Scope] = []
        s: Scope | None = scope
        while s is not None:
            if name in s.params or name in s.funs:
                break
            if name in s.late_const:
                found.append(s)
            s = s.parent
        return found

    def _store_own_late(self, name: str, val: str, scope: Scope, line: int) -> str:
        """``'u`` in the ability that owns the slot. It does not walk outward."""
        slot = scope.late_slot[name]
        rhs = (
            f"_fix_here({scope.const_set}, {scope.seen_set}, {name!r}, "
            f"{val}, True, {line})"
        )
        self.emit(f"{slot} = {rhs}")
        return slot

    def _store_guard(
        self,
        slots: list[Scope],
        name: str,
        val: str,
        scope: Scope,
        line: int,
    ) -> str:
        """Plain assignment that may meet a ``'u`` slot closer than the outer binding."""
        if not slots:
            return self._store_resolved(name, val, scope, False, line)
        slot = slots[0].late_slot[name]
        tmp = self.tmp()
        self.emit("try:")
        self.indent += 1
        self.emit(f"{tmp} = {slot}")
        self.indent -= 1
        self.emit("except NameError:")
        self.indent += 1
        rebound = self._store_guard(slots[1:], name, val, scope, line)
        self.emit(f"{tmp} = {rebound}")
        self.indent -= 1
        self.emit("else:")
        self.indent += 1
        msg = f"'{name}' was fixed in the past ('u) and cannot change"
        self.emit(f"raise RuntimeFault({msg!r}, {line})")
        self.indent -= 1
        return tmp

    def _store_local_const(
        self,
        name: str,
        val: str,
        scope: Scope,
        const: bool,
        line: int,
    ) -> str:
        """'u in an ability binds here, even when an outer name has the same spelling."""
        rhs = (
            f"_fix_here({scope.const_set}, {scope.seen_set}, {name!r}, "
            f"{val}, {const}, {line})"
        )
        if name in scope.captured and scope.box:
            self.emit(f"{scope.box}[{name!r}] = {rhs}")
            return f"{scope.box}[{name!r}]"
        py = py_id(name)
        self.emit(f"{py} = {rhs}")
        return py

    def _mark_program(self, program: list[ast.Stmt], module: Scope) -> None:
        for stmt in module.funs.values():
            self._mark_func(stmt)
        self._mark_block(program, module, set(module.hoisted), skip_funcs=True)

    def _mark_func(self, stmt: ast.FuncDef) -> None:
        child: Scope | None = getattr(stmt, "_phyx_scope", None)
        if child is None:
            return
        for nested in child.funs.values():
            self._mark_func(nested)
        self._mark_block(stmt.body, child, set(stmt.params), skip_funcs=False)

    def _mark_block(
        self,
        stmts: list[ast.Stmt],
        scope: Scope,
        proven: set[str],
        skip_funcs: bool,
    ) -> set[str]:
        for stmt in stmts:
            if skip_funcs and isinstance(stmt, ast.FuncDef):
                continue
            proven = self._mark_stmt(stmt, scope, proven)
        return proven

    def _mark_stmt(self, stmt: ast.Stmt, scope: Scope, proven: set[str]) -> set[str]:
        if isinstance(stmt, ast.FuncDef):
            self._mark_func(stmt)
            return proven | {stmt.name}
        if isinstance(stmt, ast.ExprStmt):
            for e in stmt.exprs:
                proven = self._mark_expr(e, scope, proven)
            return proven
        if isinstance(stmt, ast.Print):
            for e in stmt.exprs:
                proven = self._mark_expr(e, scope, proven)
            return proven
        if isinstance(stmt, ast.Input):
            for e in stmt.prompt:
                proven = self._mark_expr(e, scope, proven)
            if isinstance(stmt.target, ast.Name):
                return proven | {stmt.target.name}
            return self._mark_expr(stmt.target, scope, proven)
        if isinstance(stmt, ast.If):
            proven = self._mark_expr(stmt.cond, scope, proven)
            then_p = self._mark_block(stmt.body, scope, proven, skip_funcs=False)
            if stmt.orelse:
                else_p = self._mark_block(stmt.orelse, scope, proven, skip_funcs=False)
            else:
                else_p = proven
            return then_p & else_p
        if isinstance(stmt, ast.While):
            self._mark_expr(stmt.cond, scope, proven)
            self._mark_block(stmt.body, scope, proven, skip_funcs=False)
            return proven
        if isinstance(stmt, ast.For):
            proven = self._mark_expr(stmt.iterable, scope, proven)
            self._mark_block(stmt.body, scope, proven | {stmt.var}, skip_funcs=False)
            return proven
        if isinstance(stmt, ast.Assert):
            proven = self._mark_expr(stmt.cond, scope, proven)
            if stmt.message is not None:
                proven = self._mark_expr(stmt.message, scope, proven)
            return proven
        if isinstance(stmt, ast.Try):
            body_p = self._mark_block(stmt.body, scope, proven, skip_funcs=False)
            if stmt.handler:
                hand_p = self._mark_block(
                    stmt.handler, scope, proven | {BLAME_WORD}, skip_funcs=False
                )
                return body_p & hand_p
            return body_p
        return proven

    def _mark_expr(self, expr: ast.Expr, scope: Scope, proven: set[str]) -> set[str]:
        if isinstance(expr, ast.Name):
            expr._phyx_proven = (  # type: ignore[attr-defined]
                expr.name in proven or expr.name in self._always_bound(scope)
            )
            return proven
        if isinstance(expr, (ast.Literal, ast.Break, ast.Continue)):
            return proven
        if isinstance(expr, ast.Assign):
            proven = self._mark_expr(expr.value, scope, proven)
            if isinstance(expr.target, ast.Name):
                return proven | {expr.target.name}
            return self._mark_expr(expr.target, scope, proven)
        if isinstance(expr, (ast.Call, ast.UserCall)):
            for a in expr.args:
                proven = self._mark_expr(a, scope, proven)
            return proven
        if isinstance(expr, ast.Return) and expr.value is not None:
            return self._mark_expr(expr.value, scope, proven)
        return proven

    def store(
        self,
        target: ast.Expr,
        val: str,
        scope: Scope,
        const: bool,
        line: int,
    ) -> str:
        if isinstance(target, ast.Name):
            return self.store_name(target.name, val, scope, const, line)
        if isinstance(target, ast.Call) and target.verb.word == GET_WORD:
            # The value was evaluated first. Copy it before the place's
            # statements, then evaluate the place left to right.
            caps = [self._capture(node, scope, True) for node in target.args]
            if any(lines for _, lines in caps) and not _is_emitted_literal(val):
                val = self.bind(val)
            coll, key = self._commit(list(target.args), caps, [False, False])
            return self.bind(f"_put_at({coll}, {key}, {val}, {line})")
        raise RuntimeFault("cannot put a value there", line)  # pragma: no cover

    def store_name(
        self,
        name: str,
        val: str,
        scope: Scope,
        const: bool,
        line: int,
    ) -> str:
        if scope.kind == "func" and const and name in scope.late_const:
            return self._store_own_late(name, val, scope, line)
        if scope.kind == "func" and not const:
            slots = self._late_plain_scopes(scope, name)
            if slots:
                return self._store_guard(slots, name, val, scope, line)
        return self._store_resolved(name, val, scope, const, line)

    def _store_resolved(
        self,
        name: str,
        val: str,
        scope: Scope,
        const: bool,
        line: int,
    ) -> str:
        py = py_id(name)
        found = scope.find(name)
        if (
            scope.kind == "func"
            and const
            and (name in scope.params or name in scope.funs)
        ):
            already = (
                f"'{name}' already has a value here and cannot be fixed in the past ('u)"
            )
            self.emit(f"raise RuntimeFault({already!r}, {line})")
            return "None"
        if (
            scope.kind == "func"
            and name in scope.const_names
            and name not in scope.late_const
            and name not in scope.params
            and name not in scope.funs
        ):
            return self._store_local_const(name, val, scope, const, line)
        if self._outer_dynamic(name, scope, found):
            return self._dyn_store(scope, name, val, const, line)
        if scope.kind == "module" and self.persist and name not in scope.funs:
            if const:
                rhs = f"_rt.fix({name!r}, {val}, {line})"
            else:
                rhs = f"_rt.setv({name!r}, {val}, {line}, True)"
            return self.bind(rhs)
        if found is scope and name in scope.captured:
            if const:
                rhs = f"_rt.fix({name!r}, {val}, {line})"
            elif name in self.const_anywhere:
                rhs = f"_rt.setv({name!r}, {val}, {line}, {self.persist})"
            else:
                rhs = val
            self.emit(f"{scope.box}[{name!r}] = {rhs}")
            return f"{scope.box}[{name!r}]"
        persist_env = scope.kind == "module" or (
            found is not None
            and found.kind == "module"
            and name not in found.funs
        )
        need_env = persist_env and (self.persist or name in self.const_anywhere)
        if const:
            rhs = f"_rt.fix({name!r}, {val}, {line})"
        elif need_env:
            rhs = f"_rt.setv({name!r}, {val}, {line}, {self.persist})"
        else:
            rhs = val
        nameless = persist_env and scope.kind == "module" and scope.persist and found is None
        if nameless:
            return self.bind(rhs)
        self.emit(f"{py} = {rhs}")
        return py


def compile_to_python(program: list[ast.Stmt], persist: bool = False) -> str:
    """Return the CPython source a φyrx program compiles to."""
    try:
        em = Emitter(persist=persist)
        em.compile_program(program)
        return em.text()
    except RecursionError as err:
        raise nesting_fault(err) from None


def run_compiled(interp, program: list[ast.Stmt], persist: bool = False) -> None:
    src = compile_to_python(program, persist=persist)
    if _DUMP:
        print(src, file=sys.stderr)
    try:
        code = compile(src, "<φyrx>", "exec")
    except SyntaxError as err:  # pragma: no cover - compiler bug
        raise RuntimeFault(f"internal compiler error: {err}") from err
    ns = dict(_NS_NAMES)
    exec(code, ns)
    try:
        ns["__phyx_run"](interp)
    except MemoryError:
        raise memory_fault() from None
    except RecursionError as err:
        fault = RuntimeFault("the abilities called each other too deeply")
        _attach_python_frames(fault, ns, err.__traceback__)
        raise fault from None
    except RuntimeFault as err:
        _attach_python_frames(err, ns)
        raise
