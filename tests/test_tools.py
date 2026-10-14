import io
import unittest
from pathlib import Path

from phyx.cli import main
from phyx.render import render_html
from phyx.vertical import from_vertical, to_vertical

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class VerticalTests(unittest.TestCase):
    def test_roundtrip_all_examples(self):
        for path in sorted(EXAMPLES.glob("*.phyx")):
            src = path.read_text(encoding="utf-8")
            expected = "\n".join(ln.rstrip() for ln in src.rstrip("\n").split("\n")) + "\n"
            with self.subTest(path.name):
                self.assertEqual(from_vertical(to_vertical(src)), expected)

    def test_layout_shape(self):
        vert = to_vertical("^ab.\n  !c.\n")
        # indentation becomes a vertical offset: the second column starts lower
        self.assertEqual(vert, "^\na\nb !\n. c\n  .\n")

    def test_gap(self):
        vert = to_vertical("ab\ncd\n", gap=3)
        self.assertEqual(vert, "a   c\nb   d\n")
        self.assertEqual(from_vertical(vert, gap=3), "ab\ncd\n")

    def test_misaligned_character(self):
        with self.assertRaises(ValueError):
            from_vertical("ab\n")


class RenderTests(unittest.TestCase):
    def test_columns_and_indent(self):
        page = render_html("^ba-x:\n    !x.\n\n^rukx note\n", title="t")
        self.assertIn('class="col" style="--indent:0"', page)
        self.assertIn('class="col" style="--indent:1"', page)
        self.assertIn('class="col blank"', page)
        self.assertIn('class="col note"', page)
        self.assertIn("writing-mode: vertical-lr", page)
        self.assertIn('font-family: "Phyrexian"', page)
        self.assertIn('local("Phyrexian")', page)
        self.assertIn("font-display: block", page)

    def test_non_font_file_is_not_embedded(self):
        import tempfile

        fake = Path(tempfile.mkdtemp()) / "Phyrexian-Regular.ttf"
        fake.write_text("<html>not a font</html>", encoding="utf-8")
        from phyx.render import font_source

        src = font_source(fake)
        self.assertNotIn("data:font", src)
        self.assertIn("local(\"Phyrexian\")", src)

    def test_official_font_embeds_when_present(self):
        from phyx.fonts import is_font_file, local_font

        font = local_font()
        if not is_font_file(font):
            self.skipTest("Phyrexian Regular not fetched yet")
        page = render_html("!φyrx.", local_font=font)
        self.assertIn("data:font/ttf;base64,", page)
        self.assertIn('font-family: "Phyrexian"', page)

    def test_escapes_html(self):
        page = render_html('!"<b>".')
        self.assertIn("&lt;b&gt;", page)


class CliTests(unittest.TestCase):
    def _run(self, *argv):
        import contextlib
        import sys

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        _ = sys
        return code, out.getvalue(), err.getvalue()

    def test_run_example(self):
        code, out, err = self._run("run", str(EXAMPLES / "01_welcome.phyx"))
        self.assertEqual(code, 0, err)
        self.assertIn("šdeχd-keθəɢð", out)

    def test_run_vertical_example(self):
        code, out, _ = self._run("run", str(EXAMPLES / "08_vertical.vphyx"))
        self.assertEqual(code, 0)
        self.assertIn("x: 5 x+10: 15", out)

    def test_run_ascii_example(self):
        code, out, _ = self._run("run", "--ascii", str(EXAMPLES / "07_ascii.phyx"))
        self.assertEqual(code, 0)
        self.assertIn("one more: 10", out)

    def test_error_reporting(self):
        code, _, err = self._run("run", str(EXAMPLES / "05_mistakes.phyx"))
        self.assertEqual(code, 1)
        self.assertIn("ɬšeɴazv [program] (line 29)", err)

    def test_check_and_words(self):
        code, out, _ = self._run("check", str(EXAMPLES / "03_abilities.phyx"))
        self.assertEqual(code, 0)
        self.assertIn("grammar is sound", out)
        code, out, _ = self._run("words")
        self.assertEqual(code, 0)
        self.assertIn("baxuφ", out)
        self.assertIn("ţə''", out)

    def test_missing_file(self):
        code, _, err = self._run("run", "nope.phyx")
        self.assertEqual(code, 1)
        self.assertIn("no such file", err)

    def test_error_shows_source_line(self):
        code, _, err = self._run("run", str(EXAMPLES / "05_mistakes.phyx"))
        self.assertEqual(code, 1)
        self.assertIn("line 29", err)
        self.assertIn("29 |", err)

    def test_sieve_example(self):
        code, out, err = self._run("run", str(EXAMPLES / "09_sieve.phyx"))
        self.assertEqual(code, 0, err)
        self.assertEqual(out.split(), ["2", "3", "5", "7", "0b", "0d", "11", "13", "17", "1d", "1f"])

    def test_include_example_lib(self):
        code, out, err = self._run("run", str(EXAMPLES / "lib_asərθ.phyx"))
        self.assertEqual(code, 0, err)
        # the library only defines abilities
        self.assertEqual(out, "")

    def test_implicit_run_is_the_path(self):
        code, out, err = self._run(str(EXAMPLES / "01_welcome.phyx"))
        self.assertEqual(code, 0, err)
        self.assertIn("šdeχd-keθəɢð", out)

    def test_eval_dash_c(self):
        code, out, err = self._run("-c", "!1-2-babg.")
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "3\n")

    def test_script_args_and_shebang(self):
        code, out, err = self._run(
            "run", str(EXAMPLES / "10_command.phyx"), "red", "blue",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("šdeχd-keθəɢð", out)
        self.assertIn("red", out)
        self.assertIn("blue", out)

    def test_kill_exit_code(self):
        code, _, _ = self._run("-c", "^lo-3-qab'.")
        self.assertEqual(code, 3)

    def test_version_names_the_language(self):
        code, out, err = self._run("-V")
        self.assertEqual(code, 0)
        text = out + err
        self.assertIn("φyrx", text)
        self.assertIn("PhyrxScript", text)
        self.assertIn("PhyrexianScript", text)

    def test_bench_runs(self):
        code, out, err = self._run("bench", "--size", "10", "--loops", "2000")
        self.assertEqual(code, 0, err)
        self.assertIn("φyrx", out)
        self.assertIn("python", out)
        self.assertIn("fib(", out)
        self.assertIn("timed after compile", out)

    def test_list_library_map(self):
        src = (
            '^lo-"lib_ťewn.phyx"-bukð.\n'
            "^ťe-n-dub:\n"
            "    ^lo-n-ķus'ər-'iţpənn.\n"
            "!1-2-3-3-ťewn-dub-naķm-map.\n"
        )
        from phyx.interpreter import run_source
        buf = io.StringIO()
        run_source(src, stdout=buf, base_dir=EXAMPLES)
        self.assertEqual(buf.getvalue().strip(), "2-4-6-3-ťewn")

    def test_sort_sum_min_max(self):
        from phyx.interpreter import run_source
        src = (
            '^lo-"lib_ťewn.phyx"-bukð.\n'
            '^lo-"lib_asərθ.phyx"-bukð.\n'
            "!3-1-2-3-ťewn-sort,1-2-3-3-ťewn-sum,ķi-9-min,ķi-9-max.\n"
        )
        buf = io.StringIO()
        run_source(src, stdout=buf, base_dir=EXAMPLES)
        self.assertEqual(buf.getvalue().strip(), "1-2-3-3-ťewn 6 3 9")

    def test_dis_shows_python(self):
        code, out, err = self._run("dis", str(EXAMPLES / "03_abilities.phyx"))
        self.assertEqual(code, 0, err)
        self.assertIn("def __phyx_run(_rt):", out)
        self.assertIn("def _a_", out)

    def test_lookup_uses_lexicon_without_fetch(self):
        code, out, err = self._run("lookup", "add")
        self.assertEqual(code, 0, err)
        self.assertIn("babg", out)
        self.assertNotIn("dictionary not downloaded", err)

    def test_lookup_conjugation_and_miss(self):
        code, out, err = self._run("lookup", "babeg")
        self.assertEqual(code, 0, err)
        self.assertIn("babg", out)
        code, out, err = self._run("lookup", "zzzznotawordzzzz")
        self.assertEqual(code, 1)
        self.assertIn("nothing found", out)


if __name__ == "__main__":
    unittest.main()
