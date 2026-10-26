"""Random φyrx programs must agree on both engines.

The default run executes 300 programs from a fixed list of seeds. Set
``PHYX_FUZZ`` to a positive integer to run that many programs from fresh
seeds instead; a failure prints the seed and the program.

A fault is ``(class name, message, line, hint)``, the same record as
``tests.test_engine_parity._run_one``. ``qab'`` is an exit status, not a
fault: ``0`` when the program finishes, ``1`` when a Phyrexian fault
stops it, or the number ``qab'`` carries. Both engines share one random
seed, so ``'uɬč`` is comparable.

Every program is finite: loops are counted, recursion counts down, and
each run has a timeout.
"""

from __future__ import annotations

import io
import os
import random
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass
from pathlib import Path

from phyx.conjugation import lemma_of
from phyx.errors import PhyrexianError, RuntimeFault, format_error
from phyx.interpreter import Interpreter, run_source
from phyx.lexer import tokenize
from phyx.limits import MIN_RECURSION, _interrupt_thread
from phyx.parser import parse
from phyx.vocabulary import MARKERS, RESERVED, VERBS

try:
    from test_engine_parity import assertParity, run_both
except ImportError:  # ``python -m unittest tests.test_parity_fuzz``
    from tests.test_engine_parity import assertParity, run_both


# Documented host ceiling is 16384. A small value still has to clear the
# documented minimum, and a depth-2 ability stays under both engines there.
_SMALL_RECURSION = 256
_DEFAULT_SEEDS = tuple(range(300))
_TIMEOUT_S = 1.0
_ARGV = ("red", "blue")
_STDIN = "norn\nmore\nthird\nfourth\n"

# Mood words, plus the two sentence openers that are not markers.
STATEMENT_KINDS = (
    "xe",
    "lo",
    "'u",
    "ba",
    "bu",
    "əx",
    "qit",
    "baxuφ",
    "aχəw'",
    "ťe",
    "ǩaπa",
    "baqilx",
    "!",
    "?",
)

_NAMES = (
    "alfa",
    "bravo",
    "carlo",
    "delta",
    "echo",
    "foxt",
    "golf",
    "hotel",
)
_SYLLABLES = (
    "ba", "be", "bi", "bo", "bu",
    "ka", "ke", "ki", "ko", "ku",
    "ma", "me", "mi", "mo", "mu",
    "ra", "re", "ri", "ro", "ru",
    "sa", "se", "si", "so", "su",
)
_VERB_WORDS = tuple(VERBS)


def _usable(name: str) -> bool:
    return bool(name) and name.isalpha() and name not in RESERVED and lemma_of(name) is None


for _name in _NAMES + ("item", "kount", "ret", "kept", "bump", "down", "brought", "inner", "outer"):
    if not _usable(_name):
        raise RuntimeError(f"{_name} cannot be a generated name")


def hx(number: int) -> str:
    """Hex literal. A numeral has to start with a digit, so ``10`` is ``0a``."""
    if number < 0:
        return "əx" + hx(-number)
    text = format(number, "x")
    if text[0] not in "0123456789":
        text = "0" + text
    return text


def _exit_status(err: SystemExit) -> int:
    code = err.code
    if code is None:
        return 0
    if isinstance(code, int) and not isinstance(code, bool):
        return code
    return 1


@dataclass
class Case:
    seed: int
    source: str
    chunks: tuple[str, ...] | None = None
    recursion: int | None = None

    def texts(self) -> tuple[str, ...]:
        if self.chunks:
            return self.chunks
        return (self.source,)


@dataclass
class Outcome:
    stdout: str
    fault: tuple | str | None
    exit_code: int


def observe(
    source: str,
    *,
    treewalk: bool,
    seed: int,
    base_dir: Path,
    argv: tuple[str, ...] = _ARGV,
    stdin: str = _STDIN,
    persistent: bool = False,
    known: dict[str, int] | None = None,
) -> Outcome:
    """Run one source. The fault record matches ``_run_one``."""
    out = io.StringIO()
    fault = None
    exit_code = 0
    try:
        program = parse(source, base_dir=base_dir, known_functions=known)
        Interpreter(
            stdout=out,
            stdin=io.StringIO(stdin),
            argv=list(argv),
            base_dir=base_dir,
            persistent=persistent,
            treewalk=treewalk,
            seed=seed,
        ).run(program)
    except PhyrexianError as err:
        fault = (type(err).__name__, err.message, err.line, err.hint)
        exit_code = 1
    except SystemExit as err:
        exit_code = _exit_status(err)
    except KeyboardInterrupt:
        raise
    except BaseException as err:
        fault = "PYTHON:" + type(err).__name__
        exit_code = 1
    return Outcome(out.getvalue(), fault, exit_code)


def observe_chunks(
    chunks: tuple[str, ...],
    *,
    treewalk: bool,
    seed: int,
    base_dir: Path,
) -> Outcome:
    """Several programs on one persistent interpreter, as ``_run_chunks`` does."""
    out = io.StringIO()
    fault = None
    exit_code = 0
    interp = Interpreter(
        stdout=out,
        stdin=io.StringIO(_STDIN),
        argv=list(_ARGV),
        base_dir=base_dir,
        persistent=True,
        treewalk=treewalk,
        seed=seed,
    )
    try:
        for source in chunks:
            program = parse(
                source,
                base_dir=base_dir,
                known_functions=interp.known_functions(),
            )
            interp.run(program)
    except PhyrexianError as err:
        fault = (type(err).__name__, err.message, err.line, err.hint)
        exit_code = 1
    except SystemExit as err:
        exit_code = _exit_status(err)
    except KeyboardInterrupt:
        raise
    except BaseException as err:
        fault = "PYTHON:" + type(err).__name__
        exit_code = 1
    return Outcome(out.getvalue(), fault, exit_code)


def _run_case(case: Case, *, treewalk: bool, base_dir: Path) -> Outcome:
    if case.chunks:
        return observe_chunks(case.chunks, treewalk=treewalk, seed=case.seed, base_dir=base_dir)
    return observe(case.source, treewalk=treewalk, seed=case.seed, base_dir=base_dir)


def _with_timeout(fn, label: str):
    box: dict = {}

    def work() -> None:
        try:
            box["value"] = fn()
        except BaseException as err:  # noqa: BLE001 - handed back to the caller
            box["err"] = err

    thread = threading.Thread(target=work, name="phyx-fuzz", daemon=True)
    thread.start()
    thread.join(_TIMEOUT_S)
    timed_out = False
    if thread.is_alive():
        timed_out = True
        _interrupt_thread(thread)
        thread.join(1.0)
    if "err" in box:
        err = box["err"]
        if timed_out and isinstance(err, KeyboardInterrupt):
            raise TimeoutError(label)
        raise err
    if timed_out:
        raise TimeoutError(label)
    return box["value"]


def run_case(case: Case, base_dir: Path) -> tuple[Outcome, Outcome]:
    """Both engines, with ``PHYX_RECURSION`` set only for this case."""
    previous = os.environ.get("PHYX_RECURSION")
    if case.recursion is not None:
        os.environ["PHYX_RECURSION"] = str(case.recursion)
    try:
        return _with_timeout(
            lambda: (
                _run_case(case, treewalk=False, base_dir=base_dir),
                _run_case(case, treewalk=True, base_dir=base_dir),
            ),
            f"seed {case.seed}",
        )
    finally:
        if case.recursion is not None:
            if previous is None:
                os.environ.pop("PHYX_RECURSION", None)
            else:
                os.environ["PHYX_RECURSION"] = previous


def _pair_differs(source: str, *, seed: int, base_dir: Path, recursion: int | None) -> bool:
    case = Case(seed, source, recursion=recursion)
    try:
        compiled, walked = run_case(case, base_dir)
    except TimeoutError:
        return False
    return _as_tuple(compiled) != _as_tuple(walked)


def reduce_program(source: str, still_bad) -> str:
    """Delete lines while ``still_bad`` still reports a disagreement.

    ``still_bad`` takes the candidate source and returns true when the
    engines still differ. A candidate that hangs is kept out.
    """
    lines = source.splitlines()
    for _ in range(40):
        removed = False
        index = 0
        while index < len(lines):
            trial = lines[:index] + lines[index + 1:]
            text = "\n".join(trial).strip()
            if text and still_bad(text + "\n"):
                lines = trial
                removed = True
            else:
                index += 1
        if not removed:
            break
    body = "\n".join(lines).strip()
    return (body + "\n") if body else ""


def _as_tuple(outcome: Outcome) -> tuple:
    return (outcome.stdout, outcome.fault, outcome.exit_code)


def _fault_kind(outcome: Outcome) -> str:
    if isinstance(outcome.fault, str):
        return outcome.fault
    if outcome.fault is not None:
        return outcome.fault[0]
    if outcome.exit_code != 0:
        return "exit"
    return "ok"


def _raw_python(outcome: Outcome) -> bool:
    return isinstance(outcome.fault, str) and outcome.fault.startswith("PYTHON:")


# ---------------------------------------------------------------- grammar
def _aname(rng: random.Random, used: set[str]) -> str:
    for _ in range(200):
        name = rng.choice(_SYLLABLES) + rng.choice(_SYLLABLES)
        if name not in used and _usable(name):
            used.add(name)
            return name
    raise RuntimeError("ran out of ability names")


def _atom(rng: random.Random, *, wrong: bool) -> str:
    """One postfix value. ``wrong`` avoids a plain number."""
    if wrong:
        kind = rng.choice(("text", "truth", "void", "list", "book"))
    else:
        kind = "num"
    if kind == "num":
        return hx(rng.choice((0, 1, 2, 3, 4, 7, -1, -2, 8, 15, 0xFFFF)))
    if kind == "text":
        return rng.choice(('""', '"a"', '"ab"', '"z"'))
    if kind == "truth":
        return rng.choice(("bytp", "əxbytp"))
    if kind == "void":
        return "əixiww"
    if kind == "list":
        return rng.choice(("0-ťewn", "1-1-ťewn", '"a"-1-ťewn'))
    return rng.choice(("0-tekt", '"k"-"v"-1-tekt'))


def _list_phrase(rng: random.Random, *, wrong: bool) -> str:
    if rng.randrange(4) == 0 and not wrong:
        return "0-ťewn"
    count = rng.randrange(1, 4)
    items = [_atom(rng, wrong=wrong) for _ in range(count)]
    return "-".join(items + [hx(count), "ťewn"])


def _book_phrase(rng: random.Random, *, wrong: bool) -> str:
    """A book. The wrong path keys it with a list or a book.

    A number and a truth are different keys, so some books carry both
    ``1`` and ``əxbytp``, or both ``0`` and ``bytp``.
    """
    if wrong:
        key = rng.choice(("0-ťewn", "0-tekt"))
        return f"{key}-{_atom(rng, wrong=False)}-1-tekt"
    if rng.randrange(5) == 0:
        return "0-tekt"
    if rng.randrange(3) == 0:
        left = _atom(rng, wrong=False)
        right = _atom(rng, wrong=False)
        return rng.choice((
            f"1-{left}-əxbytp-{right}-2-tekt",
            f"0-{left}-bytp-{right}-2-tekt",
        ))
    key = rng.choice(('"k"', "0", "1", "əxbytp", "bytp"))
    return f"{key}-{_atom(rng, wrong=False)}-1-tekt"


def _ron_phrase(rng: random.Random, *, wrong: bool) -> str:
    if wrong:
        # Just past the documented span. The check fails before allocation.
        return f"{hx(rng.choice((-4, -1, 0, 0x100001)))}-ronɣ"
    return f"{hx(rng.choice((0, 1, 2, 3)))}-ronɣ"


def _mul_phrase(rng: random.Random, *, wrong: bool) -> str:
    if wrong:
        kind = rng.randrange(4)
        if kind == 0:
            return f'"ab"-{hx(0x100000)}-tøwp'
        if kind == 1:
            return f"{_atom(rng, wrong=True)}-{_atom(rng, wrong=True)}-tøwp"
        if kind == 2:
            return '"ab"-əx2-tøwp'
        return '""-5-tøwp'
    kind = rng.randrange(4)
    if kind == 0:
        return f"{hx(rng.choice((0, 2, -3, 6)))}-{hx(rng.choice((0, 1, 2, -2)))}-tøwp"
    if kind == 1:
        return f'"z"-{hx(rng.choice((0, 1, 3)))}-tøwp'
    if kind == 2:
        return "0-ťewn-4-tøwp"
    return "1-2-2-ťewn-2-tøwp"


# Negative-literal base of lu'f, and negative literals for the three
# integer operators. seed % 50 attaches one sentence, so each of the five
# shows up in six of the default 300 programs.
_NEGATIVE_POOL = (
    "!əx2-2-lu'f.\n",
    "!əx2-3-lu'f.\n",
    "!əx5-3-geft.\n",
    "!əx8-əx2-χɬkevk.\n",
    "!əx5-əx2-mɒɣg.\n",
)
_NEG_BINARY = {
    "geft": ("əx5-3-geft", "əx8-əx2-geft", "5-əx2-geft"),
    "χɬkevk": ("əx8-əx2-χɬkevk", "əx8-2-χɬkevk", "8-əx2-χɬkevk"),
    "mɒɣg": ("əx5-əx2-mɒɣg", "əx5-2-mɒɣg", "5-əx2-mɒɣg"),
}


def _pool_sentence(seed: int) -> str:
    slot = seed % 50
    if slot >= len(_NEGATIVE_POOL):
        return ""
    return _NEGATIVE_POOL[slot]


def _with_pool(seed: int, source: str) -> str:
    extra = _pool_sentence(seed)
    if not extra:
        return source
    if source and not source.endswith("\n"):
        source += "\n"
    return source + extra


def _pow_phrase(rng: random.Random, *, wrong: bool) -> str:
    if wrong:
        if rng.randrange(2) == 0:
            return f"{hx(rng.choice((0, 2, -2)))}-{hx(10001)}-lu'f"
        return f"{hx(rng.choice((2, -3)))}-əx1-lu'f"
    # Even and odd exponents of a negative base are half the draws.
    if rng.randrange(2) == 0:
        return rng.choice(("əx2-2-lu'f", "əx2-3-lu'f"))
    return f"{hx(rng.choice((0, 2, -2, 3)))}-{hx(rng.choice((0, 1, 2, 3)))}-lu'f"


def _value_phrase(word: str, rng: random.Random, *, wrong: bool) -> str:
    """Postfix that applies ``word`` and leaves one value."""
    if word == "ťewn":
        return _list_phrase(rng, wrong=wrong)
    if word == "tekt":
        return _book_phrase(rng, wrong=wrong)
    if word == "ronɣ":
        return _ron_phrase(rng, wrong=wrong)
    if word == "tøwp":
        return _mul_phrase(rng, wrong=wrong)
    if word == "lu'f":
        return _pow_phrase(rng, wrong=wrong)
    if word == "'uɬč":
        bound = rng.choice((0, -1, -3)) if wrong else rng.choice((1, 2, 4))
        return f"{hx(bound)}-'uɬč"
    if word == "ţə''":
        return f"{_atom(rng, wrong=wrong)}-alfa-ţə''"
    if word == "'uxq":
        return "'uxq"
    if word == "asərθ":
        if wrong:
            return rng.choice(("əixiww", "0-ťewn", '"zz"', "bytp")) + "-asərθ"
        return rng.choice(('"0a"', '"əx2"', "əxbytp", "bytp", hx(4))) + "-asərθ"
    if word in ("bɬølπ",):
        if wrong:
            return f"{hx(1)}-{_atom(rng, wrong=False)}-bɬølπ"
        return f"0-ťewn-{_atom(rng, wrong=False)}-bɬølπ"
    if word == "čxət'":
        if wrong:
            return f"{hx(1)}-{hx(0)}-čxət'"
        return "1-2-2-ťewn-0-čxət'"
    if word == "tapq":
        if wrong:
            return f'"ab"-{hx(-1)}-tapq'
        return f"1-2-2-ťewn-{hx(rng.choice((0, -1)))}-tapq"
    if word in ("'iixtfu'q", "ǩeǆylqitsodrm"):
        if wrong:
            return f"{hx(1)}-{word}"
        return f"1-2-2-ťewn-{word}"
    if word == "samk":
        if wrong:
            return f"{rng.choice((hx(1), 'bytp', 'əixiww'))}-samk"
        return rng.choice(("0-ťewn", '"ab"', "0-tekt")) + "-samk"
    if word == "rukxtekt":
        if wrong:
            return "0-ťewn-rukxtekt"
        return '"k"-"v"-1-tekt-rukxtekt'
    if word == "tluxt":
        if wrong:
            return f"{hx(1)}-tluxt"
        return rng.choice(("1-2-2-ťewn", '"k"-"v"-1-tekt')) + "-tluxt"
    if word == "ɣɒzɢ":
        if wrong:
            return f"{hx(1)}-{hx(0)}-{hx(1)}-ɣɒzɢ"
        return rng.choice(('"abcd"-1-3-ɣɒzɢ', "1-2-3-3-ťewn-1-3-ɣɒzɢ", '"ab"-əx1-2-ɣɒzɢ'))
    if word == "pən'g":
        if wrong:
            return f"{hx(1)}-{hx(1)}-pən'g"
        return rng.choice(('"a-b"-"-"-pən\'g', '""-"-"-pən\'g', '"ab"-""-pən\'g'))
    if word == "raφoj":
        if wrong:
            return f"{hx(1)}-{hx(1)}-raφoj"
        return '1-"a"-2-ťewn-"-"-raφoj'
    if word == "dl":
        if wrong:
            return f"{hx(1)}-{hx(1)}-dl"
        return '1-1-2-2-ťewn-dl'
    if word in _NEG_BINARY and not wrong and rng.randrange(2) == 0:
        return rng.choice(_NEG_BINARY[word])
    if word in ("χɬkevk", "geft") and wrong:
        if rng.randrange(2) == 0:
            return f"{hx(rng.choice((1, 4, -2)))}-0-{word}"
        return f"{_atom(rng, wrong=True)}-{_atom(rng, wrong=True)}-{word}"
    if word in ("grmɒɣg", "korxgr") and not wrong:
        return f"{hx(1)}-{hx(2)}-{word}"
    if word == "ǆ'ynpp" and not wrong:
        return rng.choice((f"{hx(1)}-{hx(1)}-ǆ'ynpp", f"{hx(1)}-əxbytp-ǆ'ynpp", '"a"-"a"-ǆ\'ynpp'))
    if word == "ʁšθakɴ" and not wrong:
        return f"əxbytp-{hx(1)}-{hx(2)}-ʁšθakɴ"
    arity = VERBS[word].arity
    if arity < 0:
        raise RuntimeError(word)
    parts = [_atom(rng, wrong=wrong) for _ in range(arity)]
    parts.append(word)
    return "-".join(parts)


def _caught(phrase: str) -> str:
    return f"^baqilx:\n    ^{phrase}.\n^qit:\n    !dekp.\n"


def _shown(phrase: str) -> str:
    return f"!{phrase}.\n"


_CONTROL = {
    "'iţpənn", "lups", "ɢnagɮ", "ɬšeɴazv", "qab'", "bukð",
    "čtəčpliɣn", "naķm", "brøtjt", "mɴyrx",
}


def _value_program(word: str, rng: random.Random) -> str:
    good = _value_phrase(word, rng, wrong=False)
    bad = _value_phrase(word, rng, wrong=True)
    return _shown(good) + _caught(bad)


def _cast_source(seed: int, folder: Path) -> str:
    name = f"c{seed}.phyx"
    (folder / name).write_text(
        "^ťe-brought:\n    ^lo-7-'iţpənn.\n^3-alfa-ţə''.\n",
        encoding="utf-8",
        newline="\n",
    )
    return (
        f'^"{name}"-bukð.\n'
        "!brought.\n"
        "!alfa.\n"
        + _caught("1-bukð")
    )


def _notes_source(seed: int) -> str:
    name = f"n{seed}.txt"
    missing = f"missing-{seed}.txt"
    return (
        f'^"hello"-"{name}"-mɴyrx-kept-ţə\'\'.\n'
        f'!"{name}"-brøtjt.\n'
        "!kept.\n"
        + _caught(f'"{missing}"-brøtjt')
        + _caught("1-2-mɴyrx")
        + _caught("1-brøtjt")
    )


def _activate_source() -> str:
    return (
        "^ťe-a-b-add:\n"
        "    ^lo-a-b-babg-'iţpənn.\n"
        "^xe-add-naķm-fn-ţə''.\n"
        "!3-4-2-ťewn-fn-čtəčpliɣn.\n"
        "!1-add-πøkk.\n"
        "^ťe-hi:\n"
        '    !"yo".\n'
        "^xe-hi-naķm-g-ţə''.\n"
        "^lo-0-ťewn-g-čtəčpliɣn.\n"
        "^xe-hi.\n"
        + _caught("1-fn-čtəčpliɣn")
        + _caught("1-naķm")
    )


def _return_source() -> str:
    return (
        "^ťe-ret:\n"
        "    ^lo-1-'iţpənn.\n"
        "!ret.\n"
    )


def _break_source() -> str:
    return (
        "^aχəw'-item-dl-4-ronɣ:\n"
        "    ^ba-item-2-ǆ'ynpp:\n"
        "        ^xe-lups.\n"
        "    !item.\n"
    )


def _continue_source() -> str:
    return (
        "^aχəw'-item-dl-3-ronɣ:\n"
        "    ^ba-item-1-ǆ'ynpp:\n"
        "        ^xe-ɢnagɮ.\n"
        "    !item.\n"
    )


def _raise_source() -> str:
    # qit with dekp, and qit that does not read dekp.
    return (
        _caught('"boom"-ɬšeɴazv')
        + _caught("1-0-χɬkevk")
        + "^baqilx:\n    ^1-0-geft.\n^qit:\n    !1.\n"
    )


def program_for_verb(word: str, rng: random.Random, seed: int, folder: Path) -> str:
    if word == "qab'":
        return f"^{hx(rng.choice((0, 2, 4, -1)))}-qab'.\n"
    if word == "bukð":
        return _cast_source(seed, folder)
    if word == "mɴyrx":
        return _notes_source(seed)
    if word == "brøtjt":
        return _notes_source(seed)
    if word in ("čtəčpliɣn", "naķm"):
        return _activate_source()
    if word == "'iţpənn":
        return _return_source()
    if word == "lups":
        return _break_source()
    if word == "ɢnagɮ":
        return _continue_source()
    if word == "ɬšeɴazv":
        return _raise_source()
    return _value_program(word, rng)


# ---------------------------------------------------------------- scenarios
# Each one is a finite program. Together they walk the Scope section.

def _walk_out() -> str:
    # An assignment walks outward through enclosing abilities.
    return (
        "^ťe-outer:\n"
        "    ^1-alfa-ţə''.\n"
        "    ^ťe-inner:\n"
        "        ^2-alfa-ţə''.\n"
        "        !alfa.\n"
        "    ^xe-inner.\n"
        "    !alfa.\n"
        "^xe-outer.\n"
    )


def _parameter() -> str:
    # A parameter is a binding from the moment the body runs, and shadows.
    return (
        "^5-alfa-ţə''.\n"
        "^ťe-alfa-show:\n"
        "    !alfa.\n"
        "    ^alfa-1-babg-alfa-ţə''.\n"
        "    !alfa.\n"
        "!7-show.\n"
        "!alfa.\n"
    )


def _const_rebind() -> str:
    return (
        "^'u-1-alfa-ţə''.\n"
        + _caught("2-alfa-ţə''")
    )


def _const_shadow() -> str:
    # 'u fixes the running scope and does not walk outward.
    return (
        "^5-alfa-ţə''.\n"
        "^ťe-kept:\n"
        "    ^'u-2-alfa-ţə''.\n"
        "    !alfa.\n"
        "^xe-kept.\n"
        "!alfa.\n"
    )


def _local_stays() -> str:
    # No outer binding: the assignment creates a local, and it does not leak.
    return (
        "^ťe-kept:\n"
        "    ^3-alfa-ţə''.\n"
        "    !alfa.\n"
        "^xe-kept.\n"
        + _caught("alfa")
    )


def _bind_when_run() -> str:
    # The choice is made when the assignment runs, not when ťe is read.
    return (
        "^ťe-kept:\n"
        "    ^9-alfa-ţə''.\n"
        "    !alfa.\n"
        "^4-alfa-ţə''.\n"
        "^xe-kept.\n"
        "!alfa.\n"
    )


def _read_then_plain_assign() -> str:
    # A later plain assignment does not hide the outer name from an earlier read.
    return (
        "^5-alfa-ţə''.\n"
        "^ťe-kept:\n"
        "    !alfa.\n"
        "    ^2-alfa-ţə''.\n"
        "^xe-kept.\n"
        "!alfa.\n"
    )


def _bind_inside() -> str:
    # A name is bound once an assignment inside ba / baxuφ / aχəw' / baqilx has run.
    return (
        "^ba-əxbytp:\n"
        "    ^4-alfa-ţə''.\n"
        "!alfa.\n"
        "^0-kount-ţə''.\n"
        "^baxuφ-kount-2-grmɒɣg:\n"
        "    ^7-bravo-ţə''.\n"
        "    ^kount-1-babg-kount-ţə''.\n"
        "!bravo.\n"
        "^aχəw'-item-dl-2-ronɣ:\n"
        "    ^8-carlo-ţə''.\n"
        "!carlo.\n"
        "^baqilx:\n"
        "    ^9-delta-ţə''.\n"
        "^qit:\n"
        "    !dekp.\n"
        "!delta.\n"
    )


def _skipped_branch() -> str:
    return (
        "^ba-bytp:\n"
        "    ^1-alfa-ţə''.\n"
        + _caught("alfa")
    )


def _try_shares() -> str:
    # The tried body and the qit handler share the scope that contains them.
    return (
        "^baqilx:\n"
        "    ^1-alfa-ţə''.\n"
        '    ^"x"-ɬšeɴazv.\n'
        "^qit:\n"
        "    !alfa,dekp.\n"
    )


def _empty_for() -> str:
    # An empty loop does not bind the item.
    return (
        "^aχəw'-alfa-dl-0-ronɣ:\n"
        "    !alfa.\n"
        + _caught("alfa")
    )


def _for_and_ask() -> str:
    # The item and the target of ? stay bound once the sentence has run.
    return (
        "^aχəw'-alfa-dl-3-ronɣ:\n"
        "    !alfa.\n"
        "!alfa.\n"
        '?"name"-bravo.\n'
        "!bravo.\n"
    )


def _handler_keeps() -> str:
    # dekp, and any name or ability bound in the handler, stay bound.
    return (
        "^baqilx:\n"
        "    ^1-0-χɬkevk.\n"
        "^qit:\n"
        "    ^7-alfa-ţə''.\n"
        "    ^ťe-kept:\n"
        "        ^lo-4-'iţpənn.\n"
        "!alfa.\n"
        "!kept.\n"
        "!dekp.\n"
    )


# Reviewer case (b). Both engines now report the same fault.
LOOP_CONST = (
    "^ťe-fbx:\n"
    "    ^aχəw'-w-dl-2-ronɣ:\n"
    "        !w.\n"
    "        ^aχəw'-y-dl-2-ronɣ:\n"
    "            ^'u-2-w-ţə''.\n"
    "^xe-fbx.\n"
)


def _later_const_assign() -> str:
    return (
        "^ťe-kept:\n"
        "    ^'u-2-alfa-ţə''.\n"
        "    ^3-alfa-ţə''.\n"
        "^xe-kept.\n"
    )


def _names_around() -> str:
    # Module names assigned before and after abilities that read or assign them.
    return (
        "^1-alfa-ţə''.\n"
        "^ťe-rd:\n"
        "    !alfa.\n"
        "^xe-rd.\n"
        "^ťe-wr:\n"
        "    ^9-alfa-ţə''.\n"
        "^ťe-readb:\n"
        "    !bravo.\n"
        "^2-bravo-ţə''.\n"
        "^xe-wr.\n"
        "!alfa.\n"
        "^xe-readb.\n"
    )


def _read_unbound() -> str:
    return _caught("missing") + (
        "^ťe-kept:\n"
        "    !missing.\n"
        "^xe-kept.\n"
    )


def _uncalled() -> str:
    # A fault in an ability that is never called must not matter.
    return (
        "^ťe-kept:\n"
        "    ^lo-1-0-χɬkevk-'iţpənn.\n"
        "^ťe-other:\n"
        "    !missing.\n"
        "!1.\n"
    )


def _under_apply(rng: random.Random) -> str:
    # Fewer objects than the arity is the ability value. Zero parameters is a call.
    depth = rng.randrange(0, 3)
    return (
        "^ťe-a-b-add:\n"
        "    ^lo-a-b-babg-'iţpənn.\n"
        "!1-add-πøkk.\n"
        "!3-4-add.\n"
        "^ťe-hi:\n"
        '    !"yo".\n'
        "^xe-hi-naķm-g-ţə''.\n"
        "!g-πøkk.\n"
        "^xe-hi.\n"
        "^ťe-n-down:\n"
        "    ^ba-n-1-grmɒɣg:\n"
        "        ^lo-n-'iţpənn.\n"
        "    ^lo-n-1-mɒɣg-down-'iţpənn.\n"
        f"!{hx(depth)}-down.\n"
    )


def _nested() -> str:
    return (
        "^ťe-n-outer:\n"
        "    ^ťe-m-inner:\n"
        "        ^lo-m-1-babg-'iţpənn.\n"
        "    ^lo-n-inner-'iţpənn.\n"
        "!4-outer.\n"
        "!1-inner.\n"
    )


def _defined_late() -> str:
    # ťe names are visible throughout the file, including before the sentence.
    return (
        "!3-4-add.\n"
        "^ťe-a-b-add:\n"
        "    ^lo-a-b-babg-'iţpənn.\n"
    )


def _qab_ability(rng: random.Random) -> str:
    code = rng.choice((0, 2, 3, 7, -1))
    return (
        "^ťe-stop:\n"
        f"    ^{hx(code)}-qab'.\n"
        "^xe-stop.\n"
        '!"no".\n'
    )


def _qab_try(rng: random.Random) -> str:
    code = rng.choice((0, 4, 5))
    return (
        "^baqilx:\n"
        f"    ^{hx(code)}-qab'.\n"
        "^qit:\n"
        "    !dekp.\n"
        '!"after".\n'
    )


def _qab_bad() -> str:
    return _caught('"no"-qab\'')


def _book_key() -> str:
    return (
        _caught('0-ťewn-"v"-1-tekt')
        + _caught('0-tekt-"v"-1-tekt')
        + "^xe-\"a\"-1-1-tekt-bravo-ţə''.\n"
        + _caught("9-bravo-0-ťewn-tapq-ţə''")
        + _caught("9-bravo-0-tekt-tapq-ţə''")
    )


def _span(seed: int, first_span_seed: int) -> str:
    over_ron = _caught(f"{hx(0x100001)}-ronɣ")
    over_mul = _caught(f'"ab"-{hx(0x100000)}-tøwp')
    empty = (
        f"!{hx(-1)}-ronɣ-samk.\n"
        '!""-əx3-tøwp-samk.\n'
        "!0-ťewn-0-tøwp-samk.\n"
        "!0-ťewn-əx2-tøwp-samk.\n"
    )
    if seed != first_span_seed:
        return over_ron + over_mul + empty
    # Exactly the documented limit, once. samk keeps the spoken value small.
    return (
        f"!{hx(0x100000)}-ronɣ-samk.\n"
        f'!"a"-{hx(0x100000)}-tøwp-samk.\n'
        + over_ron
        + over_mul
        + empty
    )


def _ask() -> str:
    return '?"name"-alfa.\n!alfa.\n'


def _assert() -> str:
    return (
        '^ǩaπa-1-1-ǆ\'ynpp,"yes".\n'
        + _caught('ǩaπa-bytp,"no"')
    )


def _else_if() -> str:
    return (
        "^ba-bytp:\n"
        "    !1.\n"
        "^qit-ba-əxbytp:\n"
        "    !2.\n"
        "^qit:\n"
        "    !3.\n"
    )


def _unless() -> str:
    return (
        "^bu-bytp:\n"
        "    !1.\n"
        "^əx-bytp:\n"
        "    !2.\n"
        "^ba-bytp:\n"
        "    !3.\n"
        "^qit:\n"
        "    !4.\n"
    )


def _comma() -> str:
    return "!1,2.\n!1-2-babg,3.\n"


def _while_bounds() -> str:
    return (
        "^0-kount-ţə''.\n"
        "^baxuφ-kount-0-grmɒɣg:\n"
        "    ^1-alfa-ţə''.\n"
        "    ^kount-1-babg-kount-ţə''.\n"
        + _caught("alfa")
        + "^0-kount-ţə''.\n"
        "^baxuφ-kount-3-grmɒɣg:\n"
        "    !kount.\n"
        "    ^kount-1-babg-kount-ţə''.\n"
    )


def _collections() -> str:
    return (
        "^xe-1-2-2-ťewn-alfa-ţə''.\n"
        "^xe-alfa-9-bɬølπ.\n"
        "^xe-8-alfa-0-tapq-ţə''.\n"
        "^xe-alfa-əx1-tapq.\n"
        "^xe-alfa-1-čxət'.\n"
        "!alfa.\n"
        "^xe-alfa-tluxt-samk.\n"
        "^xe-alfa-'iixtfu'q.\n"
        "^xe-alfa-ǩeǆylqitsodrm.\n"
        "^xe-1-alfa-dl.\n"
        '^xe-"k"-"v"-1-tekt-rukxtekt.\n'
        '^xe-"abcd"-1-3-ɣɒzɢ.\n'
        '^xe-"a-b"-"-"-pən\'g.\n'
        '^xe-1-"a"-2-ťewn-"-"-raφoj.\n'
    )


def _logic() -> str:
    return (
        "!bytp-əxbytp-xə.\n"
        "!bytp-əxbytp-ðə.\n"
        "!1-əxbytp-ǆ'ynpp.\n"
        "!əxbytp-1-2-ʁšθakɴ.\n"
        "!bytp-\"a\"-\"b\"-ʁšθakɴ.\n"
        f"!{hx(0xFFFF)}-1-babg.\n"
        f"!{hx(0x100000)}-əx1-mɒɣg.\n"
        "!2-əx3-tøwp.\n"
        + _caught('1-"a"-grmɒɣg')
        + _caught("1-0-χɬkevk")
        + _caught("1-0-geft")
    )


def _persistent() -> tuple[str, str]:
    # A later ability rebinds a name an earlier sentence of the session bound.
    return (
        "^1-alfa-ţə''.\n^ťe-bump:\n    ^alfa-1-babg-alfa-ţə''.\n",
        "!alfa.\n^xe-bump.\n!alfa.\n",
    )


def _small_recursion() -> str:
    return (
        "^ťe-n-down:\n"
        "    ^ba-n-1-grmɒɣg:\n"
        "        ^lo-n-'iţpənn.\n"
        "    ^lo-n-1-mɒɣg-down-'iţpənn.\n"
        "!2-down.\n"
        "!1.\n"
    )


def _mix(rng: random.Random) -> str:
    used: set[str] = set()
    name = _aname(rng, used)
    params = rng.sample(_NAMES, rng.randrange(0, 4))
    if not params:
        body = "    ^lo-1-'iţpənn.\n"
        call = f"^xe-{name}.\n"
    else:
        folded = "-".join(params)
        if len(params) == 1:
            body = f"    ^lo-{params[0]}-1-babg-'iţpənn.\n"
        else:
            body = f"    ^lo-{folded}-babg-'iţpənn.\n"
        args = "-".join(hx(rng.choice((0, 1, 2, 3))) for _ in params)
        call = f"!{args}-{name}.\n"
        if rng.randrange(2) == 0 and len(params) > 1:
            # One object short: the ability value, not a call.
            call += f"!{hx(1)}-{name}-πøkk.\n"
    header = "^ťe-" + "-".join([*params, name]) + ":\n"
    lines = [
        f"^{hx(rng.choice((0, 1, 2, -1)))}-alfa-ţə''.",
        f"^{hx(rng.choice((0, 1, 3)))}-bravo-ţə''.",
        header + body + call.rstrip("\n"),
    ]
    pool = [w for w in _VERB_WORDS if w not in _CONTROL and w != "qab'"]
    for _ in range(4):
        word = rng.choice(pool)
        phrase = _value_phrase(word, rng, wrong=rng.randrange(2) == 0)
        if rng.randrange(3) == 0:
            lines.append(_caught(phrase).rstrip("\n"))
        else:
            lines.append(_shown(phrase).rstrip("\n"))
    # lo, as well as xe, shows up as a marker above. A bare read may fault.
    if rng.randrange(3) == 0:
        lines.append(_caught("missing").rstrip("\n"))
    return "\n".join(lines) + "\n"


def _scenarios(first_span_seed: int):
    def bind(fn):
        def run(rng, seed, folder):
            return fn()
        return run

    return (
        bind(_walk_out),
        bind(_parameter),
        bind(_const_rebind),
        bind(_const_shadow),
        bind(_local_stays),
        bind(_bind_when_run),
        bind(_read_then_plain_assign),
        bind(_bind_inside),
        bind(_skipped_branch),
        bind(_try_shares),
        bind(_empty_for),
        bind(_for_and_ask),
        bind(_handler_keeps),
        lambda rng, seed, folder: LOOP_CONST,
        bind(_later_const_assign),
        bind(_names_around),
        bind(_read_unbound),
        bind(_uncalled),
        lambda rng, seed, folder: _under_apply(rng),
        bind(_nested),
        bind(_defined_late),
        lambda rng, seed, folder: _qab_ability(rng),
        lambda rng, seed, folder: _qab_try(rng),
        bind(_qab_bad),
        lambda rng, seed, folder: _activate_source(),
        lambda rng, seed, folder: _cast_source(seed, folder),
        lambda rng, seed, folder: _book_key(),
        lambda rng, seed, folder: _span(seed, first_span_seed),
        bind(_ask),
        bind(_assert),
        bind(_else_if),
        bind(_unless),
        lambda rng, seed, folder: _break_source() + _continue_source(),
        bind(_comma),
        lambda rng, seed, folder: _persistent(),
        lambda rng, seed, folder: _small_recursion(),
        lambda rng, seed, folder: _mix(rng),
        bind(_while_bounds),
        bind(_collections),
        bind(_logic),
        lambda rng, seed, folder: _notes_source(seed),
    )


_SCENARIOS = None
_FIRST_SPAN = None


def _scenario_table():
    global _SCENARIOS, _FIRST_SPAN
    if _SCENARIOS is None:
        _FIRST_SPAN = len(_VERB_WORDS) + 27  # index of _span in the table above
        _SCENARIOS = _scenarios(_FIRST_SPAN)
    return _SCENARIOS


def generate(seed: int, folder: Path) -> Case:
    """One finite program for ``seed``."""
    rng = random.Random(seed)
    scenarios = _scenario_table()
    if seed < len(_VERB_WORDS):
        source = _with_pool(seed, program_for_verb(_VERB_WORDS[seed], rng, seed, folder))
        return Case(seed, source)
    scenario = scenarios[(seed - len(_VERB_WORDS)) % len(scenarios)]
    made = scenario(rng, seed, folder)
    if isinstance(made, tuple):
        parts = [part if part.endswith("\n") else part + "\n" for part in made]
        extra = _pool_sentence(seed)
        if extra:
            parts[-1] = parts[-1] + extra
        joined = "\n".join(part.rstrip("\n") for part in parts) + "\n"
        return Case(seed, joined, chunks=tuple(parts))
    made = _with_pool(seed, made)
    # _small_recursion is index 35. A depth-2 ability under a small ceiling.
    if (seed - len(_VERB_WORDS)) % len(scenarios) == 35:
        return Case(seed, made, recursion=_SMALL_RECURSION)
    return Case(seed, made)


def _check_index_of_span() -> None:
    """The span scenario is the one allowed to build a full-size list."""
    # Pinned by counting the table. A drift here would either skip the
    # limit or build a million-item list on every cycle.
    scenarios = _scenario_table()
    if _FIRST_SPAN != len(_VERB_WORDS) + 27:
        raise RuntimeError("span seed drifted")
    if len(scenarios) < 35:
        raise RuntimeError("scenario table shrank")


_check_index_of_span()


# ---------------------------------------------------------------- coverage
def scan(source: str, verbs: set[str], forms: set[str]) -> None:
    tokens = tokenize(source)
    total = len(tokens)
    for index, tok in enumerate(tokens):
        if tok.kind == "WORD" and tok.value in VERBS:
            verbs.add(tok.value)
        if tok.kind == "START" and tok.value in ("!", "?"):
            forms.add(tok.value)
        if tok.kind != "START" or tok.value != "^":
            continue
        nxt = index + 1
        while nxt < total and tokens[nxt].kind == "SEP":
            nxt += 1
        if nxt < total and tokens[nxt].kind == "WORD" and tokens[nxt].value in MARKERS:
            forms.add(tokens[nxt].value)
        else:
            forms.add("xe")


def _format_counter(counter: dict[str, int]) -> str:
    parts = [f"{name}:{counter[name]}" for name in sorted(counter)]
    return ",".join(parts) if parts else "none"


# ---------------------------------------------------------------- known bugs
# (a) A read, then 'u of the same name, inside one ability.
BUG_J = (
    "^ťe-fbx:\n"
    "    !w.\n"
    "    ^'u-2-w-ţə''.\n"
    "^aχəw'-w-dl-3-ronɣ:\n"
    "    ^xe-fbx.\n"
)
BUG_J_WALKER = ("0\n1\n2\n", None)

# 'iţpənn outside an ability, and lups / ɢnagɮ outside a loop, are grammar
# faults. The parser names the line and a hint, so neither engine runs them.
_RETURN_HINT = "'iţpənn returns from the ability that is running; write it inside ťe"
_STOP_HINT = "lups leaves a baxuφ or aχəw'; write it inside that loop"
_NEXT_HINT = "ɢnagɮ skips to the next turn of a baxuφ or aχəw'; write it inside that loop"
BUG_L = "^1-'iţpənn.\n"
BUG_L_WALKER = (
    "",
    ("ParseError", "'iţpənn (return) used outside of an ability", 1, _RETURN_HINT),
)
BUG_M = "^lups.\n"
BUG_M_WALKER = (
    "",
    ("ParseError", "lups (stop) used outside of a loop", 1, _STOP_HINT),
)
BUG_N = "^ɢnagɮ.\n"
BUG_N_WALKER = (
    "",
    ("ParseError", "ɢnagɮ (next) used outside of a loop", 1, _NEXT_HINT),
)

# The same words inside baqilx are still grammar faults. qit does not run.
BUG_O = "^baqilx:\n    ^1-'iţpənn.\n^qit:\n    !dekp.\n"
BUG_O_WALKER = (
    "",
    ("ParseError", "'iţpənn (return) used outside of an ability", 2, _RETURN_HINT),
)
BUG_P = "^baqilx:\n    ^lups.\n^qit:\n    !dekp.\n"
BUG_P_WALKER = (
    "",
    ("ParseError", "lups (stop) used outside of a loop", 2, _STOP_HINT),
)
BUG_Q = "^baqilx:\n    ^ɢnagɮ.\n^qit:\n    !dekp.\n"
BUG_Q_WALKER = (
    "",
    ("ParseError", "ɢnagɮ (next) used outside of a loop", 2, _NEXT_HINT),
)

# 'u of the enclosing loop's item, when that name also exists outside.
# The same text without a persistent session is LOOP_CONST, and the engines
# agree. In a persistent session the tree-walker prints 0 and then faults on
# the 'u. The compiled engine faults with an unknown word on the print.
BUG_R = (
    "^ťe-fbx:\n"
    "    ^aχəw'-w-dl-2-ronɣ:\n"
    "        !w.\n"
    "        ^aχəw'-y-dl-2-ronɣ:\n"
    "            ^'u-2-w-ţə''.\n"
    "^xe-fbx.\n"
)
BUG_R_WALKER = (
    "0\n",
    (
        "RuntimeFault",
        "'w' already has a value here and cannot be fixed in the past ('u)",
        5,
        None,
    ),
)

# 'u in a qit handler of a name bound in the baqilx body of the same ability.
# The program without the last line agrees: both engines fault on the 'u.
# The tried body does fault (unknown y) and both engines catch that the same
# way, so the handler runs. A later module assignment of the same name is
# what still separates them. The tree-walker faults on the 'u. The compiled
# engine does not fault.
BUG_S = (
    "^ťe-fbx:\n"
    "    ^baqilx:\n"
    "        ^1-z-ţə''.\n"
    "        ^y-1-babg-y-ţə''.\n"
    "    ^qit:\n"
    "        ^'u-3-z-ţə''.\n"
    "^xe-fbx.\n"
    "^0-z-ţə''.\n"
)
BUG_S_WALKER = (
    "",
    (
        "RuntimeFault",
        "'z' already has a value here and cannot be fixed in the past ('u)",
        6,
        None,
    ),
)

# A second 'u of the same name, in a different nested block of the handler.
# The second 'u is not reached. The tree-walker faults on the first 'u.
# The compiled engine faults on the aχəw' above it, and its message is
# "'y' was fixed in the past ('u) and cannot change".
BUG_T = (
    "^baqilx:\n"
    "    !w.\n"
    "    ^aχəw'-y-dl-3-ronɣ:\n"
    "        !y.\n"
    "^qit:\n"
    "    ^ťe-fcx:\n"
    "        ^aχəw'-y-dl-3-ronɣ:\n"
    "            ^'u-2-y-ţə''.\n"
    "    ^xe-fcx.\n"
    "    ^baqilx:\n"
    "        ^'u-3-y-ţə''.\n"
)
BUG_T_WALKER = (
    "",
    (
        "RuntimeFault",
        "'y' already has a value here and cannot be fixed in the past ('u)",
        8,
        None,
    ),
)

# Both engines fault once the call depth passes the host ceiling.
# The line is omitted: it would point at whichever call happened to overflow.
BUG_K = (
    "^ťe-n-go:\n"
    "    ^ba-n-1-grmɒɣg:\n"
    "        ^lo-0-'iţpənn.\n"
    "    ^lo-n-1-mɒɣg-go-'iţpənn.\n"
    "!80-go.\n"
)
BUG_K_WALKER = (
    "",
    ("RuntimeFault", "the abilities called each other too deeply", None, None),
)


def _normalise(source: str) -> str:
    body = "\n".join(line.rstrip() for line in source.strip().splitlines())
    return body + "\n"


# Disagreements that the fuzzer should skip. The pinned bugs are fixed,
# so a program that reduces to one of them is a new bug and must fail.
_KNOWN: set[str] = set()


class ParityFuzzTests(unittest.TestCase):
    def test_loop_const_agrees(self):
        # Reviewer case (b): 'u of a name the loop already bound.
        walked = run_both(LOOP_CONST)[1]
        self.assertEqual(
            walked,
            (
                "0\n",
                (
                    "RuntimeFault",
                    "'w' already has a value here and cannot be fixed in the past ('u)",
                    5,
                    None,
                ),
            ),
        )
        assertParity(LOOP_CONST)

    def test_BUG_J_tree_walker(self):
        self.assertEqual(run_both(BUG_J)[1], BUG_J_WALKER)

    def test_BUG_J_read_then_fix_local(self):
        assertParity(BUG_J)

    def test_BUG_L_tree_walker(self):
        self.assertEqual(run_both(BUG_L)[1], BUG_L_WALKER)

    def test_BUG_L_return_outside_has_no_line(self):
        assertParity(BUG_L)

    def test_BUG_M_tree_walker(self):
        self.assertEqual(run_both(BUG_M)[1], BUG_M_WALKER)

    def test_BUG_M_stop_outside_has_no_line(self):
        assertParity(BUG_M)

    def test_BUG_N_tree_walker(self):
        self.assertEqual(run_both(BUG_N)[1], BUG_N_WALKER)

    def test_BUG_N_next_outside_has_no_line(self):
        assertParity(BUG_N)

    def test_BUG_O_tree_walker(self):
        self.assertEqual(run_both(BUG_O)[1], BUG_O_WALKER)

    def test_BUG_O_return_inside_try_is_not_caught(self):
        assertParity(BUG_O)

    def test_BUG_P_tree_walker(self):
        self.assertEqual(run_both(BUG_P)[1], BUG_P_WALKER)

    def test_BUG_P_stop_inside_try_is_not_caught(self):
        assertParity(BUG_P)

    def test_BUG_Q_tree_walker(self):
        self.assertEqual(run_both(BUG_Q)[1], BUG_Q_WALKER)

    def test_BUG_Q_next_inside_try_is_not_caught(self):
        assertParity(BUG_Q)

    def test_BUG_R_tree_walker(self):
        self.assertEqual(run_both(BUG_R, persistent=True)[1], BUG_R_WALKER)

    @unittest.expectedFailure
    def test_BUG_R_enclosing_loop_name_persistent(self):
        assertParity(BUG_R, persistent=True)

    def test_BUG_S_tree_walker(self):
        self.assertEqual(run_both(BUG_S)[1], BUG_S_WALKER)

    @unittest.expectedFailure
    def test_BUG_S_fix_in_handler_of_try_name(self):
        assertParity(BUG_S)

    def test_BUG_T_tree_walker(self):
        self.assertEqual(run_both(BUG_T)[1], BUG_T_WALKER)

    @unittest.expectedFailure
    def test_BUG_T_second_fix_message(self):
        assertParity(BUG_T)

    def test_BUG_K_deep_fault_lines(self):
        previous = os.environ.get("PHYX_RECURSION")
        os.environ["PHYX_RECURSION"] = str(MIN_RECURSION)
        shown: list[str] = []
        try:
            compiled, walked = run_both(BUG_K)
            for flag in (False, True):
                try:
                    run_source(BUG_K, treewalk=flag)
                except RuntimeFault as err:
                    shown.append(format_error(err, BUG_K))
                else:
                    self.fail("expected the abilities-too-deeply fault")
        finally:
            if previous is None:
                os.environ.pop("PHYX_RECURSION", None)
            else:
                os.environ["PHYX_RECURSION"] = previous
        self.assertEqual(walked, BUG_K_WALKER)
        self.assertEqual(compiled, walked)
        self.assertEqual(len(shown), 2)
        for text in shown:
            self.assertNotIn("(line ", text)
            self.assertIn("the abilities called each other too deeply", text)
            self.assertIn("in abilities: go x", text)

    def test_BUG_K_engines_disagree(self):
        previous = os.environ.get("PHYX_RECURSION")
        os.environ["PHYX_RECURSION"] = str(MIN_RECURSION)
        try:
            assertParity(BUG_K)
        finally:
            if previous is None:
                os.environ.pop("PHYX_RECURSION", None)
            else:
                os.environ["PHYX_RECURSION"] = previous

    def test_reduce_program_keeps_a_disagreement(self):
        # BUG-J now agrees. The reducer still has to drop lines that are
        # not part of the marked core and keep a core that stays marked.
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.assertFalse(
                _pair_differs(BUG_J, seed=0, base_dir=folder, recursion=None)
            )
            source = "!1.\n" + BUG_J

            def still_marked(text: str) -> bool:
                return "'u-2-w-ţə''" in text and "fbx" in text

            reduced = reduce_program(source, still_marked)
        self.assertNotIn("!1.", reduced)
        self.assertIn("fbx", reduced)
        self.assertTrue(still_marked(reduced))
        self.assertLessEqual(len(reduced.splitlines()), len(source.splitlines()))

    def test_fixed_seeds_agree(self):
        raw = os.environ.get("PHYX_FUZZ", "").strip()
        if raw:
            count = int(raw)
            if count < 1:
                self.fail("PHYX_FUZZ must be a positive integer")
            draw = random.SystemRandom()
            seeds = [draw.randrange(2**31) for _ in range(count)]
            check_budget = False
        else:
            seeds = list(_DEFAULT_SEEDS)
            check_budget = True
        self._drive(seeds, check_budget=check_budget, summary=bool(raw))

    def _drive(self, seeds: list[int], *, check_budget: bool, summary: bool) -> None:
        verbs: set[str] = set()
        forms: set[str] = set()
        faults: dict[str, int] = {}
        pool_hits = {sentence: 0 for sentence in _NEGATIVE_POOL}
        failures: list[str] = []
        saw_limit = False
        saw_recursion = False
        started = time.perf_counter()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for seed in seeds:
                case = generate(seed, folder)
                if case.recursion is not None:
                    saw_recursion = True
                if "100000-ronɣ-samk" in case.source and '"a"-100000-tøwp-samk' in case.source:
                    saw_limit = True
                blob = "\n".join(case.texts())
                for sentence in _NEGATIVE_POOL:
                    if sentence.strip() in blob:
                        pool_hits[sentence] += 1
                for text in case.texts():
                    try:
                        parse(text, base_dir=folder)
                    except PhyrexianError as err:
                        self.fail(
                            f"seed {seed} is not a valid program: {err.message}\n{text}"
                        )
                    scan(text, verbs, forms)
                try:
                    compiled, walked = run_case(case, folder)
                except TimeoutError:
                    failures.append(f"seed {seed} timed out\n{case.source}")
                    continue
                if _raw_python(compiled) or _raw_python(walked):
                    failures.append(
                        f"seed {seed} raised a Python exception\n"
                        f"compiled {compiled!r}\nwalker {walked!r}\n{case.source}"
                    )
                    continue
                faults[_fault_kind(walked)] = faults.get(_fault_kind(walked), 0) + 1
                if _as_tuple(compiled) == _as_tuple(walked):
                    continue
                if case.chunks:
                    minimal = case.source
                else:
                    minimal = reduce_program(
                        case.source,
                        lambda source, seed=seed, recursion=case.recursion: _pair_differs(
                            source, seed=seed, base_dir=folder, recursion=recursion,
                        ),
                    )
                if _normalise(minimal) in _KNOWN:
                    continue
                print(f"seed {seed}\n{case.source}", file=sys.stderr)
                failures.append(
                    f"seed {seed}\n--- program ---\n{case.source}"
                    f"--- reduced ---\n{minimal}"
                    f"compiled {_as_tuple(compiled)!r}\n"
                    f"walker {_as_tuple(walked)!r}"
                )
                if len(failures) >= 8:
                    break
        elapsed = time.perf_counter() - started
        if summary:
            print(
                f"fuzz: programs={len(seeds)} "
                f"faults={_format_counter(faults)} "
                f"verbs={len(verbs)}/{len(VERBS)} "
                f"time={elapsed:.2f}s",
                file=sys.stderr,
            )
        if check_budget:
            missing_verbs = [word for word in _VERB_WORDS if word not in verbs]
            missing_forms = [kind for kind in STATEMENT_KINDS if kind not in forms]
            self.assertFalse(
                missing_verbs or missing_forms,
                "generator missed "
                + (
                    f"verbs {missing_verbs} " if missing_verbs else ""
                )
                + (f"statements {missing_forms}" if missing_forms else ""),
            )
            self.assertGreaterEqual(len(seeds), 300)
            self.assertTrue(saw_limit, "generator never reached the ronɣ/tøwp limit")
            self.assertTrue(saw_recursion, "generator never set PHYX_RECURSION")
            self.assertLess(
                elapsed,
                5.0,
                f"{len(seeds)} programs took {elapsed:.2f}s",
            )
            for sentence, count in pool_hits.items():
                self.assertGreaterEqual(
                    count,
                    5,
                    f"{sentence.strip()} appeared in {count} of {len(seeds)} programs",
                )
        if failures:
            self.fail("\n\n".join(failures))


if __name__ == "__main__":
    unittest.main()
