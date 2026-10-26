"""Language server for φyrx: complete the lexicon, jump to ``ťe``.

JSON-RPC 2.0 over stdin/stdout with ``Content-Length`` headers.
No third-party packages.  ``python -m phyx lsp``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from . import __version__, ast
from .errors import PhyrexianError
from .hints import explain_word
from .lexer import Token, tokenize
from .lint import lint_program
from .parser import parse
from .paths import resolve_cast
from .values import to_source
from .vocabulary import CAST_WORD, CONSTANTS, MARKERS, VERBS


def _uri_to_path(uri: str) -> Path | None:
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme and parsed.scheme != "file":
        return None
    path = url2pathname(unquote(parsed.path or uri))
    if parsed.netloc and sys.platform == "win32":
        path = f"//{parsed.netloc}{path}"
    return Path(path)


def _path_to_uri(path: Path) -> str:
    return path.resolve().as_uri()


def token_at(source: str, line: int, character: int, *, ascii_mode: bool = False) -> Token | None:
    """Token covering 0-based ``line`` / ``character``. ``None`` if the source will not lex."""
    try:
        toks = tokenize(source, ascii_mode=ascii_mode)
    except PhyrexianError:
        return None
    target_line = line + 1
    target_col = character + 1
    hit: Token | None = None
    for tok in toks:
        if tok.line != target_line or tok.kind == "EOF":
            continue
        text = tok.value if isinstance(tok.value, str) else (
            str(tok.value) if tok.value is not None else ""
        )
        start = tok.col
        end = tok.col + max(len(text), 1)
        inside = start <= target_col < end
        at_word_end = tok.kind == "WORD" and target_col == end
        if not (inside or at_word_end):
            continue
        if tok.kind == "WORD":
            return tok
        hit = tok
    return hit


def _walk_stmts(stmts: list[ast.Stmt]):
    for stmt in stmts:
        yield stmt
        for attr in ("body", "orelse", "handler"):
            inner = getattr(stmt, attr, None)
            if inner:
                yield from _walk_stmts(inner)


def _include_paths(source: str, base_dir: Path | None, *, ascii_mode: bool) -> list[Path]:
    try:
        toks = tokenize(source, ascii_mode=ascii_mode)
    except PhyrexianError:
        return []
    found: list[Path] = []
    for i, tok in enumerate(toks):
        if tok.kind != "WORD" or tok.value != CAST_WORD:
            continue
        j = i - 1
        while j >= 0 and toks[j].kind == "SEP":
            j -= 1
        if j < 0 or toks[j].kind != "STRING":
            continue
        path = resolve_cast(str(toks[j].value), base_dir)
        if path is not None:
            found.append(path)
    return found


def abilities_in(
    source: str,
    *,
    base_dir: Path | str | None = None,
    ascii_mode: bool = False,
    origin: Path | None = None,
    seen: set[Path] | None = None,
) -> dict[str, tuple[Path | None, int]]:
    """``ťe`` names → (file or None for the buffer, 1-based line)."""
    folder = Path(base_dir) if base_dir is not None else (origin.parent if origin else None)
    out: dict[str, tuple[Path | None, int]] = {}
    try:
        program = parse(source, ascii_mode=ascii_mode, base_dir=folder)
    except PhyrexianError:
        program = []
    for stmt in _walk_stmts(program):
        if isinstance(stmt, ast.FuncDef):
            out[stmt.name] = (origin, stmt.line)
    visited = seen if seen is not None else set()
    for path in _include_paths(source, folder, ascii_mode=ascii_mode):
        key = path.resolve()
        if key in visited:
            continue
        visited.add(key)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        nested = abilities_in(
            text,
            base_dir=path.parent,
            ascii_mode=ascii_mode,
            origin=path,
            seen=visited,
        )
        for name, loc in nested.items():
            out.setdefault(name, loc)
    return out


def completions_for(
    source: str,
    *,
    base_dir: Path | str | None = None,
    ascii_mode: bool = False,
    origin: Path | None = None,
) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()

    def add(label: str, kind: int, detail: str, doc: str = "") -> None:
        if label in seen:
            return
        seen.add(label)
        item = {"label": label, "kind": kind, "detail": detail}
        if doc:
            item["documentation"] = doc
        items.append(item)

    for w, (kind, gloss) in MARKERS.items():
        add(w, 14, f"mood / {kind}", gloss)
    for v in VERBS.values():
        add(v.word, 3, v.gloss, v.doc)
    for w, val in CONSTANTS.items():
        add(w, 21, "constant", to_source(val))
    for name, (_path, _line) in abilities_in(
        source, base_dir=base_dir, ascii_mode=ascii_mode, origin=origin
    ).items():
        add(name, 3, "ťe", "user ability")
    return items


def definition_at(
    source: str,
    line: int,
    character: int,
    *,
    base_dir: Path | str | None = None,
    ascii_mode: bool = False,
    origin: Path | None = None,
) -> tuple[Path | None, int] | None:
    """Location of the ``ťe`` the cursor is on, or ``None``."""
    tok = token_at(source, line, character, ascii_mode=ascii_mode)
    if tok is None or tok.kind != "WORD":
        return None
    name = str(tok.value)
    abilities = abilities_in(source, base_dir=base_dir, ascii_mode=ascii_mode, origin=origin)
    return abilities.get(name)


def hover_at(
    source: str,
    line: int,
    character: int,
    *,
    ascii_mode: bool = False,
) -> str | None:
    tok = token_at(source, line, character, ascii_mode=ascii_mode)
    if tok is None:
        return None
    if tok.kind == "WORD":
        return explain_word(str(tok.value))
    if tok.kind in ("START", "END", "COLON", "SEP", "COMMA") and isinstance(tok.value, str):
        return explain_word(tok.value)
    return None


def diagnostics_for(
    source: str,
    *,
    base_dir: Path | str | None = None,
    ascii_mode: bool = False,
) -> list[dict]:
    folder = Path(base_dir) if base_dir is not None else None
    try:
        program = parse(source, ascii_mode=ascii_mode, base_dir=folder)
    except PhyrexianError as err:
        line = (err.line or 1) - 1
        col = (err.col or 1) - 1
        if line < 0:
            line = 0
        if col < 0:
            col = 0
        msg = err.message
        if err.hint:
            msg = f"{msg} — {err.hint}"
        return [{
            "range": {
                "start": {"line": line, "character": col},
                "end": {"line": line, "character": col + 1},
            },
            "severity": 1,
            "source": "phyx",
            "message": msg,
        }]
    out: list[dict] = []
    for note in lint_program(program):
        line = max((note.line or 1) - 1, 0)
        out.append({
            "range": {
                "start": {"line": line, "character": 0},
                "end": {"line": line, "character": 1},
            },
            "severity": 2,
            "source": "phyx",
            "message": note.message,
        })
    return out


def _read_message(inp) -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = inp.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        try:
            text = line.decode("ascii")
        except UnicodeDecodeError:
            continue
        if ":" in text:
            key, value = text.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = inp.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(out, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    out.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii"))
    out.write(raw)
    out.flush()


class Server:
    def __init__(self) -> None:
        self.docs: dict[str, str] = {}

    def _doc(self, uri: str) -> tuple[str, Path | None]:
        text = self.docs.get(uri, "")
        path = _uri_to_path(uri)
        return text, path

    def handle(self, msg: dict) -> dict | None:
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "completionProvider": {"triggerCharacters": ["-"]},
                        "definitionProvider": True,
                        "hoverProvider": True,
                    },
                    "serverInfo": {"name": "phyx", "version": __version__},
                },
            }
        if method == "shutdown":
            return {"jsonrpc": "2.0", "id": req_id, "result": None}
        if method in ("initialized", "exit", "textDocument/didClose"):
            return None
        if method == "textDocument/didOpen":
            doc = params.get("textDocument") or {}
            uri = doc.get("uri")
            if uri:
                self.docs[uri] = doc.get("text") or ""
            return None
        if method == "textDocument/didChange":
            doc = params.get("textDocument") or {}
            uri = doc.get("uri")
            changes = params.get("contentChanges") or []
            if uri and changes:
                last = changes[-1]
                if "text" in last:
                    self.docs[uri] = last["text"]
            return None
        if method == "textDocument/completion":
            uri = (params.get("textDocument") or {}).get("uri", "")
            pos = params.get("position") or {}
            text, path = self._doc(uri)
            _ = pos
            items = completions_for(
                text,
                base_dir=path.parent if path else None,
                origin=path,
            )
            return {"jsonrpc": "2.0", "id": req_id, "result": items}
        if method == "textDocument/definition":
            uri = (params.get("textDocument") or {}).get("uri", "")
            pos = params.get("position") or {}
            text, path = self._doc(uri)
            loc = definition_at(
                text,
                int(pos.get("line", 0)),
                int(pos.get("character", 0)),
                base_dir=path.parent if path else None,
                origin=path,
            )
            if loc is None:
                return {"jsonrpc": "2.0", "id": req_id, "result": None}
            dest, line = loc
            target = dest if dest is not None else path
            if target is None:
                target_uri = uri
            else:
                target_uri = _path_to_uri(target)
            line0 = max(line - 1, 0)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "uri": target_uri,
                    "range": {
                        "start": {"line": line0, "character": 0},
                        "end": {"line": line0, "character": 1},
                    },
                },
            }
        if method == "textDocument/hover":
            uri = (params.get("textDocument") or {}).get("uri", "")
            pos = params.get("position") or {}
            text, _path = self._doc(uri)
            shown = hover_at(
                text,
                int(pos.get("line", 0)),
                int(pos.get("character", 0)),
            )
            if not shown:
                return {"jsonrpc": "2.0", "id": req_id, "result": None}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": {"kind": "plaintext", "value": shown}},
            }
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            }
        return None

    def serve(self, inp=None, out=None) -> int:
        inp = inp if inp is not None else sys.stdin.buffer
        out = out if out is not None else sys.stdout.buffer
        while True:
            try:
                msg = _read_message(inp)
            except (OSError, json.JSONDecodeError, ValueError):
                break
            if msg is None:
                break
            if msg.get("method") == "exit":
                return 0
            reply = self.handle(msg)
            if reply is not None:
                _write_message(out, reply)
            if msg.get("method") == "shutdown":
                continue
        return 0


def serve() -> int:
    return Server().serve()
