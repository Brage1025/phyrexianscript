"""Short calls of abilities brought in with bukð."""

import io
import tempfile
import unittest
from pathlib import Path

from phyx.cli import main
from phyx.errors import ParseError
from phyx.lint import lint_program
from phyx.lsp import diagnostics_for
from phyx.parser import parse
from phyx.vertical import to_vertical

ROOT = Path(__file__).resolve().parents[1]
SHORT = "ability 'addtwo' wants 2 objects but got 1 — quote it with naķm if you wanted the ability as a value"
ONE = "ability 'addtwo' wants 1 object but got 0 — quote it with naķm if you wanted the ability as a value"
ADD = "^ťe-a-b-addtwo:\n    ^lo-a-b-babg-'iţpənn.\n"


def _lint(source: str, folder: Path):
    brought: dict[str, int] = {}
    program = parse(source, base_dir=folder, imported=brought)
    return brought, lint_program(program, imported=brought)


class ImportedLintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name: str, text: str) -> Path:
        path = self.folder / name
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def _run(self, *argv):
        import contextlib

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_short_call_of_an_imported_ability_is_a_note(self):
        self._write("add.phyx", ADD)
        source = '^lo-"add.phyx"-bukð.\n!1-addtwo.\n'
        brought, notes = _lint(source, self.folder)
        self.assertEqual(brought, {"addtwo": 2})
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].line, 2)
        self.assertEqual(notes[0].message, SHORT)

    def test_full_call_is_silent(self):
        self._write("add.phyx", ADD)
        source = '^lo-"add.phyx"-bukð.\n!1-2-addtwo.\n'
        _brought, notes = _lint(source, self.folder)
        self.assertEqual(notes, [])

    def test_quoted_ability_is_silent(self):
        self._write("add.phyx", ADD)
        source = "^lo-\"add.phyx\"-bukð.\n^xe-addtwo-naķm-fn-ţə''.\n"
        _brought, notes = _lint(source, self.folder)
        self.assertEqual(notes, [])

    def test_activated_ability_is_silent(self):
        self._write("add.phyx", ADD)
        source = '^lo-"add.phyx"-bukð.\n!1-2-2-ťewn-addtwo-čtəčpliɣn.\n'
        _brought, notes = _lint(source, self.folder)
        self.assertEqual(notes, [])

    def test_zero_parameter_ability_is_silent(self):
        self._write("greet.phyx", '^ťe-greet:\n    !"šdeχd".\n')
        source = '^lo-"greet.phyx"-bukð.\n!greet.\n'
        brought, notes = _lint(source, self.folder)
        self.assertEqual(brought, {"greet": 0})
        self.assertEqual(notes, [])

    def test_local_te_wins_over_the_cast_arity(self):
        self._write("add.phyx", ADD)
        source = '^lo-"add.phyx"-bukð.\n^ťe-x-addtwo:\n    ^lo-x-\'iţpənn.\n!addtwo.\n'
        brought, notes = _lint(source, self.folder)
        self.assertEqual(brought, {"addtwo": 2})
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].line, 4)
        self.assertEqual(notes[0].message, ONE)
        full = '^lo-"add.phyx"-bukð.\n^ťe-x-addtwo:\n    ^lo-x-\'iţpənn.\n!1-addtwo.\n'
        _brought, notes = _lint(full, self.folder)
        self.assertEqual(notes, [])

    def test_ability_imported_through_another_cast_is_a_note(self):
        self._write("c.phyx", ADD)
        self._write("b.phyx", '^lo-"c.phyx"-bukð.\n')
        source = '^lo-"b.phyx"-bukð.\n!1-addtwo.\n'
        brought, notes = _lint(source, self.folder)
        self.assertEqual(brought, {"addtwo": 2})
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].line, 2)
        self.assertEqual(notes[0].message, SHORT)

    def test_vphyx_cast_file_is_a_note(self):
        self._write("add.vphyx", to_vertical(ADD))
        source = '^lo-"add.vphyx"-bukð.\n!1-addtwo.\n'
        brought, notes = _lint(source, self.folder)
        self.assertEqual(brought, {"addtwo": 2})
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].line, 2)
        self.assertEqual(notes[0].message, SHORT)

    def test_missing_cast_file_is_silent(self):
        path = self._write("main.phyx", '^lo-"missing.phyx"-bukð.\n!1-addtwo.\n')
        brought, notes = _lint(path.read_text(encoding="utf-8"), self.folder)
        self.assertEqual(brought, {})
        self.assertEqual(notes, [])
        code, out, err = self._run("lint", str(path))
        self.assertEqual(code, 0, err)
        self.assertIn("no notes", out)
        self.assertNotIn("Traceback", err)

    def test_unreadable_cast_file_is_silent(self):
        (self.folder / "bad.phyx").write_bytes(b"\xff")
        path = self._write("main.phyx", '^lo-"bad.phyx"-bukð.\n!1-addtwo.\n')
        brought, notes = _lint(path.read_text(encoding="utf-8"), self.folder)
        self.assertEqual(brought, {})
        self.assertEqual(notes, [])
        code, out, err = self._run("lint", str(path))
        self.assertEqual(code, 0, err)
        self.assertIn("no notes", out)
        self.assertNotIn("Traceback", err)

    def test_cast_cycle_stays_a_parse_error(self):
        self._write("a.phyx", '^lo-"b.phyx"-bukð.\n')
        self._write("b.phyx", '^lo-"a.phyx"-bukð.\n')
        source = '^lo-"a.phyx"-bukð.\n'
        found = {"stale": 1}
        with self.assertRaises(ParseError) as caught:
            parse(source, base_dir=self.folder, imported=found)
        self.assertIn("already being cast", str(caught.exception))
        self.assertEqual(found, {"stale": 1})
        path = self._write("main.phyx", source)
        code, out, err = self._run("lint", str(path))
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("already being cast", err)
        self.assertNotIn("Traceback", err)

    def test_omitted_imported_keyword_ignores_cast_abilities(self):
        self._write("add.phyx", ADD)
        source = '^lo-"add.phyx"-bukð.\n!1-addtwo.\n'
        program = parse(source, base_dir=self.folder)
        self.assertEqual(lint_program(program), [])

    def test_diagnostics_for_notes_an_imported_short_call(self):
        self._write("add.phyx", ADD)
        source = '^lo-"add.phyx"-bukð.\n!1-addtwo.\n'
        diagnostics = diagnostics_for(source, base_dir=self.folder)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["message"], SHORT)
        self.assertEqual(diagnostics[0]["severity"], 2)
        self.assertEqual(diagnostics[0]["range"]["start"]["line"], 1)

    def test_cli_exit_matches_a_local_short_call(self):
        self._write("add.phyx", ADD)
        imported = self._write("use.phyx", '^lo-"add.phyx"-bukð.\n!1-addtwo.\n')
        local = self._write("local.phyx", ADD + "!1-addtwo.\n")
        local_code, local_out, local_err = self._run("lint", str(local))
        code, out, err = self._run("lint", str(imported))
        self.assertEqual(local_err, "")
        self.assertEqual(err, "")
        self.assertEqual(local_code, 1)
        self.assertEqual(code, local_code)
        self.assertIn(SHORT, local_out)
        self.assertIn(SHORT, out)
        self.assertIn("line 2:", out)


class ShippedLintTests(unittest.TestCase):
    def _run(self, *argv):
        import contextlib

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_examples_and_lib_gain_no_notes(self):
        suffixes = {".phyx", ".vphyx"}
        seen = 0
        for folder in (ROOT / "examples", ROOT / "phyx" / "lib"):
            for path in sorted(p for p in folder.iterdir() if p.suffix.lower() in suffixes):
                seen += 1
                argv = ["lint", str(path)]
                # examples/07_ascii.phyx is ASCII capitals; lint reads it with --ascii.
                if path.name == "07_ascii.phyx":
                    argv = ["lint", "--ascii", str(path)]
                code, out, err = self._run(*argv)
                self.assertEqual(err, "", path)
                self.assertEqual(code, 0, out)
                self.assertIn("no notes", out)
        self.assertGreater(seen, 0)
