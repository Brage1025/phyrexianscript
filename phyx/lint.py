"""Static notes about a φyrx program.  Never invents syntax; only names traps."""

from __future__ import annotations

from dataclasses import dataclass

from . import ast
from .hints import ENGLISH_NAME_TRAPS, ENGLISH_TO_PHYX
from .vocabulary import CONSTANTS, MARKERS, VERBS


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


def lint_program(program: list[ast.Stmt]) -> list[Note]:
    notes: list[Note] = []

    def visit_block(stmts: list[ast.Stmt]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ast.FuncDef):
                used: set[str] = set()
                returns: list[bool] = []
                for s in stmt.body:
                    _walk_stmt(s, used, returns)
                for p in stmt.params:
                    if p not in used:
                        notes.append(Note(
                            stmt.line,
                            f"ability '{stmt.name}' never uses object '{p}'",
                        ))
                if not returns:
                    last = _last_stmt(stmt.body)
                    if last is not None and _discarded_value(last):
                        notes.append(Note(
                            last.line or stmt.line,
                            f"ability '{stmt.name}' computes a value and drops it — "
                            "end the sentence with 'iţpənn to give the value back "
                            "(without it the ability yields əixiww / void)",
                        ))
                visit_block(stmt.body)
            elif isinstance(stmt, ast.If):
                _note_english_name(stmt.cond, notes)
                visit_block(stmt.body)
                if stmt.orelse:
                    visit_block(stmt.orelse)
            elif isinstance(stmt, ast.While):
                _note_english_name(stmt.cond, notes)
                visit_block(stmt.body)
            elif isinstance(stmt, ast.For):
                _note_english_name(stmt.iterable, notes)
                visit_block(stmt.body)
            elif isinstance(stmt, ast.Try):
                visit_block(stmt.body)
                if stmt.handler:
                    visit_block(stmt.handler)
            elif isinstance(stmt, ast.Print):
                for e in stmt.exprs:
                    _note_english_name(e, notes)
            elif isinstance(stmt, ast.ExprStmt):
                for e in stmt.exprs:
                    _note_english_name(e, notes)

    visit_block(program)
    return notes


def _note_english_name(expr: ast.Expr, notes: list[Note]) -> None:
    if isinstance(expr, ast.Name):
        low = expr.name.lower()
        if low in ENGLISH_NAME_TRAPS and expr.name not in VERBS \
                and expr.name not in MARKERS and expr.name not in CONSTANTS:
            phy = ENGLISH_TO_PHYX[low]
            notes.append(Note(
                expr.line,
                f"'{expr.name}' is English; the Phyrexian word is '{phy}' "
                f"(python -m phyx explain {phy})",
            ))
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
