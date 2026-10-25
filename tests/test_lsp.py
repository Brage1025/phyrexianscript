import io
import tempfile
import unittest
from pathlib import Path

from phyx.lsp import (
    Server,
    abilities_in,
    completions_for,
    definition_at,
    hover_at,
    token_at,
)
from phyx.scaffold import create


class LspHelperTests(unittest.TestCase):
    def test_completions_include_lexicon_and_ability(self):
        src = (
            "^ťe-n-fib:\n"
            "    ^lo-n-'iţpənn.\n"
            "!5-fib.\n"
        )
        labels = {item["label"] for item in completions_for(src)}
        self.assertIn("ba", labels)
        self.assertIn("babg", labels)
        self.assertIn("əxbytp", labels)
        self.assertIn("fib", labels)

    def test_jump_to_te(self):
        src = (
            "^ťe-n-fib:\n"
            "    ^lo-n-'iţpənn.\n"
            "!5-fib.\n"
        )
        # Cursor on the call ``fib`` in ``!5-fib.``
        loc = definition_at(src, 2, 3)
        self.assertIsNotNone(loc)
        _path, line = loc
        self.assertEqual(line, 1)

    def test_hover_verb(self):
        src = "!1-2-babg.\n"
        text = hover_at(src, 0, 5)
        self.assertIsNotNone(text)
        self.assertIn("babg", text)
        self.assertIn("add", text)

    def test_token_at_word(self):
        tok = token_at("!1-2-babg.\n", 0, 5)
        self.assertIsNotNone(tok)
        self.assertEqual(tok.value, "babg")

    def test_ability_from_bukð(self):
        folder = Path(tempfile.mkdtemp())
        create("greet", directory=folder)
        test = (folder / "test_greet.phyx").read_text(encoding="utf-8")
        abilities = abilities_in(test, base_dir=folder, origin=folder / "test_greet.phyx")
        self.assertIn("greet", abilities)
        path, line = abilities["greet"]
        self.assertEqual(path, (folder / "greet.phyx").resolve())
        self.assertGreaterEqual(line, 1)


class LspProtocolTests(unittest.TestCase):
    def test_initialize_and_completion(self):
        server = Server()
        init = server.handle({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        self.assertIn("completionProvider", init["result"]["capabilities"])
        server.handle({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///tmp/x.phyx",
                    "text": "^ťe-n-fib:\n    ^lo-n-'iţpənn.\n!5-fib.\n",
                }
            },
        })
        reply = server.handle({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": "file:///tmp/x.phyx"},
                "position": {"line": 2, "character": 3},
            },
        })
        labels = {item["label"] for item in reply["result"]}
        self.assertIn("fib", labels)
        self.assertIn("ťe", labels)

    def test_content_length_roundtrip(self):
        from phyx.lsp import _read_message, _write_message

        payload = {"jsonrpc": "2.0", "id": 1, "method": "shutdown"}
        buf = io.BytesIO()
        _write_message(buf, payload)
        buf.seek(0)
        got = _read_message(buf)
        self.assertEqual(got["method"], "shutdown")
