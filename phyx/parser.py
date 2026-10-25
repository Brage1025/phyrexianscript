"""Parser: tokens → syntax tree.

Grammar (informal)::

    program   := sentence*
    sentence  := START marker? phrase ('.' | ':' body)
    body      := inline-sentence            -- rest of the same line
               | INDENT sentence+ DEDENT    -- following, deeper-indented lines
    phrase    := clause (',' clause)*
    clause    := word ('-' word)*

A *phrase* is evaluated in Phyrexian word order: objects first, the verb last
(SOV).  Each verb has a known number of objects, so a clause such as
``a-b-babg-c-tøwp`` is resolved at parse time into ``(a + b) × c``.
"""

from __future__ import annotations

from pathlib import Path

from . import ast
from .conjugation import lemma_of
from .errors import ParseError, nesting_fault
from .hints import ENGLISH_MARKERS
from .lexer import Token, tokenize, transliterate
from .paths import resolve_cast
from .vertical import from_vertical
from .vocabulary import (
    BREAK_WORD,
    CAST_WORD,
    CONSTANTS,
    CONTINUE_WORD,
    GET_WORD,
    IN_WORD,
    MARKERS,
    PUT_WORD,
    QUOTE_WORD,
    RESERVED,
    RETURN_WORD,
    VERBS,
)


class Parser:
    def __init__(
        self,
        tokens: list[Token],
        known_functions: dict[str, int] | None = None,
        base_dir: Path | str | None = None,
        ascii_mode: bool = False,
        _ingesting: set[Path] | None = None,
    ):
        self.toks = tokens
        self.pos = 0
        self.functions: dict[str, int] = dict(known_functions or {})  # ability name → arity
        self._defined_here: set[str] = set()
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        self.ascii_mode = ascii_mode
        self._ingesting: set[Path] = _ingesting if _ingesting is not None else set()

    # ------------------------------------------------------------ helpers
    def peek(self, offset: int = 0) -> Token:
        return self.toks[min(self.pos + offset, len(self.toks) - 1)]

    def advance(self) -> Token:
        tok = self.toks[self.pos]
        if tok.kind != "EOF":
            self.pos += 1
        return tok

    def expect(self, kind: str, what: str) -> Token:
        tok = self.peek()
        if tok.kind != kind:
            raise ParseError(f"expected {what}, found {self._describe(tok)}", tok.line, tok.col)
        return self.advance()

    def skip_seps(self) -> None:
        while self.peek().kind == "SEP":
            self.advance()

    def _next_word(self) -> str | None:
        i = 0
        while True:
            tok = self.peek(i)
            if tok.kind == "SEP":
                i += 1
                continue
            if tok.kind == "WORD":
                return tok.value
            return None

    @staticmethod
    def _describe(tok: Token) -> str:
        if tok.kind == "EOF":
            return "the end of the text"
        if tok.kind in ("WORD", "START", "END", "COLON", "SEP", "COMMA"):
            return f"'{tok.value}'"
        if tok.kind == "STRING":
            return "a quoted sentence"
        return f"the numeral {tok.value:x}"

    # ------------------------------------------------------------ prescan
    def prescan_includes(self) -> None:
        """Load ability arities from files named by ``bukð`` so they may be
        called as verbs in this text (execution still happens at runtime)."""
        for i, tok in enumerate(self.toks):
            if tok.kind != "WORD" or tok.value != CAST_WORD:
                continue
            j = i - 1
            while j >= 0 and self.toks[j].kind == "SEP":
                j -= 1
            if j < 0 or self.toks[j].kind != "STRING":
                continue
            self._ingest_module(self.toks[j].value, tok)

    def _ingest_module(self, path_str: str, at: Token) -> None:
        path = resolve_cast(path_str, self.base_dir)
        if path is None:
            return
        if path in self._ingesting:
            raise ParseError(
                f"bukð (play/cast): '{path_str}' is already being cast (cycle)",
                at.line, at.col,
            )
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return
        if path.suffix.lower() == ".vphyx":
            text = from_vertical(text)
        if self.ascii_mode:
            text = transliterate(text)
        self._ingesting.add(path)
        inner = Parser(
            tokenize(text),
            known_functions=dict(self.functions),
            base_dir=path.parent,
            ascii_mode=self.ascii_mode,
            _ingesting=self._ingesting,
        )
        try:
            inner.prescan_includes()
            inner.prescan_abilities()
            for name, arity in inner.functions.items():
                self.functions[name] = arity
        finally:
            self._ingesting.discard(path)

    def prescan_abilities(self) -> None:
        """Register every ``ťe`` sentence so abilities may be used before (or
        recursively inside) their definition."""
        for i, tok in enumerate(self.toks):
            if tok.kind != "START" or tok.value != "^":
                continue
            nxt = self.toks[i + 1] if i + 1 < len(self.toks) else None
            if nxt is None or nxt.kind != "WORD" or nxt.value != "ťe":
                continue
            words: list[Token] = []
            j = i + 2
            while j < len(self.toks) and self.toks[j].kind in ("WORD", "SEP"):
                if self.toks[j].kind == "WORD":
                    words.append(self.toks[j])
                j += 1
            if not words:
                raise ParseError("ťe (can) needs the name of the ability", nxt.line, nxt.col)
            name = words[-1]
            if name.value in RESERVED or lemma_of(name.value) is not None:
                raise ParseError(f"'{name.value}' is a word of the language and cannot name an ability",
                                 name.line, name.col)
            if name.value in self._defined_here:
                raise ParseError(f"the ability '{name.value}' is defined twice", name.line, name.col)
            self._defined_here.add(name.value)
            self.functions[name.value] = len(words) - 1

    # ------------------------------------------------------------ program
    def parse_program(self) -> list[ast.Stmt]:
        self.prescan_includes()
        self.prescan_abilities()
        first = self.peek()
        if first.kind == "EOF":
            return []
        if first.kind != "START":
            raise ParseError(f"a sentence must begin with ^, ! or ?, found {self._describe(first)}",
                             first.line, first.col)
        if first.indent != 0:
            raise ParseError("the first sentence must not be indented", first.line, first.col)
        stmts = self.parse_block(0)
        tok = self.peek()
        if tok.kind != "EOF":
            raise ParseError(f"unexpected {self._describe(tok)}", tok.line, tok.col)
        self._reject_misplaced_control(stmts)
        return stmts

    def parse_block(self, indent: int) -> list[ast.Stmt]:
        stmts: list[ast.Stmt] = []
        while True:
            tok = self.peek()
            if tok.kind == "EOF":
                break
            if tok.kind != "START":
                raise ParseError(
                    f"a sentence must begin with ^, ! or ?, found {self._describe(tok)}"
                    " (is the previous sentence missing its final '.'?)",
                    tok.line, tok.col)
            if tok.indent < indent:
                break
            if tok.indent > indent:
                raise ParseError("this sentence is indented deeper than its neighbours", tok.line, tok.col)
            stmt = self.parse_sentence(self.advance())
            if isinstance(stmt, ast.Else):
                self._attach_else(stmts, stmt)
            else:
                stmts.append(stmt)
        return stmts

    def _attach_else(self, stmts: list[ast.Stmt], els: ast.Else) -> None:
        prev = stmts[-1] if stmts else None
        if isinstance(prev, ast.Try):
            if prev.handler is not None:
                raise ParseError("this baqilx (try) sentence already has its qit (instead)", els.line)
            prev.handler = els.body
            return
        if isinstance(prev, ast.If):
            tail = prev
            while tail.orelse and len(tail.orelse) == 1 and isinstance(tail.orelse[0], ast.If) \
                    and tail.orelse[0].chained:
                tail = tail.orelse[0]
            if tail.orelse is not None:
                raise ParseError("qit (instead) was already given for this ba (if) sentence", els.line)
            tail.orelse = els.body
            return
        raise ParseError("qit (instead) must follow a ba (if) or baqilx (try) sentence", els.line)

    # ------------------------------------------------------------ sentences
    def parse_sentence(self, start: Token | None) -> ast.Stmt:
        kind = start.value if start is not None else "^"
        line = start.line if start is not None else self.peek().line

        if kind == "!":
            exprs = self.parse_phrase()
            self.expect("END", "'.' to end the exclamation")
            return ast.Print(exprs, line=line)

        if kind == "?":
            exprs = self.parse_phrase()
            self.expect("END", "'.' to end the question")
            if not exprs:
                raise ParseError("a question needs the name that will hold the answer", line)
            target = exprs[-1]
            self._check_target(target, line)
            return ast.Input(exprs[:-1], target, line=line)

        # normal sentence: optional marker
        tok = self.peek()
        marker = "xe"
        if tok.kind == "WORD" and tok.value in MARKERS:
            marker = tok.value
            self.advance()
            self.skip_seps()
        elif tok.kind == "WORD" and tok.value.lower() in ENGLISH_MARKERS:
            phy = ENGLISH_MARKERS[tok.value.lower()]
            raise ParseError(
                f"'{tok.value}' is English, not Phyrexian. "
                f"The mood marker you want is '{phy}'. "
                f"Write ^{phy}-…  (python -m phyx explain {phy})",
                tok.line,
                tok.col,
                hint=f"python -m phyx explain {phy}",
            )
        stmt_kind = MARKERS[marker][0]
        handler = getattr(self, f"parse_{stmt_kind}")
        return handler(marker, line)

    # -- xe / lo -------------------------------------------------------------
    def parse_expr(self, marker: str, line: int) -> ast.Stmt:
        exprs = self.parse_phrase()
        self._end_or_error(marker)
        return ast.ExprStmt(exprs, line=line)

    # -- 'u -------------------------------------------------------------------
    def parse_const(self, marker: str, line: int) -> ast.Stmt:
        exprs = self.parse_phrase()
        self._end_or_error(marker)
        found = False
        for e in exprs:
            if isinstance(e, ast.Assign):
                if not isinstance(e.target, ast.Name):
                    raise ParseError("'u (past) can only fix a plain name as constant", line)
                e.const = True
                found = True
        if not found:
            raise ParseError("'u (past) expects an assignment (… name ţə'')", line)
        return ast.ExprStmt(exprs, line=line)

    # -- ba / bu / əx -----------------------------------------------------------
    def parse_if(self, marker: str, line: int) -> ast.Stmt:
        cond = self.parse_condition(marker)
        body = self.parse_body(line)
        return ast.If(cond, body, negate=False, line=line)

    def parse_unless(self, marker: str, line: int) -> ast.Stmt:
        cond = self.parse_condition(marker)
        body = self.parse_body(line)
        return ast.If(cond, body, negate=True, line=line)

    # -- qit --------------------------------------------------------------------
    def parse_else(self, marker: str, line: int) -> ast.Stmt:
        tok = self.peek()
        if tok.kind == "WORD" and tok.value in MARKERS and MARKERS[tok.value][0] in ("if", "unless"):
            sub_marker = self.advance().value
            self.skip_seps()
            cond = self.parse_condition(sub_marker)
            body = self.parse_body(line)
            nested = ast.If(cond, body, negate=MARKERS[sub_marker][0] == "unless",
                            chained=True, line=line)
            return ast.Else([nested], line=line)
        body = self.parse_body(line)
        return ast.Else(body, line=line)

    # -- baxuφ ------------------------------------------------------------------
    def parse_while(self, marker: str, line: int) -> ast.Stmt:
        cond = self.parse_condition(marker)
        body = self.parse_body(line)
        return ast.While(cond, body, line=line)

    # -- aχəw' ------------------------------------------------------------------
    def parse_for(self, marker: str, line: int) -> ast.Stmt:
        var = self.expect("WORD", "the name of each item")
        if var.value in RESERVED:
            raise ParseError(f"'{var.value}' is a word of the language and cannot name an item",
                             var.line, var.col)
        self.skip_seps()
        prep = self.expect("WORD", f"'{IN_WORD}' (in)")
        if prep.value != IN_WORD:
            raise ParseError(f"aχəw' (each) reads: aχəw'-ITEM-{IN_WORD}-COLLECTION; found '{prep.value}'",
                             prep.line, prep.col)
        iterable = self.parse_condition(marker, what="collection")
        body = self.parse_body(line)
        return ast.For(var.value, iterable, body, line=line)

    # -- ťe ---------------------------------------------------------------------
    def parse_def(self, marker: str, line: int) -> ast.Stmt:
        words: list[Token] = []
        while True:
            self.skip_seps()
            tok = self.peek()
            if tok.kind == "WORD":
                words.append(self.advance())
                continue
            break
        if not words:
            raise ParseError("ťe (can) needs the name of the ability", line)
        name = words[-1].value
        params = [w.value for w in words[:-1]]
        for w in words[:-1]:
            if w.value in RESERVED or w.value in self.functions:
                raise ParseError(f"'{w.value}' cannot be used as an object name", w.line, w.col)
        if len(set(params)) != len(params):
            raise ParseError(f"the ability '{name}' repeats an object name", line)
        if self.peek().kind != "COLON":
            tok = self.peek()
            raise ParseError(f"an ability definition needs ':' and a body, found {self._describe(tok)}",
                             tok.line, tok.col)
        body = self.parse_body(line)
        return ast.FuncDef(name, params, body, line=line)

    # -- ǩaπa -------------------------------------------------------------------
    def parse_assert(self, marker: str, line: int) -> ast.Stmt:
        exprs = self.parse_phrase()
        self._end_or_error(marker)
        if len(exprs) not in (1, 2):
            raise ParseError("ǩaπa (must) takes a condition and optionally a message", line)
        return ast.Assert(exprs[0], exprs[1] if len(exprs) == 2 else None, line=line)

    # -- baqilx -----------------------------------------------------------------
    def parse_try(self, marker: str, line: int) -> ast.Stmt:
        body = self.parse_body(line)
        return ast.Try(body, line=line)

    # ------------------------------------------------------------ pieces
    def parse_condition(self, marker: str, what: str = "condition") -> ast.Expr:
        exprs = self.parse_phrase()
        if len(exprs) != 1:
            tok = self.peek()
            raise ParseError(
                f"{marker} needs exactly one {what}, this phrase leaves {len(exprs)} values",
                tok.line, tok.col)
        return exprs[0]

    def _end_or_error(self, marker: str) -> None:
        tok = self.peek()
        if tok.kind == "COLON":
            hint = None
            if marker in ("xe", "lo"):
                hint = (
                    "to define an ability, the mood is ťe: ^ťe-n-name:  "
                    "(python -m phyx explain ťe). "
                    "If this file uses ASCII capitals (Te for ťe, TTE'' for ţə''), "
                    "run with --ascii"
                )
            raise ParseError(
                f"a '{marker}' sentence ends with '.', it does not take a body (':')",
                tok.line,
                tok.col,
                hint=hint,
            )
        self.expect("END", "'.' to end the sentence")

    def parse_body(self, header_line: int) -> list[ast.Stmt]:
        colon = self.expect("COLON", "':' followed by the body")
        nxt = self.peek()
        if nxt.kind == "EOF":
            raise ParseError("the text ends right after ':' — a body is missing", colon.line, colon.col)
        if nxt.line == colon.line:
            # inline body: "Next sentence does not need a start symbol."
            if nxt.kind == "START":
                return [self._single(self.parse_sentence(self.advance()))]
            return [self._single(self.parse_sentence(None))]
        if nxt.kind != "START":
            raise ParseError(f"a sentence must begin with ^, ! or ?, found {self._describe(nxt)}",
                             nxt.line, nxt.col)
        if nxt.indent <= colon.indent:
            raise ParseError("the body after ':' must be indented deeper than its header",
                             nxt.line, nxt.col)
        return self.parse_block(nxt.indent)

    @staticmethod
    def _single(stmt: ast.Stmt) -> ast.Stmt:
        if isinstance(stmt, ast.Else):
            raise ParseError("qit (instead) cannot be the inline body of another sentence", stmt.line)
        return stmt

    def _check_target(self, target: ast.Expr, line: int) -> None:
        if isinstance(target, ast.Name):
            return
        if isinstance(target, ast.Call) and target.verb.word == GET_WORD:
            return
        raise ParseError(f"the target of {PUT_WORD} (put) must be a name or a '{GET_WORD}' place", line)

    # ------------------------------------------------------------ phrases
    def parse_phrase(self) -> list[ast.Expr]:
        stack: list[ast.Expr] = []
        barrier = 0

        def pop(n: int, verb_word: str, gloss: str, tok: Token) -> list[ast.Expr]:
            available = len(stack) - barrier
            if available < n:
                raise ParseError(
                    f"the verb '{verb_word}' ({gloss}) wants {n} object{'s' if n != 1 else ''} "
                    f"before it, but only {available} {'is' if available == 1 else 'are'} there",
                    tok.line,
                    tok.col,
                    hint=(
                        f"write the objects first, then '{verb_word}' — "
                        f"e.g. 1-2-{verb_word}  (a comma before the verb fences objects off)"
                    ),
                )
            items = stack[len(stack) - n:]
            del stack[len(stack) - n:]
            return items

        while True:
            tok = self.peek()
            if tok.kind in ("END", "COLON", "EOF"):
                return stack
            if tok.kind == "SEP":
                self.advance()
                continue
            if tok.kind == "COMMA":
                self.advance()
                barrier = len(stack)
                continue
            if tok.kind == "START":
                raise ParseError(
                    f"a new sentence starts with '{tok.value}' before the previous one ended with '.'",
                    tok.line, tok.col)
            if tok.kind in ("NUMBER", "STRING"):
                stack.append(ast.Literal(tok.value, line=tok.line))
                self.advance()
                continue

            word = tok.value
            self.advance()

            if word in CONSTANTS:
                stack.append(ast.Literal(CONSTANTS[word], line=tok.line))
                continue

            lemma = lemma_of(word)
            if lemma is not None:
                verb = VERBS[lemma]
                if lemma == PUT_WORD:
                    value, target = pop(2, word, verb.gloss, tok)
                    self._check_target(target, tok.line)
                    stack.append(ast.Assign(target, value, line=tok.line))
                elif lemma == RETURN_WORD:
                    value = pop(1, word, verb.gloss, tok)[0] if len(stack) - barrier >= 1 else None
                    stack.append(ast.Return(value, line=tok.line))
                elif lemma == BREAK_WORD:
                    stack.append(ast.Break(line=tok.line))
                elif lemma == CONTINUE_WORD:
                    stack.append(ast.Continue(line=tok.line))
                elif verb.arity == -1:
                    count_expr = pop(1, word, verb.gloss, tok)[0]
                    if not isinstance(count_expr, ast.Literal) or not isinstance(count_expr.value, int) \
                            or isinstance(count_expr.value, bool) or count_expr.value < 0:
                        raise ParseError(
                            f"'{word}' ({verb.gloss}) must be preceded by a plain numeral giving "
                            "how many items to gather", tok.line, tok.col)
                    n = count_expr.value * (2 if lemma == "tekt" else 1)
                    available = len(stack) - barrier
                    if available < n:
                        count_hex = format(count_expr.value, "x")
                        if lemma == "tekt":
                            wanted = (
                                f"{count_expr.value} {'entry' if count_expr.value == 1 else 'entries'} "
                                f"(key and value each) before the count {count_hex}"
                            )
                        else:
                            wanted = (
                                f"{count_expr.value} item{'s' if count_expr.value != 1 else ''} "
                                f"before the count {count_hex}"
                            )
                        raise ParseError(
                            f"'{word}' ({verb.gloss}) wants {wanted}, "
                            f"but only {available} {'is' if available == 1 else 'are'} there. "
                            f"Write the items first, then the count, then {word} "
                            f"(empty: 0-{word})",
                            tok.line, tok.col)
                    items = pop(n, word, verb.gloss, tok)
                    stack.append(ast.Call(verb, items, line=tok.line))
                else:
                    args = pop(verb.arity, word, verb.gloss, tok)
                    stack.append(ast.Call(verb, args, line=tok.line))
                continue

            if word in self.functions:
                if self._next_word() == QUOTE_WORD:
                    # ``name-naķm`` — the work, not a call (needed for 0-arity ťe)
                    stack.append(ast.Name(word, line=tok.line))
                    continue
                arity = self.functions[word]
                available = len(stack) - barrier
                if available >= arity:
                    args = pop(arity, word, "ability", tok)
                    stack.append(ast.UserCall(word, args, line=tok.line))
                else:
                    # not enough objects: the ability is being used as a value
                    stack.append(ast.Name(word, line=tok.line))
                continue

            if word in MARKERS:
                raise ParseError(
                    f"'{word}' ({MARKERS[word][1].split(' — ')[0]}) is a mood marker and can only "
                    "begin a phrase", tok.line, tok.col)

            if word == "rukx":
                raise ParseError("rukx (note) starts a comment and must directly follow '^'",
                                 tok.line, tok.col)

            stack.append(ast.Name(word, line=tok.line))

    # ------------------------------------------------------- control words
    def _reject_misplaced_control(self, stmts: list[ast.Stmt]) -> None:
        """``'iţpənn`` needs an ability. ``lups`` and ``ɢnagɮ`` need a loop.

        The loop has to be written in the same ability. A caller that is
        itself in a loop does not make them legal: both engines already
        fault when the word leaves the ability. The walk uses its own
        stack so a deep phrase does not spend the host recursion budget.
        """
        pending: list[tuple] = [("block", stmts, False, False)]
        while pending:
            kind, node, in_ability, in_loop = pending.pop()
            if kind == "block":
                for stmt in reversed(node):
                    pending.append(("stmt", stmt, in_ability, in_loop))
                continue
            if kind == "exprs":
                for expr in reversed(node):
                    pending.append(("expr", expr, in_ability, in_loop))
                continue
            if kind == "stmt":
                self._queue_stmt(pending, node, in_ability, in_loop)
                continue
            self._queue_expr(pending, node, in_ability, in_loop)

    def _queue_stmt(self, pending: list[tuple], stmt: ast.Stmt, in_ability: bool, in_loop: bool) -> None:
        if isinstance(stmt, ast.FuncDef):
            pending.append(("block", stmt.body, True, False))
            return
        if isinstance(stmt, ast.While):
            pending.append(("block", stmt.body, in_ability, True))
            pending.append(("expr", stmt.cond, in_ability, in_loop))
            return
        if isinstance(stmt, ast.For):
            pending.append(("block", stmt.body, in_ability, True))
            pending.append(("expr", stmt.iterable, in_ability, in_loop))
            return
        if isinstance(stmt, ast.If):
            if stmt.orelse:
                pending.append(("block", stmt.orelse, in_ability, in_loop))
            pending.append(("block", stmt.body, in_ability, in_loop))
            pending.append(("expr", stmt.cond, in_ability, in_loop))
            return
        if isinstance(stmt, ast.Try):
            if stmt.handler:
                pending.append(("block", stmt.handler, in_ability, in_loop))
            pending.append(("block", stmt.body, in_ability, in_loop))
            return
        if isinstance(stmt, ast.ExprStmt):
            pending.append(("exprs", stmt.exprs, in_ability, in_loop))
            return
        if isinstance(stmt, ast.Print):
            pending.append(("exprs", stmt.exprs, in_ability, in_loop))
            return
        if isinstance(stmt, ast.Input):
            pending.append(("expr", stmt.target, in_ability, in_loop))
            pending.append(("exprs", stmt.prompt, in_ability, in_loop))
            return
        if isinstance(stmt, ast.Assert):
            if stmt.message is not None:
                pending.append(("expr", stmt.message, in_ability, in_loop))
            pending.append(("expr", stmt.cond, in_ability, in_loop))

    def _queue_expr(self, pending: list[tuple], expr: ast.Expr, in_ability: bool, in_loop: bool) -> None:
        if isinstance(expr, ast.Return):
            if not in_ability:
                raise ParseError(
                    "'iţpənn (return) used outside of an ability",
                    expr.line,
                    hint="'iţpənn returns from the ability that is running; write it inside ťe",
                )
            if expr.value is not None:
                pending.append(("expr", expr.value, in_ability, in_loop))
            return
        if isinstance(expr, ast.Break):
            if not in_loop:
                raise ParseError(
                    "lups (stop) used outside of a loop",
                    expr.line,
                    hint="lups leaves a baxuφ or aχəw'; write it inside that loop",
                )
            return
        if isinstance(expr, ast.Continue):
            if not in_loop:
                raise ParseError(
                    "ɢnagɮ (next) used outside of a loop",
                    expr.line,
                    hint="ɢnagɮ skips to the next turn of a baxuφ or aχəw'; write it inside that loop",
                )
            return
        if isinstance(expr, ast.Assign):
            pending.append(("expr", expr.target, in_ability, in_loop))
            pending.append(("expr", expr.value, in_ability, in_loop))
            return
        if isinstance(expr, (ast.Call, ast.UserCall)):
            pending.append(("exprs", expr.args, in_ability, in_loop))


def parse(
    source: str,
    ascii_mode: bool = False,
    known_functions: dict[str, int] | None = None,
    base_dir: Path | str | None = None,
) -> list[ast.Stmt]:
    try:
        return Parser(
            tokenize(source, ascii_mode=ascii_mode),
            known_functions=known_functions,
            base_dir=base_dir,
            ascii_mode=ascii_mode,
        ).parse_program()
    except RecursionError as err:
        raise nesting_fault(err) from None
