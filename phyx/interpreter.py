"""Evaluator for φyrx: compile to CPython, with a tree-walker as fallback."""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import IO

from . import ast
from .builtins import IMPLS, put_into
from .errors import PhyrexianError, RuntimeFault, UserMistake
from .limits import call_on_stack, memory_fault
from .parser import parse
from .paths import cast_hint, resolve_cast
from .values import Ability, Env, to_text, truthy
from .vertical import from_vertical
from .vocabulary import BLAME_WORD


class _Return(Exception):
    def __init__(self, value: object):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class Interpreter:
    def __init__(self, stdout: IO[str] | None = None, stdin: IO[str] | None = None,
                 seed: int | None = None, base_dir: Path | str | None = None,
                 ascii_mode: bool = False, argv: list[str] | None = None,
                 persistent: bool = False, treewalk: bool | None = None):
        self.out = stdout if stdout is not None else sys.stdout
        self.inp = stdin if stdin is not None else sys.stdin
        self.rng = random.Random(seed)
        self.globals = Env()
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        self.ascii_mode = ascii_mode
        self.argv = list(argv or [])
        self.persistent = persistent
        self._include_stack: list[Path] = []
        self._stack: list[str] = []
        self._treewalk = bool(os.environ.get("PHYX_TREEWALK")) if treewalk is None else treewalk

    # ------------------------------------------------------------- I/O
    def write(self, text: str) -> None:
        self.out.write(text)

    def speak_values(self, values: list, line: int | None = None) -> None:
        try:
            self.out.write(" ".join(to_text(v) for v in values) + "\n")
        except RuntimeFault as err:
            if err.line is None and line:
                err.line = line
            raise

    def read_line(self, prompt: str = "") -> object:
        if prompt:
            self.out.write(prompt)
        try:
            self.out.flush()
        except Exception:  # pragma: no cover
            pass
        line = self.inp.readline()
        if line == "":
            return None
        return line.rstrip("\r\n")

    # ------------------------------------------------------------- entry
    def known_functions(self) -> dict[str, int]:
        """Ability name → arity, for the parser to treat later sentences as calls."""
        out: dict[str, int] = {}
        env: Env | None = self.globals
        while env is not None:
            for name, value in env.vars.items():
                if isinstance(value, Ability) and name not in out:
                    out[name] = len(value.params)
            env = env.parent
        return out

    def run(self, program: list[ast.Stmt]) -> None:
        call_on_stack(lambda: self._run_here(program))

    def _run_here(self, program: list[ast.Stmt]) -> None:
        if not self._treewalk:
            from .compiler import run_compiled
            persist = self.persistent or bool(self._include_stack)
            run_compiled(self, program, persist=persist)
            return
        self._run_tree(program)

    def _run_tree(self, program: list[ast.Stmt]) -> None:
        # abilities defined at the top level are known from the first sentence
        for stmt in program:
            if isinstance(stmt, ast.FuncDef):
                self.globals.vars[stmt.name] = Ability(stmt.name, stmt.params, stmt.body, self.globals)
        try:
            self.exec_block(program, self.globals)
        except _Return:
            raise RuntimeFault("'iţpənn (return) used outside of an ability")
        except _Break:
            raise RuntimeFault("lups (stop) used outside of a loop")
        except _Continue:
            raise RuntimeFault("ɢnagɮ (next) used outside of a loop")
        except RuntimeFault as err:
            # The overflow is raised on whichever call happened to be deepest.
            # A line would name that call and the compiled engine has none.
            if err.message == "the abilities called each other too deeply":
                err.line = None
            raise

    def load(self, name: str, line: int = 0) -> object:
        try:
            return self.globals.lookup(name)
        except RuntimeFault as err:
            if err.line is None:
                err.line = line
            raise

    def setv(self, name: str, value: object, line: int = 0, persist: bool = False) -> object:
        if name in self.globals.consts:
            raise RuntimeFault(f"'{name}' was fixed in the past ('u) and cannot change", line)
        vars_ = self.globals.vars
        if persist:
            vars_[name] = value
        elif name not in vars_:
            vars_[name] = value
        return value

    def fix(self, name: str, value: object, line: int = 0) -> object:
        try:
            self.globals.assign(name, value, const=True)
        except RuntimeFault as err:
            if err.line is None:
                err.line = line
            raise
        return value

    def gstore(self, name: str, value: object, const: bool = False, line: int = 0) -> object:
        try:
            self.globals.assign(name, value, const=const)
        except RuntimeFault as err:
            if err.line is None:
                err.line = line
            raise
        return value

    def export_ability(self, name: str, ability: Ability) -> None:
        self.globals.vars[name] = ability
        if ability.closure is None:
            ability.closure = self.globals

    def invoke(self, name: str, args: list, line: int = 0) -> object:
        ability = self.load(name, line)
        if not isinstance(ability, Ability):
            raise RuntimeFault(f"'{name}' is not an ability", line)
        try:
            return self.call(ability, args)
        except RuntimeFault as err:
            if err.line is None:
                err.line = line
            raise

    # ------------------------------------------------------------- statements
    def exec_block(self, stmts: list[ast.Stmt], env: Env) -> None:
        for stmt in stmts:
            self.exec_stmt(stmt, env)

    def exec_stmt(self, stmt: ast.Stmt, env: Env) -> None:
        try:
            self._exec(stmt, env)
        except MemoryError:
            raise memory_fault(stmt.line) from None
        except PhyrexianError as err:
            if err.line is None:
                err.line = stmt.line
            raise

    def _exec(self, stmt: ast.Stmt, env: Env) -> None:
        if isinstance(stmt, ast.ExprStmt):
            for e in stmt.exprs:
                self.eval(e, env)

        elif isinstance(stmt, ast.Print):
            values = [self.eval(e, env) for e in stmt.exprs]
            self.write(" ".join(to_text(v) for v in values) + "\n")

        elif isinstance(stmt, ast.Input):
            prompt = " ".join(to_text(self.eval(e, env)) for e in stmt.prompt)
            answer = self.read_line(prompt)
            self.store(stmt.target, answer, env)

        elif isinstance(stmt, ast.If):
            cond = truthy(self.eval(stmt.cond, env))
            if stmt.negate:
                cond = not cond
            if cond:
                self.exec_block(stmt.body, env)
            elif stmt.orelse is not None:
                self.exec_block(stmt.orelse, env)

        elif isinstance(stmt, ast.While):
            while truthy(self.eval(stmt.cond, env)):
                try:
                    self.exec_block(stmt.body, env)
                except _Break:
                    break
                except _Continue:
                    continue

        elif isinstance(stmt, ast.For):
            coll = self.eval(stmt.iterable, env)
            if isinstance(coll, dict):
                items = list(coll.keys())
            elif isinstance(coll, (list, str)):
                items = list(coll)
            else:
                raise RuntimeFault(f"aχəw' (each) cannot walk through {to_text(coll)}", stmt.line)
            for item in items:
                env.assign(stmt.var, item)
                try:
                    self.exec_block(stmt.body, env)
                except _Break:
                    break
                except _Continue:
                    continue

        elif isinstance(stmt, ast.FuncDef):
            env.vars[stmt.name] = Ability(stmt.name, stmt.params, stmt.body, env)

        elif isinstance(stmt, ast.Assert):
            if not truthy(self.eval(stmt.cond, env)):
                msg = "ǩaπa (must) was not satisfied"
                if stmt.message is not None:
                    msg += ": " + to_text(self.eval(stmt.message, env))
                raise RuntimeFault(msg, stmt.line)

        elif isinstance(stmt, ast.Try):
            try:
                self.exec_block(stmt.body, env)
            except RuntimeFault as err:
                if stmt.handler is None:
                    return
                # The handler shares this scope. dekp stays bound afterwards.
                blame = err.value if isinstance(err, UserMistake) else err.message
                try:
                    env.assign(BLAME_WORD, blame)
                except RuntimeFault as fault:
                    if fault.line is None:
                        fault.line = stmt.line
                    raise
                self.exec_block(stmt.handler, env)

        else:  # pragma: no cover
            raise RuntimeFault(f"unknown sentence {type(stmt).__name__}", stmt.line)

    # ------------------------------------------------------------- expressions
    def eval(self, expr: ast.Expr, env: Env) -> object:
        try:
            return self._eval(expr, env)
        except PhyrexianError as err:
            if err.line is None:
                err.line = expr.line
            raise
        except RecursionError:
            raise RuntimeFault("the abilities called each other too deeply", expr.line) from None

    def _eval(self, expr: ast.Expr, env: Env) -> object:
        if isinstance(expr, ast.Literal):
            return expr.value

        if isinstance(expr, ast.Name):
            return env.lookup(expr.name)

        if isinstance(expr, ast.Call):
            args = [self.eval(a, env) for a in expr.args]
            impl = IMPLS.get(expr.verb.word)
            if impl is None:  # pragma: no cover - every verb has an implementation
                raise RuntimeFault(f"the verb '{expr.verb.word}' has no implementation", expr.line)
            return impl(self, args)

        if isinstance(expr, ast.UserCall):
            ability = env.lookup(expr.name)
            if not isinstance(ability, Ability):
                raise RuntimeFault(f"'{expr.name}' is not an ability", expr.line)
            args = [self.eval(a, env) for a in expr.args]
            return self.call(ability, args)

        if isinstance(expr, ast.Assign):
            value = self.eval(expr.value, env)
            self.store(expr.target, value, env, const=expr.const)
            return value

        if isinstance(expr, ast.Return):
            raise _Return(None if expr.value is None else self.eval(expr.value, env))

        if isinstance(expr, ast.Break):
            raise _Break()

        if isinstance(expr, ast.Continue):
            raise _Continue()

        raise RuntimeFault(f"unknown expression {type(expr).__name__}", expr.line)  # pragma: no cover

    def call(self, ability: Ability, args: list[object]) -> object:
        if len(args) != len(ability.params):  # pragma: no cover - parser enforces arity
            raise RuntimeFault(f"'{ability.name}' wants {len(ability.params)} objects, got {len(args)}")
        self._stack.append(ability.name)
        try:
            if ability.impl is not None:
                try:
                    return ability.impl(self, *args)
                except RecursionError:
                    raise RuntimeFault("the abilities called each other too deeply") from None
                except _Break:
                    raise RuntimeFault(f"lups (stop) used outside of a loop in '{ability.name}'")
                except _Continue:
                    raise RuntimeFault(f"ɢnagɮ (next) used outside of a loop in '{ability.name}'")
            local = Env(parent=ability.closure)
            for name, value in zip(ability.params, args):
                local.vars[name] = value
            try:
                self.exec_block(ability.body, local)
            except _Return as ret:
                return ret.value
            except _Break:
                raise RuntimeFault(f"lups (stop) used outside of a loop in '{ability.name}'")
            except _Continue:
                raise RuntimeFault(f"ɢnagɮ (next) used outside of a loop in '{ability.name}'")
            return None
        except RuntimeFault as err:
            if ability.impl is None and not err.frames:
                err.frames = list(self._stack)
            raise
        finally:
            self._stack.pop()

    def store(self, target: ast.Expr, value: object, env: Env, const: bool = False) -> None:
        if isinstance(target, ast.Name):
            env.assign(target.name, value, const=const)
            return
        if isinstance(target, ast.Call):  # tapq place
            coll = self.eval(target.args[0], env)
            key = self.eval(target.args[1], env)
            put_into(coll, key, value)
            return
        raise RuntimeFault("cannot put a value there", target.line)  # pragma: no cover

    def include(self, path_str: str) -> None:
        """``bukð`` — play/cast another φyrx text into this session."""
        path = resolve_cast(path_str, self.base_dir)
        if path is None:
            raise RuntimeFault(
                f"bukð (play/cast): no such text '{path_str}'",
                hint=cast_hint(path_str, self.base_dir),
            )
        if path in self._include_stack:
            raise RuntimeFault(f"bukð (play/cast): '{path_str}' is already being cast (cycle)")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as err:
            raise RuntimeFault(f"bukð (play/cast) cannot read '{path_str}': {err}") from err
        if path.suffix.lower() == ".vphyx":
            text = from_vertical(text)
        self._include_stack.append(path)
        previous = self.base_dir
        self.base_dir = path.parent
        try:
            program = parse(
                text,
                known_functions=self.known_functions(),
                base_dir=path.parent,
                ascii_mode=self.ascii_mode,
            )
            self.run(program)
        except PhyrexianError as err:
            if err.source is None:
                err.source = text
                err.filename = path.name
            raise
        finally:
            self.base_dir = previous
            self._include_stack.pop()


def run_source(source: str, ascii_mode: bool = False, **kwargs) -> Interpreter:
    """Parse and run ``source``; returns the interpreter (useful for tests)."""
    program = parse(
        source,
        ascii_mode=ascii_mode,
        base_dir=kwargs.get("base_dir"),
    )
    interp = Interpreter(ascii_mode=ascii_mode, **kwargs)
    interp.run(program)
    return interp
