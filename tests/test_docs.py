"""Mechanical claims in the docs must match the running language."""

import json
import unittest
from pathlib import Path

from phyx.cli import SUBCOMMANDS
from phyx.vocabulary import CONSTANTS, MARKERS, VERBS

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def _read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class DocDriftTests(unittest.TestCase):
    def test_every_subcommand_is_in_the_toolchain_page(self):
        text = _read("docs", "toolchain.md")
        missing = sorted(cmd for cmd in SUBCOMMANDS if cmd not in text)
        self.assertEqual(missing, [], f"docs/toolchain.md omits {missing}")

    def test_readme_names_explain_fmt_lint(self):
        text = _read("README.md")
        for cmd in ("explain", "fmt", "lint", "bench", "dis", "test", "lib", "new", "lsp"):
            self.assertIn(cmd, text)

    def test_reference_lists_every_verb_and_marker(self):
        text = _read("docs", "reference.md")
        missing_v = sorted(w for w in VERBS if f"`{w}`" not in text)
        missing_m = sorted(w for w in MARKERS if f"`{w}`" not in text)
        missing_c = sorted(w for w in CONSTANTS if f"`{w}`" not in text)
        self.assertEqual(missing_v, [], f"verbs missing from reference: {missing_v}")
        self.assertEqual(missing_m, [], f"markers missing from reference: {missing_m}")
        self.assertEqual(missing_c, [], f"constants missing from reference: {missing_c}")

    def test_extension_manifest_contributes_phyx(self):
        data = json.loads(_read("editors", "package.json"))
        self.assertEqual(data["name"], "phyx")
        langs = data["contributes"]["languages"]
        self.assertTrue(any(lang.get("id") == "phyx" for lang in langs))
        exts = {e for lang in langs for e in lang.get("extensions", [])}
        self.assertIn(".phyx", exts)
        self.assertIn(".vphyx", exts)
        grammars = data["contributes"]["grammars"]
        self.assertTrue(any(g.get("scopeName") == "source.phyx" for g in grammars))
        self.assertTrue((ROOT / "editors" / "phyx.tmLanguage.json").is_file())

    def test_ci_runs_both_test_commands(self):
        text = _read(".github", "workflows", "ci.yml")
        self.assertIn("python -m unittest discover -s tests -v", text)
        self.assertIn("python -m phyx test", text)

    def test_readme_install_name_matches_pyproject(self):
        import tomllib

        name = tomllib.loads(_read("pyproject.toml"))["project"]["name"]
        self.assertEqual(name, "phyx")
        self.assertIn("pip install phyx", _read("README.md"))

    def test_spec_and_guide_exist(self):
        for name in (
            "spec.md",
            "guide.md",
            "python.md",
            "cookbook.md",
            "rationale.md",
            "index.md",
            "tour.md",
            "stdlib.md",
            "toolchain.md",
            "reference.md",
            "roadmap.md",
        ):
            self.assertTrue((DOCS / name).is_file(), name)
