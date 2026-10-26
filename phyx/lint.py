"""Static notes about a φyrx program.  Never invents syntax; only names traps."""

from __future__ import annotations

from dataclasses import dataclass

from . import ast
from .errors import nesting_fault
from .hints import ENGLISH_NAME_TRAPS, ENGLISH_TO_PHYX
from .vocabulary import CONSTANTS, MARKERS, QUOTE_WORD, VERBS

# čtəčpliɣn's second object is the ability being activated.
_ACTIVATE_WORD = "čtəčpliɣn"


@dataclass(frozen=True)
class Note:
    line: int
    message: str


def _walk_expr(expr: ast.Expr, names: set[str]) -> None:
    if isinstance(expr, ast.Name):
        names.add(expr.name)
        return
    if isinstance(expr, ast.Call):
        for a in expr.args:
            _walk_expr(a, names)
        return
    if isinstance(expr, ast.UserCall):
        names.add(expr.name)
        for a in expr.args:
            _walk_expr(a, names)
        return
    if isinstance(expr, ast.Assign):
        _walk_expr(expr.value, names)
        _walk_expr(expr.target, names)
        return
    if isinstance(expr, ast.Return) and expr.value is not None:
        _walk_expr(expr.value, names)


def _walk_stmt(stmt: ast.Stmt, names: set[str], returns: list[bool]) -> None:
    if isinstance(stmt, ast.ExprStmt):
        for e in stmt.exprs:
            _walk_expr(e, names)
            if isinstance(e, ast.Return):
                returns.append(True)
        return
    if isinstance(stmt, ast.Print):
        for e in stmt.exprs:
            _walk_expr(e, names)
        return
    if isinstance(stmt, ast.Input):
        for e in stmt.prompt:
            _walk_expr(e, names)
        _walk_expr(stmt.target, names)
        return
    if isinstance(stmt, ast.If):
        _walk_expr(stmt.cond, names)
        for s in stmt.body:
            _walk_stmt(s, names, returns)
        if stmt.orelse:
            for s in stmt.orelse:
                _walk_stmt(s, names, returns)
        return
    if isinstance(stmt, ast.While):
        _walk_expr(stmt.cond, names)
        for s in stmt.body:
            _walk_stmt(s, names, returns)
        return
    if isinstance(stmt, ast.For):
        names.add(stmt.var)
        _walk_expr(stmt.iterable, names)
        for s in stmt.body:
            _walk_stmt(s, names, returns)
        return
    if isinstance(stmt, ast.FuncDef):
        inner: set[str] = set()
        inner_ret: list[bool] = []
        for s in stmt.body:
            _walk_stmt(s, inner, inner_ret)
        names.update(inner)
        return
    if isinstance(stmt, ast.Assert):
        _walk_expr(stmt.cond, names)
        if stmt.message is not None:
            _walk_expr(stmt.message, names)
        return
    if isinstance(stmt, ast.Try):
        for s in stmt.body:
            _walk_stmt(s, names, returns)
        if stmt.handler:
            for s in stmt.handler:
                _walk_stmt(s, names, returns)


def _last_stmt(body: list[ast.Stmt]) -> ast.Stmt | None:
    return body[-1] if body else None


def _discarded_value(stmt: ast.Stmt) -> bool:
    """True when the last sentence computes something and throws it away."""
    if not isinstance(stmt, ast.ExprStmt) or not stmt.exprs:
        return False
    last = stmt.exprs[-1]
    if isinstance(last, (ast.Assign, ast.Return, ast.Break, ast.Continue)):
        return False
    return isinstance(last, (ast.Call, ast.UserCall, ast.Name, ast.Literal))


def _collect_arities(stmts: list[ast.Stmt], arities: dict[str, int]) -> None:
    """Every ``ťe`` in the program, including ones used before their definition."""
    for stmt in stmts:
        if isinstance(stmt, ast.FuncDef):
            arities[stmt.name] = len(stmt.params)
            _collect_arities(stmt.body, arities)
        elif isinstance(stmt, ast.If):
            _collect_arities(stmt.body, arities)
            if stmt.orelse:
                _collect_arities(stmt.orelse, arities)
        elif isinstance(stmt, ast.While):
            _collect_arities(stmt.body, arities)
        elif isinstance(stmt, ast.For):
            _collect_arities(stmt.body, arities)
        elif isinstance(stmt, ast.Try):
            _collect_arities(stmt.body, arities)
            if stmt.handler:
                _collect_arities(stmt.handler, arities)


def _short_message(name: str, want: int, got: int) -> str:
    noun = "object" if want == 1 else "objects"
    return (
        f"ability '{name}' wants {want} {noun} but got {got} — quote it with {QUOTE_WORD} if you wanted the ability as a value"
    )


def _quoted(parent: ast.Expr | None, index: int) -> bool:
    return isinstance(parent, ast.Call) and parent.verb.word == QUOTE_WORD and index == 0


def _activated(parent: ast.Expr | None, index: int) -> bool:
    """The ability operand of ``čtəčpliɣn`` (args, then the ability)."""
    return isinstance(parent, ast.Call) and parent.verb.word == _ACTIVATE_WORD and index == 1


def _note_short_ability(
    exprs: list[ast.Expr],
    arities: dict[str, int],
    notes: list[Note],
) -> None:
    """An ability name left on the phrase was the parser's "not enough objects" branch.

    The count is how many values the phrase had already built when the name was read.
    ``naķm`` quotes the ability, and ``čtəčpliɣn`` takes it as the ability to activate.
    """
    if not arities:
        return
    depth = 0

    def consider(expr: ast.Name, got: int, parent: ast.Expr | None, index: int) -> None:
        want = arities.get(expr.name)
        if want is None or want < 1 or _quoted(parent, index) or _activated(parent, index):
            return
        notes.append(Note(expr.line, _short_message(expr.name, want, got)))

    def emit(expr: ast.Expr, parent: ast.Expr | None = None, index: int = 0) -> None:
        nonlocal depth
        if isinstance(expr, ast.Name):
            consider(expr, depth, parent, index)
            depth += 1
            return
        if isinstance(expr, (ast.Literal, ast.Break, ast.Continue)):
            depth += 1
            return
        if isinstance(expr, ast.Return):
            if expr.value is not None:
                emit(expr.value)
                # ``'iţpənn`` pops that value and pushes the return.
                return
            depth += 1
            return
        if isinstance(expr, ast.Assign):
            emit(expr.value)
            emit(expr.target)
            depth -= 1
            return
        if isinstance(expr, (ast.Call, ast.UserCall)):
            for i, arg in enumerate(expr.args):
                emit(arg, expr, i)
            # The verb pops its objects and pushes one result. A counted verb
            # (ťewn / tekt) also pops the numeral, which is not kept in the tree;
            # that push and pop cancel, so the depth change is the same.
            depth -= len(expr.args)
            depth += 1
            return

    for expr in exprs:
        emit(expr)


def lint_program(program: list[ast.Stmt]) -> list[Note]:
    try:
        return _lint_program(program)
    except RecursionError as err:
        raise nesting_fault(err) from None


def _lint_program(program: list[ast.Stmt]) -> list[Note]:
    notes: list[Note] = []
    arities: dict[str, int] = {}
    _collect_arities(program, arities)

    def visit_block(stmts: list[ast.Stmt]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ast.FuncDef):
                used: set[str] = set()
                returns: list[bool] = []
                for s in stmt.body:
                    _walk_stmt(s, used, returns)
                for p in stmt.params:
                    if p not in used:
                        notes.append(
                            Note(
                                stmt.line,
                                f"ability '{stmt.name}' never uses object '{p}'",
                            )
                        )
                if not returns:
                    last = _last_stmt(stmt.body)
                    if last is not None and _discarded_value(last):
                        notes.append(
                            Note(
                                last.line or stmt.line,
                                f"ability '{stmt.name}' computes a value and drops it — "
                                "end the sentence with 'iţpənn to give the value back "
                                "(without it the ability yields əixiww / void)",
                            )
                        )
                visit_block(stmt.body)
            elif isinstance(stmt, ast.If):
                _note_english_name(stmt.cond, notes)
                _note_short_ability([stmt.cond], arities, notes)
                visit_block(stmt.body)
                if stmt.orelse:
                    visit_block(stmt.orelse)
            elif isinstance(stmt, ast.While):
                _note_english_name(stmt.cond, notes)
                _note_short_ability([stmt.cond], arities, notes)
                visit_block(stmt.body)
            elif isinstance(stmt, ast.For):
                _note_english_name(stmt.iterable, notes)
                _note_short_ability([stmt.iterable], arities, notes)
                visit_block(stmt.body)
            elif isinstance(stmt, ast.Try):
                visit_block(stmt.body)
                if stmt.handler:
                    visit_block(stmt.handler)
            elif isinstance(stmt, ast.Print):
                for e in stmt.exprs:
                    _note_english_name(e, notes)
                _note_short_ability(stmt.exprs, arities, notes)
            elif isinstance(stmt, ast.ExprStmt):
                for e in stmt.exprs:
                    _note_english_name(e, notes)
                _note_short_ability(stmt.exprs, arities, notes)
            elif isinstance(stmt, ast.Input):
                _note_short_ability([*stmt.prompt, stmt.target], arities, notes)
            elif isinstance(stmt, ast.Assert):
                phrase = [stmt.cond]
                if stmt.message is not None:
                    phrase.append(stmt.message)
                _note_short_ability(phrase, arities, notes)

    visit_block(program)
    return notes


def _note_english_name(expr: ast.Expr, notes: list[Note]) -> None:
    if isinstance(expr, ast.Name):
        low = expr.name.lower()
        if low in ENGLISH_NAME_TRAPS and expr.name not in VERBS and expr.name not in MARKERS and expr.name not in CONSTANTS:
            phy = ENGLISH_TO_PHYX[low]
            notes.append(
                Note(
                    expr.line,
                    f"'{expr.name}' is English; the Phyrexian word is '{phy}' (python -m phyx explain {phy})",
                )
            )
        return
    if isinstance(expr, ast.Call):
        for a in expr.args:
            _note_english_name(a, notes)
        return
    if isinstance(expr, ast.UserCall):
        for a in expr.args:
            _note_english_name(a, notes)
        return
    if isinstance(expr, ast.Assign):
        _note_english_name(expr.value, notes)
        _note_english_name(expr.target, notes)
        return
    if isinstance(expr, ast.Return) and expr.value is not None:
        _note_english_name(expr.value, notes)


def format_notes(notes: list[Note], path: str = "") -> str:
    lines = []
    prefix = f"{path}: " if path else ""
    for n in notes:
        lines.append(f"{prefix}line {n.line}: {n.message}")
    return "\n".join(lines)
