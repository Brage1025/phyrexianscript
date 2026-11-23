"""Offline tests for pinned font and dictionary downloads."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
import re
import stat
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from phyx.cli import cmd_fetch

_UPSTREAM = "The file changed upstream. Update phyx."

_FONT = b"\x00\x01\x00\x00phyrexian-font-bytes"
_OTHER = b"\x00\x01\x00\x00different-font-bytes"
_DICT = b'{"dictionary":{"fetch":"pinned"}}'


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Body:
    def __init__(self, data: bytes, final: str, reads: list[int] | None = None):
        self._data = data
        self._final = final
        self._reads = reads

    def read(self, n: int = -1) -> bytes:
        if self._reads is not None:
            self._reads.append(n)
        if n is None or n < 0:
            return self._data
        return self._data[:n]

    def geturl(self) -> str:
        return self._final

    def __enter__(self) -> _Body:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class PinnedFetchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _dest(self, name: str) -> Path:
        return self.root / name

    def _patch_urls(self, payloads: dict[str, tuple[bytes, str]], reads: list[int] | None = None):
        def open_url(req, timeout=60):
            data, final = payloads[req.full_url]
            return _Body(data, final, reads)

        return mock.patch("phyx.fonts.urllib.request.urlopen", side_effect=open_url)

    def test_matching_download_writes_the_exact_bytes(self) -> None:
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        url = "https://example.invalid/font.ttf"
        with self._patch_urls({url: (_FONT, url)}):
            got = _download([url], dest, _sha(_FONT), 1024)
        self.assertEqual(got, dest)
        self.assertEqual(dest.read_bytes(), _FONT)
        self.assertEqual([p.name for p in self.root.iterdir()], [dest.name])

    def test_hash_mismatch_falls_through_to_the_next_url(self) -> None:
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        first = "https://example.invalid/first.ttf"
        second = "https://example.invalid/second.ttf"
        seen: list[str] = []

        def open_url(req, timeout=60):
            seen.append(req.full_url)
            data = _OTHER if req.full_url == first else _FONT
            return _Body(data, req.full_url)

        with mock.patch("phyx.fonts.urllib.request.urlopen", side_effect=open_url):
            got = _download([first, second], dest, _sha(_FONT), 1024)
        self.assertEqual(seen, [first, second])
        self.assertEqual(got.read_bytes(), _FONT)

    def test_every_url_failing_touches_nothing(self) -> None:
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        urls = ["https://example.invalid/a.ttf", "https://example.invalid/b.ttf"]
        payloads = {url: (_OTHER, url) for url in urls}
        with self._patch_urls(payloads):
            with self.assertRaises(OSError) as raised:
                _download(urls, dest, _sha(_FONT), 1024)
        self.assertIn(dest.name, str(raised.exception))
        self.assertIn(_UPSTREAM, str(raised.exception))
        self.assertFalse(dest.exists())
        self.assertEqual(list(self.root.iterdir()), [])

        original = b"\x00\x01\x00\x00keep-this-file"
        dest.write_bytes(original)
        with self._patch_urls(payloads):
            with self.assertRaises(OSError) as raised:
                _download(urls, dest, _sha(_FONT), 1024)
        self.assertIn(_UPSTREAM, str(raised.exception))
        self.assertEqual(dest.read_bytes(), original)
        self.assertEqual([p.name for p in self.root.iterdir()], [dest.name])

    def test_replace_failure_removes_the_temporary_file(self) -> None:
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        original = b"\x00\x01\x00\x00already-here"
        dest.write_bytes(original)
        url = "https://example.invalid/font.ttf"

        def refuse(src, dst):
            raise OSError("disk full")

        with self._patch_urls({url: (_FONT, url)}), mock.patch("phyx.fonts.os.replace", side_effect=refuse):
            with self.assertRaises(OSError):
                _download([url], dest, _sha(_FONT), 1024)
        self.assertEqual(dest.read_bytes(), original)
        self.assertEqual([p.name for p in self.root.iterdir()], [dest.name])

    def test_downloaded_file_follows_the_umask(self) -> None:
        if sys.platform == "win32":
            self.skipTest("umask does not apply on Windows")
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        url = "https://example.invalid/font.ttf"
        previous = os.umask(0o022)
        try:
            with self._patch_urls({url: (_FONT, url)}):
                _download([url], dest, _sha(_FONT), 1024)
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o644)
            self.assertFalse(any(".part" in path.name for path in self.root.iterdir()))
        finally:
            os.umask(previous)

    def test_oversized_response_is_rejected(self) -> None:
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        url = "https://example.invalid/font.ttf"
        payload = _FONT + (b"x" * 64)
        limit = 8
        reads: list[int] = []
        with self._patch_urls({url: (payload, url)}, reads):
            with self.assertRaises(OSError) as raised:
                _download([url], dest, _sha(payload), limit)
        self.assertIn("larger than", str(raised.exception))
        self.assertIn(dest.name, str(raised.exception))
        self.assertEqual(reads, [limit + 1])
        self.assertFalse(dest.exists())

    def test_redirect_away_from_https_is_rejected(self) -> None:
        from phyx.fonts import _download

        dest = self._dest("Phyrexian-Regular.ttf")
        url = "https://example.invalid/font.ttf"
        with self._patch_urls({url: (_FONT, "http://example.invalid/font.ttf")}):
            with self.assertRaises(OSError) as raised:
                _download([url], dest, _sha(_FONT), 1024)
        self.assertIn(dest.name, str(raised.exception))
        self.assertNotIn(_UPSTREAM, str(raised.exception))
        self.assertFalse(dest.exists())

    def test_fetch_keeps_a_match_and_replaces_a_mismatch(self) -> None:
        from phyx.fonts import ensure_pinned

        dest = self._dest("Phyrexian-Regular.ttf")
        url = "https://example.invalid/font.ttf"
        dest.write_bytes(_FONT)

        def boom(*args, **kwargs):
            raise AssertionError(f"urlopen was called: {args} {kwargs}")

        with mock.patch("phyx.fonts.urllib.request.urlopen", side_effect=boom):
            got = ensure_pinned(dest, [url], _sha(_FONT))
        self.assertEqual(got, dest)
        self.assertEqual(dest.read_bytes(), _FONT)

        dest.write_bytes(_OTHER)
        with self._patch_urls({url: (_FONT, url)}):
            got = ensure_pinned(dest, [url], _sha(_FONT))
        self.assertEqual(got.read_bytes(), _FONT)

    def test_dictionary_path_checks_its_hash(self) -> None:
        from phyx.fonts import ensure_pinned, is_font_bytes

        self.assertFalse(is_font_bytes(_DICT))
        dest = self._dest("dictionary.json")
        url = "https://example.invalid/PhyrexianAPI.json"
        with self._patch_urls({url: (_DICT, url)}):
            got = ensure_pinned(dest, [url], _sha(_DICT), require_font=False)
        self.assertEqual(got.read_bytes(), _DICT)

        wrong = self._dest("dictionary-wrong.json")
        with self._patch_urls({url: (b"not-the-dictionary", url)}):
            with self.assertRaises(OSError) as raised:
                ensure_pinned(wrong, [url], _sha(_DICT), require_font=False)
        self.assertIn(wrong.name, str(raised.exception))
        self.assertIn(_UPSTREAM, str(raised.exception))
        self.assertFalse(wrong.exists())

    def test_ensure_font_keeps_any_valid_file_and_verifies_a_download(self) -> None:
        from phyx.fonts import ensure_basilica, ensure_font

        font = self._dest("Phyrexian-Regular.ttf")
        basilica = self._dest("Basilica.otf")
        font.write_bytes(_OTHER)
        basilica.write_bytes(_OTHER)

        def boom(*args, **kwargs):
            raise AssertionError(f"urlopen was called: {args} {kwargs}")

        with mock.patch("phyx.fonts.urllib.request.urlopen", side_effect=boom):
            self.assertEqual(ensure_font(font), font)
            self.assertEqual(ensure_basilica(basilica), basilica)
        self.assertEqual(font.read_bytes(), _OTHER)
        self.assertEqual(basilica.read_bytes(), _OTHER)

        from phyx.fonts import FONT_CDN, FONT_REMOTE

        missing = self._dest("missing") / "Phyrexian-Regular.ttf"
        payloads = {FONT_CDN: (_FONT, FONT_CDN), FONT_REMOTE: (_FONT, FONT_REMOTE)}
        with self._patch_urls(payloads):
            with self.assertRaises(OSError) as raised:
                ensure_font(missing)
        self.assertIn(_UPSTREAM, str(raised.exception))
        self.assertFalse(missing.exists())

        with mock.patch("phyx.fonts.PHYREXIAN_SHA256", _sha(_FONT)), self._patch_urls(payloads):
            got = ensure_font(missing)
        self.assertEqual(got.read_bytes(), _FONT)

    def test_cmd_fetch_reports_a_network_failure(self) -> None:
        font = self._dest("fonts") / "Phyrexian-Regular.ttf"
        basilica = self._dest("fonts") / "Basilica.otf"
        dictionary = self._dest("dictionary.json")
        err = io.StringIO()
        with (
            mock.patch("phyx.cli.local_font", return_value=font),
            mock.patch("phyx.cli.local_basilica", return_value=basilica),
            mock.patch("phyx.cli.local_dictionary", return_value=dictionary),
            mock.patch("phyx.cli.install_user_font", return_value=None),
            mock.patch("phyx.fonts.urllib.request.urlopen", side_effect=urllib.error.URLError("offline")),
            contextlib.redirect_stderr(err),
        ):
            code = cmd_fetch(argparse.Namespace())
        self.assertEqual(code, 1)
        self.assertIn("error:", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())
        self.assertFalse(font.exists())
        self.assertFalse(basilica.exists())
        self.assertFalse(dictionary.exists())

    def test_cmd_fetch_says_when_a_file_already_matches(self) -> None:
        font = self._dest("Phyrexian-Regular.ttf")
        basilica = self._dest("Basilica.otf")
        dictionary = self._dest("dictionary.json")
        font.write_bytes(_FONT)
        basilica.write_bytes(_OTHER)
        dictionary.write_bytes(_DICT)
        out = io.StringIO()

        def boom(*args, **kwargs):
            raise AssertionError(f"urlopen was called: {args} {kwargs}")

        with (
            mock.patch("phyx.cli.local_font", return_value=font),
            mock.patch("phyx.cli.local_basilica", return_value=basilica),
            mock.patch("phyx.cli.local_dictionary", return_value=dictionary),
            mock.patch("phyx.cli.PHYREXIAN_SHA256", _sha(_FONT)),
            mock.patch("phyx.cli.BASILICA_SHA256", _sha(_OTHER)),
            mock.patch("phyx.cli.DICT_SHA256", _sha(_DICT)),
            mock.patch("phyx.cli.install_user_font", return_value=None),
            mock.patch("phyx.fonts.urllib.request.urlopen", side_effect=boom),
            contextlib.redirect_stdout(out),
        ):
            code = cmd_fetch(argparse.Namespace())
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().count("already up to date"), 3)
        self.assertEqual(font.read_bytes(), _FONT)
        self.assertEqual(dictionary.read_bytes(), _DICT)

    def test_pinned_urls_use_commits(self) -> None:
        from phyx import fonts
        from phyx.render import font_source

        font_urls = [fonts.FONT_REMOTE, fonts.FONT_CDN, fonts.BASILICA_REMOTE, fonts.BASILICA_CDN]
        dict_urls = [fonts.DICT_REMOTE, fonts.DICT_CDN]
        for url in font_urls + dict_urls:
            self.assertTrue(url.startswith("https://"), url)
            self.assertNotIn("/main/", url)
            self.assertNotIn("@main", url)
            self.assertNotIn("gh-pages", url)
        for url in font_urls:
            self.assertIn(fonts.FONT_COMMIT, url)
        for url in dict_urls:
            self.assertIn(fonts.DICT_COMMIT, url)
        page = font_source(None)
        self.assertIn(fonts.FONT_COMMIT, page)
        self.assertNotIn("/main/", page)
        self.assertNotIn("@main", page)

    def test_font_pins_match_editors_fonts_js(self) -> None:
        js_path = Path(__file__).resolve().parent.parent / "editors" / "fonts.js"
        if not js_path.is_file():
            self.skipTest("editors/fonts.js is not present")
        text = js_path.read_text(encoding="utf-8")
        from phyx import fonts

        for name in ("FONT_COMMIT", "PHYREXIAN_SHA256", "BASILICA_SHA256"):
            match = re.search(rf'const {name} = "([0-9a-fA-F]+)"', text)
            self.assertIsNotNone(match, name)
            assert match is not None
            self.assertEqual(getattr(fonts, name), match.group(1))


if __name__ == "__main__":
    unittest.main()
