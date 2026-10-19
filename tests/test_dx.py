import ast
import io
import unittest

from phyx.compiler import compile_to_python
from phyx.errors import ParseError, RuntimeFault, format_error
from phyx.fmt import format_source
from phyx.hints import did_you_mean, explain_word, hint_for_unknown
from phyx.interpreter import run_source
from phyx.lint import lint_program
from phyx.parser import parse


class HintTests(unittest.TestCase):
    def test_english_maps_to_phyrexian(self):
        hint = hint_for_unknown("if")
        self.assertIn("ba", hint)
        self.assertIn("English", hint)

    def test_nearby_verb(self):
        self.assertIn("babg", did_you_mean("babb"))

    def test_explain_verb_and_english(self):
        text = explain_word("babg")
        self.assertIsNotNone(text)
        self.assertIn("add", text)
        mapped = explain_word("if")
        self.assertIn("ba", mapped)
        self.assertNotIn("babg", mapped)
        self.assertIn("English: if", mapped)

    def test_format_error_shows_hint(self):
        try:
            run_source("!y.")
        except RuntimeFault as err:
            shown = format_error(err, "!y.")
            self.assertIn("unknown word 'y'", shown)
            self.assertIn("hint:", shown)
        else:
            self.fail("expected RuntimeFault")


class EnglishMarkerTests(unittest.TestCase):
    def test_if_is_rejected_with_the_phyrexian_mood(self):
        with self.assertRaisesRegex(ParseError, "ba"):
            parse("^if-x:")

    def test_ascii_ability_without_flag_names_ascii(self):
        with self.assertRaises(ParseError) as ctx:
            parse("^Te-n-f:\n    !n.\n")
        self.assertIsNotNone(ctx.exception.hint)
        self.assertIn("--ascii", ctx.exception.hint)


class CompilerShapeTests(unittest.TestCase):
    def test_pure_fib_is_ordinary_python(self):
        src = (
            "^ťe-n-fib:\n"
            "    ^ba-n-ķu-grmɒɣg:lo-n-'iţpənn.\n"
            "    ^lo-n-'ii-mɒɣg-fib-n-ķu-mɒɣg-fib-babg-'iţpənn.\n"
            "!5-fib.\n"
        )
        py = compile_to_python(parse(src))
        self.assertIn("return", py)
        self.assertIn("__phyx_names", py)
        self.assertIn("+", py)
        self.assertIn("_a_fib", py)
        self.assertNotIn("while True:", py)

    def test_literal_sum_skips_the_type_test(self):
        py = compile_to_python(parse(
            "^ťe-f:\n"
            "    ^lo-1-2-babg-'iţpənn.\n"
            "!f.\n"
        ))
        self.assertIn("(1 + 2)", py)
        self.assertNotIn("_add", py)

    def test_name_keeps_the_type_test(self):
        py = compile_to_python(parse(
            "^ťe-n-f:\n"
            "    ^lo-n-1-babg-'iţpənn.\n"
            "!1-f.\n"
        ))
        self.assertIn("_add(", py)
        self.assertIn("type(", py)

    def test_int_only_results_skip_the_outer_type_test(self):
        py = compile_to_python(parse(
            "^ťe-n-f:\n"
            "    ^lo-n-1-mɒɣg-n-2-mɒɣg-babg-'iţpənn.\n"
            "!3-f.\n"
        ))
        self.assertIn("_sub(", py)
        self.assertNotIn("_add", py)

    def test_division_of_literals_keeps_the_zero_check(self):
        py = compile_to_python(parse(
            "^ťe-d:\n"
            "    ^lo-1-2-χɬkevk-'iţpənn.\n"
            "!d.\n"
        ))
        self.assertIn("_div(", py)
        self.assertNotIn("type(", py)

    def test_pure_not_uses_the_truthy_helper(self):
        py = compile_to_python(parse(
            "^ťe-n-f:\n"
            "    ^lo-n-əx-'iţpənn.\n"
            "!0-f.\n"
        ))
        self.assertIn("_not(", py)
        self.assertNotIn("not n", py)

    def test_loop_compiles_to_while_not_break_guard(self):
        src = (
            "^ťe-n-sum:\n"
            "    ^xe-0-s-ţə''.\n"
            "    ^xe-0-i-ţə''.\n"
            "    ^baxuφ-i-n-grmɒɣg:\n"
            "        ^xe-s-i-babg-s-ţə''.\n"
            "        ^xe-i-1-babg-i-ţə''.\n"
            "    ^lo-s-'iţpənn.\n"
            "!5-sum.\n"
        )
        py = compile_to_python(parse(src))
        self.assertIn("while (", py)
        self.assertNotIn("while True:", py)

    def test_equality_does_not_treat_truth_as_one(self):
        out = io.StringIO()
        run_source(
            "^ťe-eq:\n"
            "    ^lo-1-əxbytp-ǆ'ynpp-'iţpənn.\n"
            "!eq.\n",
            stdout=out,
        )
        self.assertEqual(out.getvalue().strip(), "bytp")

    def test_less_than_does_not_order_truth_as_a_number(self):
        with self.assertRaises(RuntimeFault):
            run_source(
                "^ťe-lt:\n"
                "    ^lo-0-əxbytp-grmɒɣg-'iţpənn.\n"
                "!lt.\n"
            )

    def test_still_runs(self):
        out = io.StringIO()
        run_source(
            "^ťe-n-fib:\n"
            "    ^ba-n-ķu-grmɒɣg:lo-n-'iţpənn.\n"
            "    ^lo-n-'ii-mɒɣg-fib-n-ķu-mɒɣg-fib-babg-'iţpənn.\n"
            "!8-fib.\n",
            stdout=out,
        )
        self.assertEqual(out.getvalue().strip(), "15")

    def test_compiled_blocks_are_never_empty(self):
        sources = [
            "^xe-1.\n",
            "^baqilx:\n    ^xe-fbx.\n!\"after\".\n",
            "^ba-bytp:\n    ^xe-1.\n",
            "^ťe-f:\n    ^xe-1.\n!f.\n",
        ]
        for source in sources:
            with self.subTest(source=source):
                tree = ast.parse(compile_to_python(parse(source)))
                for node in ast.walk(tree):
                    for body in _suites(node):
                        self.assertTrue(body, ast.dump(node))


def _suites(node: ast.AST) -> list[list[ast.stmt]]:
    """Suites the compiler emits. An absent else is an empty list and is fine."""
    bodies: list[list[ast.stmt]] = []
    body = getattr(node, "body", None)
    if isinstance(body, list) and type(node) is not ast.Module:
        bodies.append(body)
    handlers = getattr(node, "handlers", None)
    if isinstance(handlers, list):
        for handler in handlers:
            bodies.append(handler.body)
    return bodies


class FrameTests(unittest.TestCase):
    def test_ability_stack_is_named(self):
        src = (
            "^ťe-boom:\n"
            "    ^ǩaπa-bytp.\n"
            "^ťe-go:\n"
            "    ^lo-boom.\n"
            "^lo-go.\n"
        )
        try:
            run_source(src)
        except RuntimeFault as err:
            shown = format_error(err, src)
            self.assertIn("in abilities:", shown)
            self.assertIn("boom", shown)
            self.assertIn("go", shown)
        else:
            self.fail("expected RuntimeFault")

    def test_treewalk_frames(self):
        src = (
            "^ťe-boom:\n"
            "    ^ǩaπa-bytp.\n"
            "^lo-boom.\n"
        )
        try:
            run_source(src, treewalk=True)
        except RuntimeFault as err:
            self.assertIn("boom", err.frames)
        else:
            self.fail("expected RuntimeFault")

    def test_repeated_frames_collapse(self):
        err = RuntimeFault("too deeply", frames=["cnt"] * 1000)
        shown = format_error(err)
        self.assertIn("in abilities: cnt x1000", shown)
        self.assertNotIn("cnt → cnt", shown)

    def test_collapse_keeps_the_first_and_last_frames(self):
        err = RuntimeFault("broke", frames=["go", *["cnt"] * 1000, "boom"])
        shown = format_error(err)
        self.assertIn("in abilities: go → cnt x1000 → boom", shown)
        self.assertNotIn("cnt → cnt", shown)
        plain = format_error(RuntimeFault("broke", frames=["go", "boom"]))
        self.assertIn("in abilities: go → boom", plain)

    def test_recursive_fault_collapses_on_both_engines(self):
        src = "^ťe-cnt:\n    ^lo-cnt-'iţpənn.\n!cnt.\n"
        for flag in (False, True):
            with self.subTest(treewalk=flag):
                try:
                    run_source(src, treewalk=flag)
                except RuntimeFault as err:
                    shown = format_error(err, src)
                else:
                    self.fail("expected RuntimeFault")
                self.assertRegex(shown, r"in abilities: cnt x[0-9]+")
                self.assertNotIn("cnt → cnt", shown)


class FmtTests(unittest.TestCase):
    def test_canonical_hyphens_and_indent(self):
        src = "^xe - 1 - x - ţə''.\n^ba-x:\n  !x.\n"
        out = format_source(src)
        self.assertIn("^xe-1-x-ţə''.", out)
        self.assertIn("    !x.", out)

    def test_keeps_notes(self):
        src = "^rukx keep me\n!1.\n"
        self.assertIn("^rukx keep me", format_source(src))

    def test_roundtrip_runs(self):
        src = "^xe-1-2-babg-x-ţə''.\n!x.\n"
        out = io.StringIO()
        run_source(format_source(src), stdout=out)
        self.assertEqual(out.getvalue(), "3\n")


class LintTests(unittest.TestCase):
    def test_dropped_return(self):
        program = parse(
            "^ťe-n-odd:\n"
            "    ^lo-n-ķu-geft.\n"
        )
        notes = lint_program(program)
        self.assertTrue(any("'iţpənn" in n.message for n in notes))

    def test_procedure_is_silent(self):
        program = parse(
            "^ťe-greet:\n"
            '    !"šdeχd".\n'
        )
        self.assertEqual(lint_program(program), [])

    def test_fn_as_a_bound_name_is_fine(self):
        program = parse(
            "^ťe-greet:\n"
            '    !"šdeχd".\n'
            "^xe-greet-naķm-fn-ţə''.\n"
        )
        self.assertEqual(lint_program(program), [])

    def test_english_if_as_a_name_is_a_note(self):
        program = parse("^xe-1-if-ţə''.")
        self.assertTrue(any("'if' is English" in n.message for n in lint_program(program)))

    def test_unused_param(self):
        program = parse(
            "^ťe-a-b-f:\n"
            "    ^lo-a-'iţpənn.\n"
        )
        notes = lint_program(program)
        self.assertTrue(any("never uses object 'b'" in n.message for n in notes))


class CliDxTests(unittest.TestCase):
    def _run(self, *argv):
        import contextlib

        from phyx.cli import main

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_explain(self):
        code, out, err = self._run("explain", "babg", "if")
        self.assertEqual(code, 0, err)
        self.assertIn("babg", out)
        self.assertIn("ba", out)

    def test_fmt_stdout(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.phyx")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("^xe - 1 - x - ţə''.\n!x.\n")
            code, out, err = self._run("fmt", path)
        self.assertEqual(code, 0, err)
        self.assertIn("^xe-1-x-ţə''.", out)

    def test_lint_exit(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.phyx")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("^ťe-n-odd:\n    ^lo-n-ķu-geft.\n")
            code, out, err = self._run("lint", path)
        self.assertEqual(code, 1, err)
        self.assertIn("'iţpənn", out)


class ReplExplainTests(unittest.TestCase):
    def test_explain_command(self):
        from phyx.repl import Repl

        out = io.StringIO()
        Repl(stdin=io.StringIO(), stdout=out, intro=False).run(lines=[".explain add", ".quit"])
        self.assertIn("babg", out.getvalue())


if __name__ == "__main__":
    unittest.main()
