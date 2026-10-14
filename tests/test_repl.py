import io
import unittest

from phyx import ast
from phyx.interpreter import Interpreter
from phyx.parser import parse
from phyx.repl import Repl, is_complete


class CompletenessTests(unittest.TestCase):
    def test_single_sentence(self):
        self.assertTrue(is_complete("!x.\n"))
        self.assertTrue(is_complete("^xe-1-x-ţə''.\n"))
        self.assertFalse(is_complete("^xe-1-x-ţə''"))
        self.assertFalse(is_complete(""))

    def test_body_waits_for_blank_or_dedent(self):
        self.assertFalse(is_complete("^ťe-n-f:\n"))
        self.assertFalse(is_complete("^ťe-n-f:\n    !n.\n"))
        self.assertTrue(is_complete("^ťe-n-f:\n    !n.\n\n"))

    def test_comment_only_is_not_a_program(self):
        self.assertFalse(is_complete("^rukx a note\n"))


class SessionTests(unittest.TestCase):
    def _run(self, *lines: str, ascii_mode: bool = False) -> str:
        out = io.StringIO()
        Repl(stdin=io.StringIO(), stdout=out, ascii_mode=ascii_mode, intro=False).run(
            lines=list(lines)
        )
        return out.getvalue()

    def test_put_and_speak(self):
        out = self._run("^xe-5-x-ţə''.", "!x.")
        self.assertEqual(out, "5\n")

    def test_ability_survives_across_sentences(self):
        out = self._run(
            "^ťe-n-dub:",
            "    ^lo-n-ķus'ər-'iţpənn.",
            "",
            "!4-dub.",
        )
        self.assertEqual(out, "8\n")

    def test_grammar_error_does_not_kill_the_session(self):
        out = self._run("!1-babg.", "!ķu.")
        self.assertIn("ɬšeɴazv [grammar]", out)
        self.assertTrue(out.strip().endswith("2"))

    def test_commands(self):
        out = self._run(".words", ".names", ".ascii", ".help", ".nope", ".quit")
        self.assertIn("ţə''", out)
        self.assertIn("(none)", out)
        self.assertIn("ASCII spelling is on", out)
        self.assertIn("mood/tense marker", out)
        self.assertIn("unknown command", out)

    def test_ascii_sentence(self):
        out = self._run("^xe-0a-x-TTE''.", "!x.", ascii_mode=True)
        self.assertEqual(out, "0a\n")

    def test_names_after_binding(self):
        out = self._run("^xe-1-x-ţə''.", ".names")
        self.assertIn("x=1", out)

    def test_load_missing(self):
        out = self._run(".load")
        self.assertIn("needs a path", out)

    def test_load_file(self):
        from pathlib import Path

        lib = Path(__file__).resolve().parent.parent / "examples" / "lib_asərθ.phyx"
        out = self._run(f".load {lib}", "!əx4-abs.")
        self.assertTrue(out.strip().endswith("4"), out)


class KnownFunctionsTests(unittest.TestCase):
    def test_seeded_ability_is_a_call(self):
        (stmt,) = parse("!1-2-f.", known_functions={"f": 2})
        self.assertIsInstance(stmt.exprs[0], ast.UserCall)

    def test_redefine_seeded_ability(self):
        interp = Interpreter(stdout=io.StringIO())
        interp.run(parse("^ťe-f:\n    ^lo-1-'iţpənn."))
        interp.run(parse("^ťe-f:\n    ^lo-ķu-'iţpənn.", known_functions=interp.known_functions()))
        out = io.StringIO()
        interp.out = out
        interp.run(parse("!f.", known_functions=interp.known_functions()))
        self.assertEqual(out.getvalue(), "2\n")


if __name__ == "__main__":
    unittest.main()
