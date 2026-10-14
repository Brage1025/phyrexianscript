"""Shipped herds, bukð search path, phyx test / phyx lib."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path

from phyx.cli import main
from phyx.errors import RuntimeFault
from phyx.interpreter import run_source
from phyx.paths import resolve_cast, resolve_note, resolve_spread, stdlib_dir
from phyx.testing import collect_tests, run_suite, run_test_file
from phyx.vocabulary import CONSTANTS, MARKERS, VERBS

ROOT = Path(__file__).resolve().parent.parent
EDITORS = ROOT / "editors"
PHYX_TESTS = ROOT / "tests" / "phyx"


def _run(*argv: str) -> tuple[int, str, str]:
    import contextlib

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class StdlibPathTests(unittest.TestCase):
    def test_shipped_herds_exist(self):
        folder = stdlib_dir()
        for name in ("asərθ.phyx", "ťewn.phyx", "compleat.phyx"):
            self.assertTrue((folder / name).is_file(), name)

    def test_suffixless_resolves_stdlib(self):
        found = resolve_cast("asərθ", tempfile.gettempdir())
        self.assertIsNotNone(found)
        self.assertEqual(found, (stdlib_dir() / "asərθ.phyx").resolve())

    def test_missing_is_none(self):
        self.assertIsNone(resolve_cast("no-such-herd.phyx", tempfile.gettempdir()))

    def test_phyx_path(self):
        with tempfile.TemporaryDirectory() as td:
            extra = Path(td) / "ping.phyx"
            extra.write_text("^ťe-ping:\n    ^lo-1-'iţpənn.\n", encoding="utf-8")
            previous = os.environ.get("PHYX_PATH")
            os.environ["PHYX_PATH"] = td
            try:
                found = resolve_cast("ping.phyx", tempfile.gettempdir())
                self.assertEqual(found, extra.resolve())
                out = io.StringIO()
                run_source(
                    '^lo-"ping.phyx"-bukð.\n!ping.',
                    stdout=out,
                    base_dir=tempfile.gettempdir(),
                )
                self.assertEqual(out.getvalue(), "1\n")
            finally:
                if previous is None:
                    os.environ.pop("PHYX_PATH", None)
                else:
                    os.environ["PHYX_PATH"] = previous

    def test_cast_stdlib_from_anywhere(self):
        out = io.StringIO()
        run_source(
            '^lo-"asərθ.phyx"-bukð.\n!əx0a-abs,30-12-ǩeznasərθ.',
            stdout=out,
            base_dir=tempfile.gettempdir(),
        )
        self.assertEqual(out.getvalue(), "0a 6\n")

    def test_missing_cast_names_search(self):
        with self.assertRaises(RuntimeFault) as ctx:
            run_source('^lo-"nope.phyx"-bukð.', base_dir=tempfile.gettempdir())
        self.assertIn("no such text", str(ctx.exception))
        self.assertIsNotNone(ctx.exception.hint)
        self.assertIn("phyx lib", ctx.exception.hint)

    def test_research_searches_phyx_path_not_stdlib(self):
        with tempfile.TemporaryDirectory() as td:
            notes = Path(td) / "notes"
            work = Path(td) / "work"
            notes.mkdir()
            work.mkdir()
            (notes / "secret.rukx").write_text("found", encoding="utf-8")
            previous = os.environ.get("PHYX_PATH")
            os.environ["PHYX_PATH"] = str(notes)
            try:
                self.assertEqual(
                    resolve_note("secret.rukx", work),
                    (notes / "secret.rukx").resolve(),
                )
                self.assertIsNone(resolve_note("asərθ.phyx", work))
                out = io.StringIO()
                run_source('!"secret.rukx"-brøtjt.', stdout=out, base_dir=work)
                self.assertEqual(out.getvalue(), "found\n")
                with self.assertRaises(RuntimeFault) as ctx:
                    run_source('!"asərθ.phyx"-brøtjt.', base_dir=work)
                self.assertIn("cannot read", str(ctx.exception))
                self.assertIsNotNone(ctx.exception.hint)
                self.assertNotIn(str(stdlib_dir()), ctx.exception.hint)
            finally:
                if previous is None:
                    os.environ.pop("PHYX_PATH", None)
                else:
                    os.environ["PHYX_PATH"] = previous

    def test_spread_stays_file_relative(self):
        with tempfile.TemporaryDirectory() as td:
            notes = Path(td) / "notes"
            work = Path(td) / "work"
            notes.mkdir()
            work.mkdir()
            (notes / "n.rukx").write_text("path-copy", encoding="utf-8")
            previous = os.environ.get("PHYX_PATH")
            os.environ["PHYX_PATH"] = str(notes)
            try:
                dest = resolve_spread("n.rukx", work)
                self.assertEqual(dest, work / "n.rukx")
                out = io.StringIO()
                run_source(
                    '^lo-"local"-"n.rukx"-mɴyrx.\n!"n.rukx"-brøtjt.',
                    stdout=out,
                    base_dir=work,
                )
                self.assertEqual(out.getvalue(), "local\n")
                self.assertEqual((work / "n.rukx").read_text(encoding="utf-8"), "local")
                self.assertEqual((notes / "n.rukx").read_text(encoding="utf-8"), "path-copy")
            finally:
                if previous is None:
                    os.environ.pop("PHYX_PATH", None)
                else:
                    os.environ["PHYX_PATH"] = previous


class CliLibTestTests(unittest.TestCase):
    def test_lib_lists_herds(self):
        code, out, err = _run("lib")
        self.assertEqual(code, 0, err)
        self.assertIn("asərθ.phyx", out)
        self.assertIn("abs/1", out)
        self.assertIn("ťewn.phyx", out)
        self.assertIn("sort/1", out)
        self.assertIn("compleat.phyx", out)
        self.assertIn("casts", out)

    def test_phyx_test_runs_language_tests(self):
        code, out, err = _run("test", str(PHYX_TESTS))
        self.assertEqual(code, 0, err + out)
        self.assertIn("passed", out)
        self.assertIn("0 failed", out)

    def test_collect_discovers_test_prefix(self):
        files = collect_tests([PHYX_TESTS])
        names = {p.name for p in files}
        self.assertIn("test_asərθ.phyx", names)
        self.assertIn("test_ťewn.phyx", names)
        self.assertIn("test_compleat.phyx", names)
        self.assertIn("test_conjugation.phyx", names)
        self.assertIn("test_core_ability.phyx", names)
        self.assertIn("test_core_loop.phyx", names)
        self.assertIn("test_core_list.phyx", names)
        self.assertIn("test_core_must.phyx", names)
        self.assertIn("test_speak.phyx", names)
        self.assertNotIn("test_speak.expected", names)

    def test_expected_sidecar_must_match_stdout(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test_out.phyx"
            path.write_text("!1-2-babg.\n", encoding="utf-8")
            sidecar = Path(td) / "test_out.expected"
            sidecar.write_text("3\n", encoding="utf-8")
            self.assertTrue(run_test_file(path).ok)
            sidecar.write_text("nope\n", encoding="utf-8")
            result = run_test_file(path)
            self.assertFalse(result.ok)
            self.assertIn("expected", result.detail)

    def test_false_must_fails_the_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test_no.phyx"
            path.write_text("^ǩaπa-bytp.\n", encoding="utf-8")
            result = run_test_file(path)
            self.assertFalse(result.ok)
            self.assertIn("ǩaπa", result.detail)


class CompleatExampleTests(unittest.TestCase):
    def test_sort_example_still_runs(self):
        code, out, err = _run("run", str(ROOT / "examples" / "12_sort.phyx"))
        self.assertEqual(code, 0, err)
        self.assertIn("sort", out)
        self.assertIn("filter odd", out)

    def test_compleat_example(self):
        code, out, err = _run("run", str(ROOT / "examples" / "14_compleat.phyx"))
        self.assertEqual(code, 0, err)
        self.assertIn("sort", out)

    def test_suite_helper_on_one_file(self):
        buf = io.StringIO()
        code = run_suite([PHYX_TESTS / "test_asərθ.phyx"], stdout=buf)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("ok", buf.getvalue())


class GrammarDriftTests(unittest.TestCase):
    def test_textmate_lists_the_lexicon(self):
        text = (EDITORS / "phyx.tmLanguage.json").read_text(encoding="utf-8")
        missing = [w for w in list(MARKERS) + list(VERBS) + list(CONSTANTS) if w not in text]
        self.assertEqual(missing, [], f"phyx.tmLanguage.json omits {missing}")

    def test_vim_syntax_lists_the_lexicon(self):
        text = (EDITORS / "syntax" / "phyx.vim").read_text(encoding="utf-8")
        missing = [w for w in list(MARKERS) + list(VERBS) + list(CONSTANTS) if w not in text]
        self.assertEqual(missing, [], f"syntax/phyx.vim omits {missing}")


if __name__ == "__main__":
    unittest.main()
