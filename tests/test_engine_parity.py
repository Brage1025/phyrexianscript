"""The compiled engine and the tree-walker must agree.

``run_both`` runs one source on each engine. A Phyrexian fault is
``(class name, message, line, hint)``. Any other Python exception is
``"PYTHON:"`` plus the exception name. ``assertParity`` fails when
those results differ.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from phyx.errors import PhyrexianError
from phyx.interpreter import Interpreter
from phyx.parser import parse
from phyx.vertical import from_vertical

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
PHYX_TESTS = ROOT / "tests" / "phyx"
SOURCE_SUFFIXES = {".phyx", ".vphyx"}


def _run_one(source, *, treewalk, argv=None, stdin="", base_dir=None, persistent=False):
    """Run ``source`` on one engine. Return ``(stdout, fault)``."""
    out = io.StringIO()
    fault = None
    try:
        program = parse(source, base_dir=base_dir)
        Interpreter(
            stdout=out,
            stdin=io.StringIO(stdin),
            argv=argv,
            base_dir=base_dir,
            persistent=persistent,
            treewalk=treewalk,
        ).run(program)
    except PhyrexianError as err:
        fault = (type(err).__name__, err.message, err.line, err.hint)
    except KeyboardInterrupt:
        raise
    except BaseException as err:
        fault = "PYTHON:" + type(err).__name__
    return (out.getvalue(), fault)


def run_both(source, argv=None, stdin="", base_dir=None, persistent=False):
    """Run ``source`` on the compiled engine and the tree-walker."""
    compiled = _run_one(
        source, treewalk=False, argv=argv, stdin=stdin, base_dir=base_dir,
        persistent=persistent,
    )
    walked = _run_one(
        source, treewalk=True, argv=argv, stdin=stdin, base_dir=base_dir,
        persistent=persistent,
    )
    return compiled, walked


def _run_chunks(chunks, *, treewalk):
    """Run several programs on one persistent interpreter. Return ``(stdout, fault)``."""
    out = io.StringIO()
    fault = None
    interp = Interpreter(stdout=out, persistent=True, treewalk=treewalk)
    try:
        for source in chunks:
            program = parse(source, known_functions=interp.known_functions())
            interp.run(program)
    except PhyrexianError as err:
        fault = (type(err).__name__, err.message, err.line, err.hint)
    except KeyboardInterrupt:
        raise
    except BaseException as err:
        fault = "PYTHON:" + type(err).__name__
    return (out.getvalue(), fault)


def assertParity(source, argv=None, stdin="", base_dir=None, persistent=False):
    """Fail when the two engines disagree, printing both results."""
    compiled, walked = run_both(
        source, argv=argv, stdin=stdin, base_dir=base_dir, persistent=persistent,
    )
    if compiled != walked:
        raise AssertionError(
            "compiled engine and tree-walker disagree\n"
            f"compiled: {compiled!r}\n"
            f"tree-walker: {walked!r}"
        )


def _load_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".vphyx":
        text = from_vertical(text)
    return text


def _example_files():
    found = []
    for path in sorted(EXAMPLES.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if path.name.startswith("06_ask") or path.name.startswith("lib_"):
            continue
        found.append(path)
    return found


def _phyx_files():
    return sorted(PHYX_TESTS.glob("test_*.phyx"))


# Snippets. The tree-walker is the behaviour these pin.
BUG_A = """\
^ťe-a-b-dv:
    ^lo-a-b-χɬkevk-'iţpənn.
^baqilx:!"try",0-0-dv.
^qit:!"caught",dekp.
!"after".
"""

BUG_B = """\
^ťe-a-b-ad:
    ^lo-a-b-babg-'iţpənn.
^baqilx:!"try","x"-1-ad.
^qit:!"caught",dekp.
!"after".
"""

BUG_C = """\
^ťe-a-b-pw:
    ^lo-a-b-lu'f-'iţpənn.
!2-əx1-pw.
"""

BUG_D = """\
^ťe-a-b-ad:
    ^lo-a-b-babg-'iţpənn.
!əxbytp-1-ad.
"""

BUG_E = """\
^ťe-bump:
    ^y-1-babg-y-ţə''.
^0-y-ţə''.
^xe-bump.
^xe-bump.
!"y =",y.
"""

BUG_F = """\
^ťe-setit:
    ^1-y-ţə''.
^0-y-ţə''.
^xe-setit.
!"y =",y.
"""

BUG_H = """\
!əx2-2-lu'f.
"""

BUG_H_ABILITY = """\
^ťe-pw:
    ^lo-əx2-2-lu'f-'iţpənn.
!pw.
"""

BUG_I = """\
^0-y-ţə''.
^ťe-bump:
    ^y-1-babg-y-ţə''.
    ^lo-y-'iţpənn.
^ťe-go:
    ^lo-y-bump-babg-'iţpənn.
!go.
"""

BUG_I_MODULE = """\
^0-y-ţə''.
^ťe-bump:
    ^y-1-babg-y-ţə''.
    ^lo-y-'iţpənn.
!y-bump-babg.
"""


def _bench_result(treewalk: bool):
    """Outcome of ``python -m phyx bench``. Timings are not compared."""
    env = os.environ.copy()
    env.pop("PHYX_TREEWALK", None)
    if treewalk:
        env["PHYX_TREEWALK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-m", "phyx", "bench", "--size", "8", "--loops", "1000"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode == 0:
        return "ok"
    name = "Exception"
    for line in reversed((proc.stderr or "").splitlines()):
        text = line.strip()
        if not text or text.startswith("File ") or text.startswith("Traceback"):
            continue
        if ":" in text:
            name = text.split(":", 1)[0].strip()
            break
    return "PYTHON:" + name


class EngineParityTests(unittest.TestCase):
    def _parity_file(self, path: Path):
        source = _load_source(path)
        with tempfile.TemporaryDirectory() as directory:
            assertParity(source, base_dir=directory)


def _add_file_test(prefix, path: Path):
    def test(self, path=path):
        self._parity_file(path)

    test.__name__ = f"test_{prefix}_{path.stem}"
    setattr(EngineParityTests, test.__name__, test)


for _path in _example_files():
    _add_file_test("example", _path)

for _path in _phyx_files():
    _add_file_test("phyx", _path)


class EngineBugTests(unittest.TestCase):
    def test_bug_a_pure_divide_by_zero_is_catchable(self):
        self.assertEqual(
            run_both(BUG_A)[1],
            ("caught nothing can be distributed into zero parts\nafter\n", None),
        )
        assertParity(BUG_A)
        uncaught = (
            "^ťe-a-b-dv:\n"
            "    ^lo-a-b-χɬkevk-'iţpənn.\n"
            "!0-0-dv.\n"
        )
        hint = (
            "χɬkevk is floor division; the second object is the number of parts "
            "and cannot be 0"
        )
        self.assertEqual(
            run_both(uncaught)[1],
            ("", ("RuntimeFault", "nothing can be distributed into zero parts", 2, hint)),
        )
        assertParity(uncaught)

    def test_bug_b_pure_type_error_is_catchable(self):
        self.assertEqual(
            run_both(BUG_B)[1],
            ("caught cannot add rukx (text) and asərθ (number)\nafter\n", None),
        )
        assertParity(BUG_B)

    def test_bug_c_negative_power_is_a_fault(self):
        self.assertEqual(
            run_both(BUG_C)[1],
            ("", ("RuntimeFault", "lu'f (energize) cannot raise to a negative power", 2, None)),
        )
        assertParity(BUG_C)

    def test_bug_d_truth_is_not_a_number(self):
        self.assertEqual(
            run_both(BUG_D)[1],
            (
                "",
                (
                    "RuntimeFault",
                    "cannot add wija'x (truth) and asərθ (number)",
                    2,
                    "babg adds two numbers, two texts, or two lists",
                ),
            ),
        )
        assertParity(BUG_D)

    def test_pure_operators_match_on_the_other_faults(self):
        cases = [
            (
                "^ťe-a-b-op:\n    ^lo-a-b-mɒɣg-'iţpənn.\n!\"x\"-1-op.\n",
                ("", ("RuntimeFault", "'mɒɣg' needs a number, got rukx (text)", 2, None)),
            ),
            (
                "^ťe-a-b-op:\n    ^lo-a-b-mɒɣg-'iţpənn.\n!1-\"x\"-op.\n",
                ("", ("RuntimeFault", "'mɒɣg' needs a number, got rukx (text)", 2, None)),
            ),
            (
                "^ťe-a-b-op:\n    ^lo-a-b-geft-'iţpənn.\n!1-0-op.\n",
                ("", ("RuntimeFault", "nothing remains when dividing by zero", 2, None)),
            ),
            (
                "^ťe-a-h:\n    ^lo-a-əxķus'ər-'iţpənn.\n!əxbytp-h.\n",
                ("", ("RuntimeFault", "'əxķus'ər' needs a number, got wija'x (truth)", 2, None)),
            ),
            (
                "^ťe-a-b-pw:\n    ^lo-a-b-lu'f-'iţpənn.\n!2-2711-pw.\n",
                ("", ("RuntimeFault", "lu'f (energize): the exponent is too great", 2, None)),
            ),
            (
                "^ťe-a-b-m:\n    ^lo-a-b-tøwp-'iţpənn.\n!3-\"ab\"-m.\n",
                ("", ("RuntimeFault", "cannot multiply asərθ (number) and rukx (text)", 2, None)),
            ),
            (
                "^ťe-a-b-m:\n    ^lo-a-b-tøwp-'iţpənn.\n!\"ab\"-3-m.\n",
                ("ababab\n", None),
            ),
            (
                "^ťe-a-n:\n    ^lo-a-əx-'iţpənn.\n!0-n.\n!\"\"-n.\n",
                ("əxbytp\nəxbytp\n", None),
            ),
        ]
        for source, walked in cases:
            with self.subTest(source=source):
                self.assertEqual(run_both(source)[1], walked)
                assertParity(source)

    def test_condition_calls_an_ability_once_per_turn(self):
        source = (
            "^ťe-tick:\n"
            "    !\"t\".\n"
            "    ^lo-'ii-'iţpənn.\n"
            "^xe-0-i-ţə''.\n"
            "^baxuφ-i-tick-babg-3-grmɒɣg:\n"
            "    ^xe-i-1-babg-i-ţə''.\n"
        )
        self.assertEqual(run_both(source)[1], ("t\nt\nt\n", None))
        assertParity(source)

    def test_bug_h_negative_power_base(self):
        self.assertEqual(run_both(BUG_H)[1], ("4\n", None))
        assertParity(BUG_H)
        self.assertEqual(run_both(BUG_H_ABILITY)[1], ("4\n", None))
        assertParity(BUG_H_ABILITY)

    def test_bug_i_operands_left_to_right(self):
        self.assertEqual(run_both(BUG_I)[1], ("1\n", None))
        assertParity(BUG_I)

    def test_bug_i_module_operands_left_to_right(self):
        self.assertEqual(run_both(BUG_I_MODULE)[1], ("1\n", None))
        assertParity(BUG_I_MODULE)

    def test_bug_e_ability_rebinds_later_global(self):
        self.assertEqual(run_both(BUG_E)[1], ("y = 2\n", None))
        assertParity(BUG_E)

    def test_bug_f_ability_changes_later_global(self):
        self.assertEqual(run_both(BUG_F)[1], ("y = 1\n", None))
        assertParity(BUG_F)

    def test_scope_module_name_assigned_before_the_ability(self):
        source = (
            "^0-y-ţə''.\n"
            "^ťe-bump:\n"
            "    ^y-1-babg-y-ţə''.\n"
            "^xe-bump.\n"
            "!\"y =\",y.\n"
        )
        self.assertEqual(run_both(source)[1], ("y = 1\n", None))
        assertParity(source)

    def test_scope_nested_ability_rebinds_the_outer_ability(self):
        source = (
            "^ťe-outer:\n"
            "    ^ťe-inner:\n"
            "        ^y-1-babg-y-ţə''.\n"
            "    ^0-y-ţə''.\n"
            "    ^xe-inner.\n"
            "    ^lo-y-'iţpənn.\n"
            "!outer.\n"
        )
        self.assertEqual(run_both(source)[1], ("1\n", None))
        assertParity(source)

    def test_scope_loop_variable_is_rebound(self):
        source = (
            "^ťe-bump:\n"
            "    ^i-1-babg-i-ţə''.\n"
            "^1-2-2-ťewn-xs-ţə''.\n"
            "^aχəw'-i-dl-xs:\n"
            "    ^xe-bump.\n"
            "!\"i =\",i.\n"
        )
        self.assertEqual(run_both(source)[1], ("i = 3\n", None))
        assertParity(source)

    def test_scope_question_target_is_rebound(self):
        source = (
            "^ťe-setit:\n"
            "    ^\"z\"-ans-ţə''.\n"
            "?\"q \"-ans.\n"
            "^xe-setit.\n"
            "!ans.\n"
        )
        self.assertEqual(run_both(source, stdin="hi\n")[1], ("q z\n", None))
        assertParity(source, stdin="hi\n")

    def test_scope_blame_name_is_rebound_in_the_handler(self):
        source = (
            "^ťe-outer:\n"
            "    ^baqilx:\n"
            "        ^xe-\"yes\"-ɬšeɴazv.\n"
            "    ^qit:\n"
            "        ^ťe-inner:\n"
            "            ^\"no\"-dekp-ţə''.\n"
            "        ^xe-inner.\n"
            "        ^lo-dekp-'iţpənn.\n"
            "!outer.\n"
        )
        self.assertEqual(run_both(source)[1], ("no\n", None))
        assertParity(source)

    def test_scope_persistent_program_rebinds_the_module_name(self):
        self.assertEqual(run_both(BUG_E, persistent=True)[1], ("y = 2\n", None))
        assertParity(BUG_E, persistent=True)
        self.assertEqual(run_both(BUG_F, persistent=True)[1], ("y = 1\n", None))
        assertParity(BUG_F, persistent=True)

    def test_scope_persistent_sentences_share_the_binding(self):
        chunks = (
            "^0-y-ţə''.\n",
            "^ťe-bump:\n    ^y-1-babg-y-ţə''.\n",
            "^xe-bump.\n^xe-bump.\n!y.\n",
        )
        compiled = _run_chunks(chunks, treewalk=False)
        walked = _run_chunks(chunks, treewalk=True)
        self.assertEqual(walked, ("2\n", None))
        self.assertEqual(compiled, walked)

    def test_scope_name_assigned_inside_ba_is_the_module_binding(self):
        source = (
            "^ťe-setit:\n"
            "    ^1-y-ţə''.\n"
            "^ba-əxbytp:\n"
            "    ^0-y-ţə''.\n"
            "^xe-setit.\n"
            "!\"y =\",y.\n"
        )
        self.assertEqual(run_both(source)[1], ("y = 1\n", None))
        assertParity(source)

    def test_scope_skipped_assignment_does_not_bind(self):
        source = (
            "^ťe-setit:\n"
            "    ^1-y-ţə''.\n"
            "^ba-bytp:\n"
            "    ^0-y-ţə''.\n"
            "^xe-setit.\n"
            "!\"y =\",y.\n"
        )
        walked = run_both(source)[1]
        self.assertEqual(walked[0], "")
        self.assertEqual(walked[1][0], "RuntimeFault")
        self.assertIn("unknown word 'y'", walked[1][1])
        assertParity(source)

    def test_scope_fresh_local_does_not_escape_the_ability(self):
        source = (
            "^ťe-f:\n"
            "    ^1-z-ţə''.\n"
            "    ^lo-z-'iţpənn.\n"
            "!f.\n"
            "!z.\n"
        )
        walked = run_both(source)[1]
        self.assertEqual(walked[0], "1\n")
        self.assertEqual(walked[1][0], "RuntimeFault")
        self.assertIn("unknown word 'z'", walked[1][1])
        assertParity(source)

    def test_scope_parameter_is_not_the_outer_name(self):
        source = (
            "^ťe-y-f:\n"
            "    ^y-1-babg-y-ţə''.\n"
            "    ^lo-y-'iţpənn.\n"
            "^7-y-ţə''.\n"
            "!3-f.\n"
            "!y.\n"
        )
        self.assertEqual(run_both(source)[1], ("4\n7\n", None))
        assertParity(source)

    def test_scope_while_name_assigned_after_the_ability(self):
        source = (
            "^ťe-bump:\n"
            "    ^n-1-babg-n-ţə''.\n"
            "^0-n-ţə''.\n"
            "^baxuφ-n-3-grmɒɣg:\n"
            "    ^xe-bump.\n"
            "!n.\n"
        )
        self.assertEqual(run_both(source)[1], ("3\n", None))
        assertParity(source)

    def test_scope_loop_inside_an_ability(self):
        source = (
            "^ťe-f:\n"
            "    ^1-2-2-ťewn-xs-ţə''.\n"
            "    ^ťe-bump:\n"
            "        ^i-1-babg-i-ţə''.\n"
            "    ^aχəw'-i-dl-xs:\n"
            "        ^xe-bump.\n"
            "    ^lo-i-'iţpənn.\n"
            "!f.\n"
        )
        self.assertEqual(run_both(source)[1], ("3\n", None))
        assertParity(source)

    def test_handler_shares_the_enclosing_scope(self):
        # dekp is bound in the running scope and stays bound after qit.
        source = (
            "^baqilx:\n"
            "    ^xe-\"yes\"-ɬšeɴazv.\n"
            "^qit:\n"
            "    !dekp.\n"
            "!dekp.\n"
        )
        self.assertEqual(run_both(source)[1], ("yes\nyes\n", None))
        assertParity(source)

    def test_handler_name_stays_bound(self):
        source = (
            "^baqilx:\n"
            "    ^xe-\"yes\"-ɬšeɴazv.\n"
            "^qit:\n"
            "    ^1-x-ţə''.\n"
            "!x.\n"
        )
        self.assertEqual(run_both(source)[1], ("1\n", None))
        assertParity(source)

    def test_ability_defined_before_the_handler_rebinds_dekp(self):
        source = (
            "^ťe-f:\n"
            "    ^\"no\"-dekp-ţə''.\n"
            "^baqilx:\n"
            "    ^xe-\"yes\"-ɬšeɴazv.\n"
            "^qit:\n"
            "    ^xe-f.\n"
            "    !dekp.\n"
        )
        self.assertEqual(run_both(source)[1], ("no\n", None))
        assertParity(source)

    def test_handler_ability_stays_bound(self):
        source = (
            "^baqilx:\n"
            "    ^xe-\"yes\"-ɬšeɴazv.\n"
            "^qit:\n"
            "    ^ťe-f:\n"
            "        ^lo-1-'iţpənn.\n"
            "!f.\n"
        )
        self.assertEqual(run_both(source)[1], ("1\n", None))
        assertParity(source)

    def test_const_in_an_ability_shadows_an_outer_name(self):
        source = (
            "^0-y-ţə''.\n"
            "^ťe-f:\n"
            "    ^'u-1-y-ţə''.\n"
            "    ^lo-y-'iţpənn.\n"
            "!f.\n"
            "!y.\n"
        )
        self.assertEqual(run_both(source)[1], ("1\n0\n", None))
        assertParity(source)

    def test_plain_assignment_of_a_local_constant_is_a_fault(self):
        source = (
            "^ťe-f:\n"
            "    ^'u-1-y-ţə''.\n"
            "    ^2-y-ţə''.\n"
            "    ^lo-y-'iţpənn.\n"
            "!f.\n"
        )
        fault = (
            "RuntimeFault",
            "'y' was fixed in the past ('u) and cannot change",
            3,
            None,
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_const_after_a_plain_assignment_in_an_ability_is_a_fault(self):
        source = (
            "^ťe-f:\n"
            "    ^1-y-ţə''.\n"
            "    ^'u-2-y-ţə''.\n"
            "!f.\n"
        )
        fault = (
            "RuntimeFault",
            "'y' already has a value here and cannot be fixed in the past ('u)",
            3,
            None,
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_second_const_in_an_ability_is_a_fault(self):
        source = (
            "^ťe-f:\n"
            "    ^'u-1-y-ţə''.\n"
            "    ^'u-2-y-ţə''.\n"
            "!f.\n"
        )
        fault = (
            "RuntimeFault",
            "'y' already has a value here and cannot be fixed in the past ('u)",
            3,
            None,
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_const_of_a_parameter_is_a_fault(self):
        source = (
            "^ťe-y-f:\n"
            "    ^'u-1-y-ţə''.\n"
            "!3-f.\n"
        )
        fault = (
            "RuntimeFault",
            "'y' already has a value here and cannot be fixed in the past ('u)",
            2,
            None,
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_read_before_a_later_assignment_is_unknown(self):
        source = "^ťe-f:\n    !y.\n^xe-f.\n^3-y-ţə''.\n"
        fault = (
            "RuntimeFault",
            "unknown word 'y'",
            2,
            "bind it first: ^xe-VALUE-y-ţə''.  Or run `python -m phyx words` for the lexicon.",
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_read_before_assignment_at_module_level_is_unknown(self):
        source = "!y.\n^1-y-ţə''.\n"
        fault = (
            "RuntimeFault",
            "unknown word 'y'",
            1,
            "bind it first: ^xe-VALUE-y-ţə''.  Or run `python -m phyx words` for the lexicon.",
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_read_after_an_untaken_ba_is_unknown(self):
        source = "^ba-bytp:\n    ^1-y-ţə''.\n!y.\n"
        fault = (
            "RuntimeFault",
            "unknown word 'y'",
            3,
            "bind it first: ^xe-VALUE-y-ţə''.  Or run `python -m phyx words` for the lexicon.",
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_read_of_a_name_assigned_only_in_an_uncalled_ability_is_unknown(self):
        source = "^ťe-f:\n    ^1-y-ţə''.\n!y.\n"
        fault = (
            "RuntimeFault",
            "unknown word 'y'",
            3,
            "bind it first: ^xe-VALUE-y-ţə''.  Or run `python -m phyx words` for the lexicon.",
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_loop_item_after_an_empty_loop_is_unknown(self):
        source = "^aχəw'-i-dl-0-ťewn:\n    !i.\n!i.\n"
        fault = (
            "RuntimeFault",
            "unknown word 'i'",
            3,
            "did you mean 'ķi'?  python -m phyx explain ķi",
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_name_sentence_is_evaluated(self):
        source = "^xe-fbx.\n"
        fault = (
            "RuntimeFault",
            "unknown word 'fbx'",
            1,
            "bind it first: ^xe-VALUE-fbx-ţə''.  Or run `python -m phyx words` for the lexicon.",
        )
        self.assertEqual(run_both(source)[1], ("", fault))
        assertParity(source)

    def test_literal_sentence_is_evaluated(self):
        source = "^xe-1.\n!\"after\".\n"
        self.assertEqual(run_both(source)[1], ("after\n", None))
        assertParity(source)

    def test_name_sentence_inside_try_is_evaluated(self):
        source = "^baqilx:\n    ^xe-fbx.\n!\"after\".\n"
        self.assertEqual(run_both(source)[1], ("after\n", None))
        assertParity(source)

    @unittest.expectedFailure  # BUG-G: python -m phyx bench crashes with a TypeError when PHYX_TREEWALK=1.
    def test_bug_g_bench_treewalk_typeerror(self):
        compiled = _bench_result(False)
        walked = _bench_result(True)
        if compiled != walked:
            raise AssertionError(
                "compiled engine and tree-walker disagree\n"
                f"compiled: {compiled!r}\n"
                f"tree-walker: {walked!r}"
            )


if __name__ == "__main__":
    unittest.main()
