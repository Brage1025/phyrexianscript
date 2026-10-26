"""Every lexicon verb has a normative row, and each row's examples run.

The fault cell quotes message text in backticks. Those strings are the
faults the examples must raise, on both engines. A cell ``none`` has no
fault example. ``qab'`` ends the process: the helper records that as
``PYTHON:SystemExit`` (the CLI turns the number into the status and
prints nothing).

``'uɬč`` with a bound above 1 is chosen by the run. The engines need not
draw the same integer. ``test_astray_draw_stays_inside_its_bound`` checks
bound 1, and that a larger draw lies in ``[0, n)`` on each engine.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from phyx.vocabulary import VERBS

try:
    from test_engine_parity import assertParity, run_both
except ImportError:  # ``python -m unittest tests.test_spec_verbs``
    from tests.test_engine_parity import assertParity, run_both

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "spec.md"
REFERENCE = ROOT / "docs" / "reference.md"

_HEADING = "### Standard verbs"
_NEXT = "\n## 6. Modules"


def _section() -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(_HEADING)
    end = text.index(_NEXT, start)
    return text[start:end]


def _rows() -> dict[str, str]:
    found = {}
    for line in _section().splitlines():
        if not line.startswith("| `"):
            continue
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        word = cells[0].strip("`")
        if len(cells) != 4:
            raise AssertionError(f"{word} has {len(cells)} cells, expected 4")
        found[word] = cells[3]
    return found


def _quoted(cell: str) -> list[str]:
    return re.findall(r"`([^`]*)`", cell)


def _run(case: dict) -> None:
    kwargs = {"stdin": case.get("stdin", ""), "argv": case.get("argv")}
    needs_dir = "files" in case or "check" in case or case.get("isolated")
    if not needs_dir:
        _expect(case, kwargs)
        return
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        for name, data in case.get("files", {}).items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(data, bytes):
                path.write_bytes(data)
            else:
                path.write_text(data, encoding="utf-8", newline="\n")
        _expect(case, {**kwargs, "base_dir": folder})
        if "check" in case and "fault" not in case:
            relative, text = case["check"]
            got = (folder / relative).read_text(encoding="utf-8")
            if got != text:
                raise AssertionError(f"{relative}: {got!r} != {text!r}")


def _expect(case: dict, kwargs: dict) -> None:
    source = case["source"]
    assertParity(source, **kwargs)
    compiled, _walked = run_both(source, **kwargs)
    stdout, fault = compiled
    if "fault" in case:
        if not isinstance(fault, tuple) or fault[0] != case["kind"] or fault[1] != case["fault"]:
            raise AssertionError(f"expected {case['kind']} {case['fault']!r}, got {fault!r}")
        return
    if case.get("exit"):
        if stdout != "" or fault != "PYTHON:SystemExit":
            raise AssertionError(f"expected a bare SystemExit, got {(stdout, fault)!r}")
        return
    if fault is not None or stdout != case["stdout"]:
        raise AssertionError(f"expected {case['stdout']!r}, got {(stdout, fault)!r}")


# verb -> examples. One success (no "fault") and, when the row quotes
# messages, one example per quoted message.
CASES: dict[str, list[dict]] = {
    "babg": [
        {"source": '!0a-1-babg,"a"-"b"-babg,1-1-ťewn-2-1-ťewn-babg.', "stdout": "0b ab 1-2-2-ťewn\n"},
        {"source": '!1-"a"-babg.', "fault": "cannot add asərθ (number) and rukx (text)", "kind": "RuntimeFault"},
    ],
    "mɒɣg": [
        {"source": "!0a-3-mɒɣg.", "stdout": "7\n"},
        {"source": '!"a"-1-mɒɣg.', "fault": "'mɒɣg' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "tøwp": [
        {
            "source": '!3-4-tøwp.\n!"ab"-3-tøwp.\n!"ab"-əx1-tøwp.\n!1-2-2-ťewn-2-tøwp.',
            "stdout": "0c\nababab\n\n1-2-1-2-4-ťewn\n",
        },
        {"source": '!"a"-"b"-tøwp.', "fault": "cannot multiply rukx (text) and rukx (text)", "kind": "RuntimeFault"},
        {"source": '!"x"-100001-tøwp.', "fault": "tøwp (times): the repetition is too great", "kind": "RuntimeFault"},
    ],
    "χɬkevk": [
        {"source": "!7-2-χɬkevk,əx7-2-χɬkevk,7-əx2-χɬkevk,əx7-əx2-χɬkevk.", "stdout": "3 əx4 əx4 3\n"},
        {"source": "!1-0-χɬkevk.", "fault": "nothing can be distributed into zero parts", "kind": "RuntimeFault"},
        {"source": '!"a"-1-χɬkevk.', "fault": "'χɬkevk' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "geft": [
        {"source": "!7-2-geft,əx7-2-geft,7-əx2-geft,əx7-əx2-geft.", "stdout": "1 1 əx1 əx1\n"},
        {"source": "!1-0-geft.", "fault": "nothing remains when dividing by zero", "kind": "RuntimeFault"},
        {"source": '!"a"-1-geft.', "fault": "'geft' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "ķus'ər": [
        {"source": "!5-ķus'ər,əx5-ķus'ər.", "stdout": "0a əx0a\n"},
        {"source": '!"a"-ķus\'ər.', "fault": "'ķus'ər' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "əxķus'ər": [
        {"source": "!5-əxķus'ər,əx5-əxķus'ər.", "stdout": "2 əx3\n"},
        {"source": '!"a"-əxķus\'ər.', "fault": "'əxķus'ər' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "lu'f": [
        {"source": "!2-8-lu'f,0-0-lu'f,1-2710-lu'f.", "stdout": "100 1 1\n"},
        {"source": "!2-əx1-lu'f.", "fault": "lu'f (energize) cannot raise to a negative power", "kind": "RuntimeFault"},
        {"source": "!2-2711-lu'f.", "fault": "lu'f (energize): the exponent is too great", "kind": "RuntimeFault"},
        {"source": '!"a"-1-lu\'f.', "fault": "'lu'f' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "'uɬč": [
        {"source": "!1-'uɬč.", "stdout": "0\n"},
        {"source": "!0-'uɬč.", "fault": "'uɬč (astray) needs a bound greater than zero", "kind": "RuntimeFault"},
        {"source": "!əx1-'uɬč.", "fault": "'uɬč (astray) needs a bound greater than zero", "kind": "RuntimeFault"},
        {"source": '!"a"-\'uɬč.', "fault": "''uɬč' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "ǆ'ynpp": [
        {"source": "!1-1-ǆ'ynpp,1-2-ǆ'ynpp,1-əxbytp-ǆ'ynpp.", "stdout": "əxbytp bytp bytp\n"},
    ],
    "grmɒɣg": [
        {"source": '!1-2-grmɒɣg,2-1-grmɒɣg,"a"-"b"-grmɒɣg.', "stdout": "əxbytp bytp əxbytp\n"},
        {"source": '!"a"-1-grmɒɣg.', "fault": "'grmɒɣg' cannot order rukx (text) and asərθ (number)", "kind": "RuntimeFault"},
    ],
    "korxgr": [
        {"source": "!2-1-korxgr.", "stdout": "əxbytp\n"},
        {
            "source": "!1-0-ťewn-korxgr.",
            "fault": "'korxgr' cannot order asərθ (number) and ťewn (list)",
            "kind": "RuntimeFault",
        },
    ],
    "əx": [
        {"source": '!0-əx,1-əx,""-əx,"a"-əx.', "stdout": "əxbytp bytp əxbytp bytp\n"},
    ],
    "xə": [
        {"source": "!1-0-xə,1-2-xə.", "stdout": "bytp əxbytp\n"},
    ],
    "ðə": [
        {"source": "!0-0-ðə,0-1-ðə.", "stdout": "bytp əxbytp\n"},
    ],
    "ʁšθakɴ": [
        {"source": '!0-"a"-"b"-ʁšθakɴ,1-"a"-"b"-ʁšθakɴ.', "stdout": "b a\n"},
    ],
    "ţə''": [
        {"source": "^xe-1-2-2-ťewn-l-ţə''.\n!9-l-0-tapq-ţə''.\n!l.", "stdout": "9\n9-2-2-ťewn\n"},
        {"source": "!1-2-ţə''.", "fault": "the target of ţə'' (put) must be a name or a 'tapq' place", "kind": "ParseError"},
        {
            "source": '!9-"ab"-0-tapq-ţə\'\'.',
            "fault": "text cannot be changed in place; build a new text instead",
            "kind": "RuntimeFault",
        },
        {"source": "!9-1-0-tapq-ţə''.", "fault": "cannot put into asərθ (number)", "kind": "RuntimeFault"},
        {"source": "!9-1-1-ťewn-5-tapq-ţə''.", "fault": "the list has 1 items; there is no item 5", "kind": "RuntimeFault"},
        {
            "source": "^'u-1-x-ţə''.\n^xe-2-x-ţə''.",
            "fault": "'x' was fixed in the past ('u) and cannot change",
            "kind": "RuntimeFault",
        },
        {
            "source": "^xe-1-x-ţə''.\n^'u-2-x-ţə''.",
            "fault": "'x' already has a value here and cannot be fixed in the past ('u)",
            "kind": "RuntimeFault",
        },
        {
            "source": '^xe-0-tekt-b-ţə\'\'.\n^xe-1-b-0-ťewn-tapq-ţə\'\'.',
            "fault": "a book cannot be keyed by a list ('ţə''')",
            "kind": "RuntimeFault",
        },
    ],
    "pihš": [
        {"source": "!1-pihš.", "stdout": "1\n1\n"},
    ],
    "krepg": [
        {"source": '!"a"-krepg.', "stdout": '"a"\na\n'},
    ],
    "'ətsxn": [
        {"source": '!"q "- \'ətsxn.', "stdin": "42\n", "stdout": "q 42\n"},
        {"source": '!""-\'ətsxn.', "stdin": "", "stdout": "əixiww\n"},
    ],
    "asərθ": [
        {"source": '!"ff"-asərθ,əxbytp-asərθ,bytp-asərθ," 0a "-asərθ.', "stdout": "0ff 1 0 0a\n"},
        {"source": '!"xyz"-asərθ.', "fault": "'xyz' is not a hexadecimal numeral", "kind": "RuntimeFault"},
        {"source": "!0-ťewn-asərθ.", "fault": "cannot turn ťewn (list) into a number", "kind": "RuntimeFault"},
    ],
    "xušv": [
        {"source": "!0a-xušv.", "stdout": "0a\n"},
    ],
    "πøkk": [
        {
            "source": '!1-πøkk,""-πøkk,bytp-πøkk,əixiww-πøkk,0-ťewn-πøkk,0-tekt-πøkk.',
            "stdout": "asərθ rukx wija'x əixiww ťewn tekt\n",
        },
        {"source": "^ťe-f:\n    ^lo-1-'iţpənn.\n!f-naķm-πøkk.", "stdout": "ɣwi't\n"},
    ],
    "ťewn": [
        {"source": "!1-2-3-3-ťewn,0-ťewn.", "stdout": "1-2-3-3-ťewn 0-ťewn\n"},
        {
            "source": "!əx1-ťewn.",
            "fault": "'ťewn' (list) must be preceded by a plain numeral giving how many items to gather",
            "kind": "ParseError",
        },
        {
            "source": "!1-ťewn.",
            "fault": (
                "'ťewn' (list) wants 1 item before the count 1, but only 0 are there. Write the items"
                " first, then the count, then ťewn (empty: 0-ťewn)"
            ),
            "kind": "ParseError",
        },
    ],
    "tekt": [
        {"source": '!"a"-1-"b"-2-2-tekt.', "stdout": '"a"-1-"b"-2-2-tekt\n'},
        {"source": '!"a"-1-"a"-2-2-tekt.', "stdout": '"a"-2-1-tekt\n'},
        {"source": "!əxbytp-5-1-9-2-tekt.", "stdout": "əxbytp-5-1-9-2-tekt\n"},
        {
            "source": "!əx1-tekt.",
            "fault": "'tekt' (book) must be preceded by a plain numeral giving how many items to gather",
            "kind": "ParseError",
        },
        {
            "source": "!1-tekt.",
            "fault": (
                "'tekt' (book) wants 1 entry (key and value each) before the count 1, but only 0 are"
                " there. Write the items first, then the count, then tekt (empty: 0-tekt)"
            ),
            "kind": "ParseError",
        },
        {"source": "!0-ťewn-1-1-tekt.", "fault": "a book cannot be keyed by a list ('tekt')", "kind": "RuntimeFault"},
    ],
    "ronɣ": [
        {"source": "!3-ronɣ,0-ronɣ,əx3-ronɣ.", "stdout": "0-1-2-3-ťewn 0-ťewn 0-ťewn\n"},
        {"source": '!"a"-ronɣ.', "fault": "'ronɣ' needs a number, got rukx (text)", "kind": "RuntimeFault"},
        {"source": "!100001-ronɣ.", "fault": "ronɣ (turns): the count is too great", "kind": "RuntimeFault"},
    ],
    "tapq": [
        {"source": '!1-2-3-3-ťewn-0-tapq,1-2-3-3-ťewn-əx1-tapq,"abc"-1-tapq.', "stdout": "1 3 b\n"},
        {
            "source": "!əxbytp-5-1-9-2-tekt-1-tapq,əxbytp-5-1-9-2-tekt-əxbytp-tapq.",
            "stdout": "9 5\n",
        },
        {"source": '!0-tekt-"k"-tapq.', "fault": 'the book has no entry "k"', "kind": "RuntimeFault"},
        {
            "source": '!"ab"-"a"-tapq.',
            "fault": "'tapq' needs a number to pick from a text, got rukx (text)",
            "kind": "RuntimeFault",
        },
        {"source": "!1-1-ťewn-5-tapq.", "fault": "the list has 1 items; there is no item 5", "kind": "RuntimeFault"},
        {"source": '!"ab"-5-tapq.', "fault": "the text has 2 items; there is no item 5", "kind": "RuntimeFault"},
        {"source": '!"a"-1-1-tekt-0-ťewn-tapq.', "fault": "a book cannot be keyed by a list ('tapq')", "kind": "RuntimeFault"},
        {"source": "!1-0-tapq.", "fault": "cannot get from asərθ (number)", "kind": "RuntimeFault"},
    ],
    "bɬølπ": [
        {"source": "^xe-1-1-ťewn-l-ţə''.\n!l-2-bɬølπ.", "stdout": "1-2-2-ťewn\n"},
        {"source": "!1-2-bɬølπ.", "fault": "'bɬølπ' needs a list, got asərθ (number)", "kind": "RuntimeFault"},
    ],
    "čxət'": [
        {"source": "^xe-1-2-3-3-ťewn-l-ţə''.\n!l-əx1-čxət'.\n!l.", "stdout": "3\n1-2-2-ťewn\n"},
        {
            "source": "^xe-əxbytp-5-1-9-2-tekt-b-ţə''.\n!b-1-čxət'.\n!b.",
            "stdout": "9\nəxbytp-5-1-tekt\n",
        },
        {"source": "!0-ťewn-0-čxət'.", "fault": "the list has 0 items; there is no item 0", "kind": "RuntimeFault"},
        {"source": '!0-tekt-"k"-čxət\'.', "fault": 'the book has no entry "k"', "kind": "RuntimeFault"},
        {
            "source": '!"a"-1-1-tekt-0-ťewn-čxət\'.',
            "fault": "a book cannot be keyed by a list ('čxət'')",
            "kind": "RuntimeFault",
        },
        {"source": '!"ab"-0-čxət\'.', "fault": "cannot exile from rukx (text)", "kind": "RuntimeFault"},
    ],
    "'iixtfu'q": [
        {"source": '!1-2-2-ťewn-\'iixtfu\'q,"ab"-\'iixtfu\'q.', "stdout": "1 a\n"},
        {"source": "!0-ťewn-'iixtfu'q.", "fault": "an empty list has no beginning", "kind": "RuntimeFault"},
        {"source": "!1-'iixtfu'q.", "fault": "asərθ (number) has no beginning", "kind": "RuntimeFault"},
    ],
    "ǩeǆylqitsodrm": [
        {"source": '!1-2-2-ťewn-ǩeǆylqitsodrm,"ab"-ǩeǆylqitsodrm.', "stdout": "2 b\n"},
        {"source": "!0-ťewn-ǩeǆylqitsodrm.", "fault": "an empty list has no bottom", "kind": "RuntimeFault"},
        {"source": "!1-ǩeǆylqitsodrm.", "fault": "asərθ (number) has no bottom", "kind": "RuntimeFault"},
    ],
    "samk": [
        {"source": '!1-2-2-ťewn-samk,"ab"-samk,0-tekt-samk.', "stdout": "2 2 0\n"},
        {"source": "!1-samk.", "fault": "asərθ (number) has no length", "kind": "RuntimeFault"},
    ],
    "dl": [
        {"source": '!"a"-"a"-1-1-tekt-dl,""-""-dl,2-1-2-2-ťewn-dl.', "stdout": "əxbytp əxbytp əxbytp\n"},
        {
            "source": "!1-1-5-1-tekt-dl,əxbytp-1-5-1-tekt-dl,əxbytp-əxbytp-5-1-tekt-dl,1-əxbytp-5-1-tekt-dl.",
            "stdout": "əxbytp bytp əxbytp bytp\n",
        },
        {
            "source": '!1-"hello"-dl.',
            "fault": "only text can be found inside text, not asərθ (number)",
            "kind": "RuntimeFault",
        },
        {"source": '!0-ťewn-"a"-1-1-tekt-dl.', "fault": "a book cannot be keyed by a list ('dl')", "kind": "RuntimeFault"},
        {"source": "!1-2-dl.", "fault": "nothing can be inside asərθ (number)", "kind": "RuntimeFault"},
    ],
    "rukxtekt": [
        {"source": '!"a"-1-"b"-2-2-tekt-rukxtekt.', "stdout": '"a"-"b"-2-ťewn\n'},
        {"source": "!0-ťewn-rukxtekt.", "fault": "'rukxtekt' needs a book, got ťewn (list)", "kind": "RuntimeFault"},
    ],
    "tluxt": [
        {
            "source": "^xe-1-1-ťewn-1-ťewn-l-ţə''.\n^xe-l-tluxt-c-ţə''.\n^xe-9-c-0-tapq-0-tapq-ţə''.\n!l,c.",
            "stdout": "9-1-ťewn-1-ťewn 9-1-ťewn-1-ťewn\n",
        },
    ],
    "ɣɒzɢ": [
        {"source": '!"hello"-1-3-ɣɒzɢ,"hello"-əixiww-2-ɣɒzɢ,1-2-3-4-4-ťewn-1-3-ɣɒzɢ.', "stdout": "el he 2-3-2-ťewn\n"},
        {"source": "!1-0-1-ɣɒzɢ.", "fault": "cannot flay asərθ (number)", "kind": "RuntimeFault"},
        {"source": '!"ab"-"x"-1-ɣɒzɢ.', "fault": "'ɣɒzɢ' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "pən'g": [
        {"source": '!"a,b,"-","-pən\'g,"abc"-""-pən\'g.', "stdout": '"a"-"b"-""-3-ťewn "a"-"b"-"c"-3-ťewn\n'},
        {
            "source": '!1-","-pən\'g.',
            "fault": "'pən'g' breaks text with text, got asərθ (number) and rukx (text)",
            "kind": "RuntimeFault",
        },
    ],
    "raφoj": [
        {"source": '!"a"-"b"-2-ťewn-"|"-raφoj,1-2-2-ťewn-"-"-raφoj.', "stdout": "a|b 1-2\n"},
        {"source": "!0-ťewn-1-raφoj.", "fault": "'raφoj' links with text, got asərθ (number)", "kind": "RuntimeFault"},
        {"source": '!"ab"-","-raφoj.', "fault": "'raφoj' needs a list, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "'iţpənn": [
        {"source": "^ťe-n-f:\n    ^lo-n-1-babg-'iţpənn.\n!3-f.", "stdout": "4\n"},
        {"source": "^ťe-g:\n    ^lo-'iţpənn.\n!g.", "stdout": "əixiww\n"},
        {"source": "^lo-1-'iţpənn.", "fault": "'iţpənn (return) used outside of an ability", "kind": "ParseError"},
    ],
    "lups": [
        {
            "source": "^xe-0-i-ţə''.\n^baxuφ-əxbytp:\n    ^xe-i-1-babg-i-ţə''.\n    ^ba-i-3-korxgr:lo-lups.\n    !i.",
            "stdout": "1\n2\n3\n",
        },
        {"source": "^lo-lups.", "fault": "lups (stop) used outside of a loop", "kind": "ParseError"},
    ],
    "ɢnagɮ": [
        {"source": "^aχəw'-i-dl-3-ronɣ:\n    ^ba-i-1-ǆ'ynpp:lo-ɢnagɮ.\n    !i.", "stdout": "0\n2\n"},
        {"source": "^lo-ɢnagɮ.", "fault": "ɢnagɮ (next) used outside of a loop", "kind": "ParseError"},
    ],
    "ɬšeɴazv": [
        {"source": '^baqilx:\n    ^xe-"bad"-ɬšeɴazv.\n^qit:\n    !dekp.\n', "stdout": "bad\n"},
        {"source": '^xe-"bad"-ɬšeɴazv.', "fault": "bad", "kind": "UserMistake"},
        {"source": "^xe-0a-ɬšeɴazv.", "fault": "0a", "kind": "UserMistake"},
        {"source": "^xe-1-2-2-ťewn-ɬšeɴazv.", "fault": "1-2-2-ťewn", "kind": "UserMistake"},
    ],
    "qab'": [
        {"source": "^lo-3-qab'.", "exit": True},
        {"source": '!"x"-qab\'.', "fault": "'qab'' needs a number, got rukx (text)", "kind": "RuntimeFault"},
    ],
    "bukð": [
        {"source": '!"ok.phyx"-bukð.', "stdout": "from-cast\nəixiww\n", "files": {"ok.phyx": '!"from-cast".\n'}},
        {
            "source": "^lo-1-bukð.",
            "fault": "'bukð' (play/cast) wants a path as text, got asərθ (number)",
            "kind": "RuntimeFault",
        },
        {
            "source": '^lo-"nope-probe.phyx"-bukð.',
            "isolated": True,
            "fault": "bukð (play/cast): no such text 'nope-probe.phyx'",
            "kind": "RuntimeFault",
        },
        {
            "source": '^lo-"bad.phyx"-bukð.',
            "files": {"bad.phyx": b"\xff"},
            "fault": (
                "bukð (play/cast) cannot read 'bad.phyx': "
                "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
            ),
            "kind": "RuntimeFault",
        },
        {
            "source": '^lo-"a.phyx"-bukð.',
            "files": {"a.phyx": '^lo-"b.phyx"-bukð.\n', "b.phyx": '^lo-"a.phyx"-bukð.\n'},
            "fault": "bukð (play/cast): 'a.phyx' is already being cast (cycle)",
            "kind": "ParseError",
        },
        {
            "source": '^lo-"c.phyx"-bukð.',
            "files": {"c.phyx": '^xe-"d.phyx"-p-ţə\'\'.\n^lo-p-bukð.\n', "d.phyx": '^lo-"c.phyx"-bukð.\n'},
            "fault": "bukð (play/cast): 'c.phyx' is already being cast (cycle)",
            "kind": "RuntimeFault",
        },
    ],
    "čtəčpliɣn": [
        {"source": "^ťe-a-b-add:\n    ^lo-a-b-babg-'iţpənn.\n!3-4-2-ťewn-add-naķm-čtəčpliɣn.", "stdout": "7\n"},
        {
            "source": "!0-ťewn-1-čtəčpliɣn.",
            "fault": "'čtəčpliɣn' (activate) wants an ability, got asərθ (number)",
            "kind": "RuntimeFault",
        },
        {
            "source": "^ťe-a-id:\n    ^lo-a-'iţpənn.\n!1-id-naķm-čtəčpliɣn.",
            "fault": "'čtəčpliɣn' wants a list of objects before the ability, got asərθ (number)",
            "kind": "RuntimeFault",
        },
        {
            "source": "^ťe-a-b-add:\n    ^lo-a-b-babg-'iţpənn.\n!1-1-ťewn-add-naķm-čtəčpliɣn.",
            "fault": "'add' wants 2 objects, this list has 1",
            "kind": "RuntimeFault",
        },
    ],
    "naķm": [
        {"source": "^ťe-f:\n    ^lo-1-'iţpənn.\n!f-naķm.", "stdout": "naķmf\n"},
        {"source": "!1-naķm.", "fault": "'naķm' (work) wants an ability, got asərθ (number)", "kind": "RuntimeFault"},
    ],
    "'uxq": [
        {"source": "!'uxq.", "argv": ["red", "blue"], "stdout": '"red"-"blue"-2-ťewn\n'},
        {"source": "!'uxq.", "stdout": "0-ťewn\n"},
    ],
    "brøtjt": [
        {"source": '!"note.rukx"-brøtjt.', "stdout": "hello\n", "files": {"note.rukx": "hello"}},
        {
            "source": "!1-brøtjt.",
            "fault": "'brøtjt' (research) wants a path as text, got asərθ (number)",
            "kind": "RuntimeFault",
        },
        {
            "source": '!"missing-probe.rukx"-brøtjt.',
            "isolated": True,
            "fault": "brøtjt (research) cannot read 'missing-probe.rukx'",
            "kind": "RuntimeFault",
        },
        {
            "source": '!"bad.phyx"-brøtjt.',
            "files": {"bad.phyx": b"\xff"},
            "fault": (
                "brøtjt (research) cannot read 'bad.phyx': "
                "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
            ),
            "kind": "RuntimeFault",
        },
    ],
    "mɴyrx": [
        {"source": '!"hi"-"n.rukx"-mɴyrx.', "stdout": "hi\n", "check": ("n.rukx", "hi")},
        {"source": '^lo-"z"-"sub/n.rukx"-mɴyrx.', "stdout": "", "check": ("sub/n.rukx", "z")},
        {
            "source": "!1-2-mɴyrx.",
            "fault": "'mɴyrx' (spread) writes text onto a path, got asərθ (number) and asərθ (number)",
            "kind": "RuntimeFault",
        },
        {
            "source": "^lo-\"\ud800\"-\"out.rukx\"-mɴyrx.",
            "fault": (
                "mɴyrx (spread) cannot write 'out.rukx': 'utf-8' codec can't encode "
                "character '\\ud800' in position 0: surrogates not allowed"
            ),
            "kind": "RuntimeFault",
            "isolated": True,
        },
    ],
}


class SpecVerbTests(unittest.TestCase):
    def test_every_verb_has_a_row_and_the_examples_agree(self):
        rows = _rows()
        self.assertEqual(set(rows), set(VERBS), sorted(set(VERBS) ^ set(rows)))
        self.assertEqual(set(CASES), set(VERBS), sorted(set(VERBS) ^ set(CASES)))
        section = _section()
        self.assertIn("`this value is nested too deeply`", section)
        self.assertIn("`the program ran out of memory`", section)
        for word in VERBS:
            cell = rows[word]
            cases = CASES[word]
            produced = [case["fault"] for case in cases if "fault" in case]
            documented = _quoted(cell)
            if cell == "none":
                self.assertEqual(documented, [], word)
                self.assertEqual(produced, [], word)
            else:
                self.assertEqual(set(produced), set(documented), word)
            self.assertTrue(any("fault" not in case for case in cases), word)
            for case in cases:
                with self.subTest(verb=word, source=case["source"].split("\n", 1)[0]):
                    _run(case)

    def test_reference_points_at_this_subsection(self):
        self.assertIn(_HEADING, SPEC.read_text(encoding="utf-8"))
        text = REFERENCE.read_text(encoding="utf-8")
        self.assertIn("[spec.md](spec.md#standard-verbs)", text)
        self.assertTrue((ROOT / "docs" / "spec.md").is_file())

    def test_astray_draw_stays_inside_its_bound(self):
        # Bound 1 has one legal draw. A wider bound is some integer in
        # [0, n) on each engine; the two draws are not required to match.
        assertParity("!1-'uɬč.")
        compiled, walked = run_both("!1-'uɬč.")
        self.assertEqual(compiled, ("0\n", None))
        self.assertEqual(walked, ("0\n", None))
        compiled, walked = run_both("!100-'uɬč.")
        for label, result in (("compiled", compiled), ("tree-walker", walked)):
            stdout, fault = result
            self.assertIsNone(fault, label)
            text = stdout.removesuffix("\n")
            self.assertTrue(text, label)
            self.assertTrue(all(c in "0123456789abcdef" for c in text), text)
            drawn = int(text, 16)
            self.assertGreaterEqual(drawn, 0, label)
            self.assertLess(drawn, 0x100, label)


if __name__ == "__main__":
    unittest.main()
