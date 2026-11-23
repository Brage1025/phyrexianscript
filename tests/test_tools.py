import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from phyx.cli import main
from phyx.render import render_html
from phyx.vertical import from_vertical, to_vertical

_REAL_COPY2 = shutil.copy2

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
        self.assertIn('local("Phyrexian")', src)

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


class _Winreg:
    def __init__(self):
        self.HKEY_CURRENT_USER = object()
        self.REG_SZ = 1
        self.entries = []

    def CreateKey(self, root, path):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def SetValueEx(self, key, name, reserved, typ, value):
        self.entries.append((name, value))


class InstallUserFontTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.local = self.root / "LocalAppData"
        (self.local / "Microsoft" / "Windows").mkdir(parents=True)
        self.src = self.root / "Phyrexian-Regular.ttf"
        self.src.write_bytes(b"\x00\x01\x00\x00" + b"phyrexian-font")
        self.dest = self.local / "Microsoft" / "Windows" / "Fonts" / self.src.name

    def tearDown(self):
        self.tmp.cleanup()

    def _install(self, copy2):
        import phyx.fonts as fonts

        winreg = _Winreg()
        stderr = io.StringIO()
        with (
            mock.patch.object(fonts.sys, "platform", "win32"),
            mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)}),
            mock.patch.object(fonts.shutil, "copy2", copy2),
            mock.patch.dict(sys.modules, {"winreg": winreg}),
            contextlib.redirect_stderr(stderr),
        ):
            result = fonts.install_user_font(self.src, "Phyrexian")
        return result, stderr.getvalue(), winreg

    def test_identical_file_is_already_installed(self):
        self.dest.parent.mkdir(parents=True)
        self.dest.write_bytes(self.src.read_bytes())
        calls = []

        def copy2(src, dst, *args, **kwargs):
            calls.append(Path(dst))
            return _REAL_COPY2(src, dst, *args, **kwargs)

        result, err, winreg = self._install(copy2)
        self.assertEqual(calls, [])
        self.assertEqual(result, self.dest)
        self.assertEqual(self.dest.read_bytes(), self.src.read_bytes())
        self.assertEqual(err, "")
        self.assertEqual(winreg.entries, [("Phyrexian (TrueType)", str(self.dest))])

    def test_locked_different_file_warns_and_returns_none(self):
        self.dest.parent.mkdir(parents=True)
        self.dest.write_bytes(b"\x00\x01\x00\x00" + b"other-font!!")
        calls = []

        def copy2(src, dst, *args, **kwargs):
            calls.append(Path(dst))
            raise PermissionError(
                32,
                "The process cannot access the file because it is being used by another process",
                str(dst),
            )

        result, err, winreg = self._install(copy2)
        self.assertEqual(calls, [self.dest])
        self.assertIsNone(result)
        self.assertEqual(self.dest.read_bytes(), b"\x00\x01\x00\x00" + b"other-font!!")
        self.assertEqual(err.count("\n"), 1)
        self.assertIn(str(self.dest), err)
        self.assertIn("being used by another process", err)
        self.assertEqual(winreg.entries, [])

    def test_normal_copy_installs_the_font(self):
        calls = []

        def copy2(src, dst, *args, **kwargs):
            calls.append(Path(dst))
            return _REAL_COPY2(src, dst, *args, **kwargs)

        result, err, winreg = self._install(copy2)
        self.assertEqual(calls, [self.dest])
        self.assertEqual(result, self.dest)
        self.assertEqual(self.dest.read_bytes(), self.src.read_bytes())
        self.assertEqual(err, "")
        self.assertEqual(winreg.entries, [("Phyrexian (TrueType)", str(self.dest))])


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
            "run",
            str(EXAMPLES / "10_command.phyx"),
            "red",
            "blue",
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
        src = "^lo-\"lib_ťewn.phyx\"-bukð.\n^ťe-n-dub:\n    ^lo-n-ķus'ər-'iţpənn.\n!1-2-3-3-ťewn-dub-naķm-map.\n"
        from phyx.interpreter import run_source

        buf = io.StringIO()
        run_source(src, stdout=buf, base_dir=EXAMPLES)
        self.assertEqual(buf.getvalue().strip(), "2-4-6-3-ťewn")

    def test_sort_sum_min_max(self):
        from phyx.interpreter import run_source

        src = '^lo-"lib_ťewn.phyx"-bukð.\n^lo-"lib_asərθ.phyx"-bukð.\n!3-1-2-3-ťewn-sort,1-2-3-3-ťewn-sum,ķi-9-min,ķi-9-max.\n'
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


_FONT_BYTES = b"\x00\x01\x00\x00" + b"phyrexian-font"


class AssetsDirTests(unittest.TestCase):
    """Font and dictionary locations. Every path is under a temp directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _checkout(self, name: str = "checkout") -> Path:
        root = self.root / name
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        return root

    def _install(self, name: str = "site-packages") -> Path:
        root = self.root / name
        root.mkdir(parents=True)
        return root

    def _font(self, path: Path, data: bytes = _FONT_BYTES) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_user_data_dir_per_platform(self):
        from phyx import fonts

        local = self.root / "LocalAppData"
        xdg = self.root / "xdg"
        cases = (
            ("win32", {"LOCALAPPDATA": str(local)}, local / "phyx"),
            (
                "darwin",
                {"XDG_DATA_HOME": str(xdg), "LOCALAPPDATA": str(local)},
                self.home / "Library" / "Application Support" / "phyx",
            ),
            ("linux", {"XDG_DATA_HOME": str(xdg), "LOCALAPPDATA": str(local)}, xdg / "phyx"),
            ("linux", {}, self.home / ".local" / "share" / "phyx"),
        )
        for platform, env, expected in cases:
            with self.subTest(platform=platform, env=sorted(env)):
                got = fonts.user_data_dir(platform, env, self.home)
                self.assertEqual(got, expected)
                self.assertFalse(got.exists())

    def test_windows_without_localappdata_uses_home(self):
        from phyx import fonts

        for env in ({}, {"LOCALAPPDATA": ""}):
            with self.subTest(env=env):
                got = fonts.user_data_dir("win32", env, self.home)
                self.assertEqual(got, self.home / "AppData" / "Local" / "phyx")
                self.assertFalse(got.exists())

    def test_empty_xdg_data_home_uses_home(self):
        from phyx import fonts

        got = fonts.user_data_dir("linux", {"XDG_DATA_HOME": ""}, self.home)
        self.assertEqual(got, self.home / ".local" / "share" / "phyx")
        self.assertFalse(got.exists())

    def test_phyx_assets_wins(self):
        from phyx import fonts

        override = self.root / "override"
        env = {
            "PHYX_ASSETS": str(override),
            "LOCALAPPDATA": str(self.root / "Local"),
            "XDG_DATA_HOME": str(self.root / "xdg"),
        }
        for root in (self._checkout(), self._install()):
            with self.subTest(root=root.name):
                got = fonts.assets_dir(env=env, package_root=root, platform="win32", home=self.home)
                self.assertEqual(got, override)
                self.assertFalse(override.exists())
                self.assertFalse((root / "assets").exists())

    def test_empty_phyx_assets_does_not_win(self):
        from phyx import fonts

        root = self._checkout("empty-override")
        got = fonts.assets_dir(env={"PHYX_ASSETS": ""}, package_root=root, platform="linux", home=self.home)
        self.assertEqual(got, root / "assets")
        self.assertFalse((root / "assets").exists())

    def test_source_checkout_keeps_repo_assets(self):
        from phyx import fonts

        root = self._checkout("src")
        env = {"LOCALAPPDATA": str(self.root / "Local"), "XDG_DATA_HOME": str(self.root / "xdg")}
        got = fonts.assets_dir(env=env, package_root=root, platform="win32", home=self.home)
        self.assertEqual(got, root / "assets")
        self.assertFalse(got.exists())

    def test_install_uses_the_user_data_dir(self):
        from phyx import fonts

        root = self._install()
        local = self.root / "Local"
        got = fonts.assets_dir(
            env={"LOCALAPPDATA": str(local)},
            package_root=root,
            platform="win32",
            home=self.home,
        )
        self.assertEqual(got, local / "phyx")
        self.assertFalse(got.exists())
        self.assertFalse(local.exists())

    def test_pyproject_beside_the_install_root_does_not_count(self):
        from phyx import fonts

        install = self._install("venv/Lib/site-packages")
        (install.parent / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        local = self.root / "Local"
        got = fonts.assets_dir(
            env={"LOCALAPPDATA": str(local)},
            package_root=install,
            platform="win32",
            home=self.home,
        )
        self.assertEqual(got, local / "phyx")

    def test_running_tree_is_a_source_checkout(self):
        from phyx import fonts

        root = Path(fonts.__file__).resolve().parent.parent
        self.assertTrue((root / "pyproject.toml").is_file())
        with mock.patch.dict(os.environ, {"PHYX_ASSETS": ""}):
            self.assertEqual(fonts.assets_dir(), root / "assets")

    def test_cli_assets_dir_is_the_fonts_one(self):
        import phyx.cli as cli
        import phyx.fonts as fonts

        self.assertIs(cli.assets_dir, fonts.assets_dir)

    def test_local_dictionary_follows_phyx_assets(self):
        from phyx.cli import local_dictionary

        override = self.root / "dict-home"
        with mock.patch.dict(os.environ, {"PHYX_ASSETS": str(override)}):
            self.assertEqual(local_dictionary(), override / "dictionary.json")
        self.assertFalse(override.exists())

    def _legacy(self, name: str, root: Path, env: dict[str, str]):
        from phyx import fonts

        return fonts.legacy_font(name, env=env, package_root=root, platform="win32", home=self.home)

    def test_legacy_font_is_used_when_the_user_dir_has_no_fonts(self):
        from phyx.fonts import FONT_FILE

        root = self._install("installed-a")
        old = self._font(root / "assets" / "fonts" / FONT_FILE)
        local = self.root / "LocalA"
        got = self._legacy(FONT_FILE, root, {"LOCALAPPDATA": str(local)})
        self.assertEqual(got, old)
        self.assertFalse((local / "phyx").exists())

    def test_legacy_font_rejects_a_non_font(self):
        from phyx.fonts import FONT_FILE

        root = self._install("installed-b")
        self._font(root / "assets" / "fonts" / FONT_FILE, b"<html>not a font</html>")
        got = self._legacy(FONT_FILE, root, {"LOCALAPPDATA": str(self.root / "LocalB")})
        self.assertIsNone(got)

    def test_legacy_font_stops_once_the_user_dir_has_a_font(self):
        from phyx.fonts import BASILICA_FILE, FONT_FILE

        root = self._install("installed-c")
        self._font(root / "assets" / "fonts" / FONT_FILE)
        local = self.root / "LocalC"
        self._font(local / "phyx" / "fonts" / BASILICA_FILE)
        got = self._legacy(FONT_FILE, root, {"LOCALAPPDATA": str(local)})
        self.assertIsNone(got)

    def test_legacy_font_ignores_a_non_font_already_in_the_user_dir(self):
        from phyx.fonts import FONT_FILE

        root = self._install("installed-d")
        old = self._font(root / "assets" / "fonts" / FONT_FILE)
        local = self.root / "LocalD"
        self._font(local / "phyx" / "fonts" / FONT_FILE, b"<html>not a font</html>")
        got = self._legacy(FONT_FILE, root, {"LOCALAPPDATA": str(local)})
        self.assertEqual(got, old)

    def test_legacy_font_skips_a_checkout_and_an_override(self):
        from phyx import fonts
        from phyx.fonts import FONT_FILE

        checkout = self._checkout("src-legacy")
        self._font(checkout / "assets" / "fonts" / FONT_FILE)
        env = {"LOCALAPPDATA": str(self.root / "LocalE")}
        self.assertIsNone(self._legacy(FONT_FILE, checkout, env))

        root = self._install("installed-e")
        self._font(root / "assets" / "fonts" / FONT_FILE)
        overridden = {**env, "PHYX_ASSETS": str(self.root / "override")}
        self.assertIsNone(fonts.legacy_font(FONT_FILE, env=overridden, package_root=root, platform="win32", home=self.home))
        self.assertFalse((self.root / "override").exists())

    def test_ensure_font_reads_the_legacy_file_without_downloading(self):
        from phyx import fonts

        old = self._font(self.root / "old" / "Phyrexian-Regular.ttf")
        missing = self.root / "user" / "fonts" / "Phyrexian-Regular.ttf"

        def boom(urls, dest, *_args):
            raise AssertionError(f"downloaded {dest}")

        with (
            mock.patch.object(fonts, "local_font", return_value=missing),
            mock.patch.object(fonts, "legacy_font", return_value=old, create=True),
            mock.patch.object(fonts, "_download", boom),
        ):
            self.assertEqual(fonts.ensure_font(), old)
        self.assertFalse(missing.exists())

    def test_ensure_basilica_reads_the_legacy_file_without_downloading(self):
        from phyx import fonts

        old = self._font(self.root / "old" / "Basilica.otf")
        missing = self.root / "user" / "fonts" / "Basilica.otf"

        def boom(urls, dest, *_args):
            raise AssertionError(f"downloaded {dest}")

        with (
            mock.patch.object(fonts, "local_basilica", return_value=missing),
            mock.patch.object(fonts, "legacy_font", return_value=old, create=True),
            mock.patch.object(fonts, "_download", boom),
        ):
            self.assertEqual(fonts.ensure_basilica(), old)
        self.assertFalse(missing.exists())

    def test_ensure_font_downloads_to_the_new_path(self):
        from phyx import fonts

        dest = self.root / "user" / "fonts" / "Phyrexian-Regular.ttf"
        seen = []

        def download(urls, path, *_args):
            seen.append(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_FONT_BYTES)
            return path

        with (
            mock.patch.object(fonts, "local_font", return_value=dest),
            mock.patch.object(fonts, "legacy_font", return_value=None, create=True),
            mock.patch.object(fonts, "_download", download),
        ):
            self.assertEqual(fonts.ensure_font(), dest)
        self.assertEqual(seen, [dest])

    def test_explicit_dest_is_where_the_download_goes(self):
        from phyx import fonts

        dest = self.root / "out" / "Phyrexian-Regular.ttf"
        old = self._font(self.root / "old-explicit.ttf")
        seen = []

        def download(urls, path, *_args):
            seen.append(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_FONT_BYTES)
            return path

        with (
            mock.patch.object(fonts, "legacy_font", return_value=old, create=True),
            mock.patch.object(fonts, "_download", download),
        ):
            self.assertEqual(fonts.ensure_font(dest), dest)
        self.assertEqual(seen, [dest])


if __name__ == "__main__":
    unittest.main()
