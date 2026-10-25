"""Run φyrx programs as tests.

``python -m phyx test`` discovers ``test_*.phyx`` / ``test_*.vphyx``.
A file passes when it finishes without a fault; ``ǩaπa`` (must) is the
assertion. If a sibling ``*.expected`` file exists (same stem as the
test), stdout must match that UTF-8 text exactly (newlines normalised
to ``\\n``).
"""

from __future__ import annotations

import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .errors import PhyrexianError, format_error
from .interpreter import run_source

TEST_SUFFIXES = (".phyx", ".vphyx")


@dataclass
class TestResult:
    path: Path
    ok: bool
    detail: str = ""


def collect_tests(roots: Sequence[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        root = Path(root)
        if root.is_file():
            if _is_test_file(root) and root.resolve() not in seen:
                found.append(root)
                seen.add(root.resolve())
            continue
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("test_*")):
            if not _is_test_file(path):
                continue
            key = path.resolve()
            if key in seen:
                continue
            seen.add(key)
            found.append(path)
    return found


def _is_test_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEST_SUFFIXES and path.name.startswith("test_")


def expected_sidecar(path: Path) -> Path:
    return path.with_suffix(".expected")


def _norm_out(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def run_test_file(path: Path, *, ascii_mode: bool = False) -> TestResult:
    src = path.read_text(encoding="utf-8")
    buf = io.StringIO()
    try:
        run_source(
            src,
            stdout=buf,
            base_dir=path.parent,
            ascii_mode=ascii_mode,
        )
    except PhyrexianError as err:
        return TestResult(path, False, format_error(err, src))
    got = _norm_out(buf.getvalue())
    sidecar = expected_sidecar(path)
    if sidecar.is_file():
        want = _norm_out(sidecar.read_text(encoding="utf-8"))
        if got != want:
            return TestResult(
                path,
                False,
                f"stdout does not match {sidecar.name}\n"
                f"  expected {want!r}\n"
                f"  got      {got!r}",
            )
    return TestResult(path, True, got)


def run_suite(
    roots: Sequence[Path],
    *,
    ascii_mode: bool = False,
    stdout: TextIO | None = None,
) -> int:
    import sys

    out = stdout if stdout is not None else sys.stdout
    files = collect_tests(roots)
    if not files:
        print("no test_*.phyx files found", file=out)
        return 1
    failed = 0
    for path in files:
        result = run_test_file(path, ascii_mode=ascii_mode)
        rel = path
        if result.ok:
            print(f"ok   {rel}", file=out)
        else:
            failed += 1
            print(f"FAIL {rel}", file=out)
            if result.detail:
                for line in result.detail.splitlines():
                    print(f"     {line}", file=out)
    total = len(files)
    print(f"{total - failed} passed, {failed} failed, {total} tests", file=out)
    return 0 if failed == 0 else 1


def format_roots(roots: Iterable[Path]) -> str:
    return ", ".join(str(r) for r in roots)
