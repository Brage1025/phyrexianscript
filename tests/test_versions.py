"""The version rule in docs/spec.md section 9.

The language version is major.minor of the toolchain version. The editor
manifest has its own cadence: only its shape is checked here.
"""

import json
import re
import tomllib
import unittest
from pathlib import Path

import phyx

ROOT = Path(__file__).resolve().parent.parent

_VERSION_HEADING = re.compile(r"(\d+\.\d+\.\d+)(?: - \d{4}-\d{2}-\d{2})?")
_README_LANGUAGE = re.compile(r"^Language version: (\d+\.\d+)\s*$", re.M)


def _project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def _major_minor(toolchain: str) -> str:
    major, minor, *_rest = toolchain.split(".")
    return f"{major}.{minor}"


class VersionRuleTests(unittest.TestCase):
    def test_package_version_matches_pyproject(self):
        self.assertEqual(
            phyx.__version__,
            _project_version(),
            'phyx.__version__ does not match pyproject.toml; run python -m pip install -e ".[dev]" again',
        )

    def test_spec_heading_is_the_language_version(self):
        heading = (ROOT / "docs" / "spec.md").read_text(encoding="utf-8").splitlines()[0]
        match = re.fullmatch(r"# φyrx language specification \((\d+\.\d+)\)", heading)
        self.assertIsNotNone(match, f"spec heading is not the language version: {heading}")
        self.assertEqual(match.group(1), _major_minor(_project_version()))

    def test_readme_status_names_the_language_version(self):
        """Status must contain a line 'Language version: X.Y'.

        X.Y is major.minor of the package version. A missing line fails.
        """
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        section = re.search(r"^## Status\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        self.assertIsNotNone(section, "README.md has no ## Status section")
        match = _README_LANGUAGE.search(section.group(1))
        self.assertIsNotNone(match, "README status has no line 'Language version: X.Y'")
        language = _major_minor(_project_version())
        self.assertEqual(
            match.group(1),
            language,
            f"README status names language {match.group(1)}, not {language}",
        )

    def test_changelog_unreleased_then_package_version(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", text, re.M)
        self.assertTrue(headings, "CHANGELOG.md has no ## headings")
        self.assertEqual(headings[0], "Unreleased")
        versioned = [heading for heading in headings if heading != "Unreleased"]
        self.assertTrue(versioned, "CHANGELOG.md has no versioned heading")
        match = _VERSION_HEADING.fullmatch(versioned[0])
        self.assertIsNotNone(match, f"first versioned heading is not a version: {versioned[0]}")
        self.assertEqual(match.group(1), _project_version())

    def test_editor_manifest_version_is_its_own_xyz(self):
        data = json.loads((ROOT / "editors" / "package.json").read_text(encoding="utf-8"))
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")
