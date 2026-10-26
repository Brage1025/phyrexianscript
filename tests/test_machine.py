import io
import unittest
from pathlib import Path

from phyx.interpreter import run_source

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def run(src, **kw):
    out = io.StringIO()
    run_source(src, stdout=out, **kw)
    return out.getvalue()


class TuringMachineTests(unittest.TestCase):
    def test_unary_adder(self):
        src = (EXAMPLES / "11_machine.phyx").read_text(encoding="utf-8")
        self.assertEqual(run(src).strip(), "5")

    def test_treewalk_agrees_on_the_machine(self):
        src = (EXAMPLES / "11_machine.phyx").read_text(encoding="utf-8")
        compiled = run(src)
        walked = run(src, treewalk=True)
        self.assertEqual(compiled, walked)


class CompletenessTests(unittest.TestCase):
    def test_unbounded_while_and_tape(self):
        # grow a list until it holds 8 items — unbounded store + while
        src = "^xe-0-ťewn-tape-ţə''.\n^baxuφ-tape-samk-8-grmɒɣg:\n    ^xe-tape-tape-samk-bɬølπ.\n!tape-samk.\n"
        self.assertEqual(run(src).strip(), "8")
