"""Verb conjugation from dictionary tutorial chapter 3.

Phyrexian does *not* put tense on the verb. Tense and mood sit on the
phrase-initial marker (``xe``, ``'u``, ``ba``, …). The verb inflects for
**who does the action** and **who receives it**, by inserting a vowel
before the last consonant.

Persons: 1 me, 2 you, 3 they, 4 one (unspecified / a second third party).
The dictionary lemma is 3→3 (they / them) with no extra vowel — that is
the form φyrx already used. Other cells of the table are the same verb.

Rounding (``i→y``, ``e→ø``) and metallicising (``p→π→φ``, …) follow the
tutorial. Ambiguous cells (1→2 equals 1→4) map to the same spelling.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lexer import CONSONANTS
from .vocabulary import CONSTANTS, MARKERS, VERBS

PERSON = {1: "me", 2: "you", 3: "they", 4: "one"}

ROUND = {"i": "y", "e": "ø"}
METAL = {
    "p": "π",
    "π": "φ",
    "t": "ť",
    "ť": "ţ",
    "k": "ǩ",
    "ǩ": "ķ",
    "q": "ǧ",
    "ǧ": "ǥ",
}

# (doing, receiving): round stem, metal stem, metal last, inserted vowel(s)
# Tutorial table for "defile" (zept). 3→3 is the lemma (no change).
_CELLS: dict[tuple[int, int], tuple[bool, bool, bool, str]] = {
    (1, 1): (False, False, False, "o"),
    (2, 1): (False, False, False, "aa"),
    (3, 1): (False, False, True, "a"),
    (4, 1): (False, False, False, "a"),
    (1, 2): (True, False, False, "a"),
    (2, 2): (True, False, False, "u"),
    (3, 2): (True, False, False, ""),
    (4, 2): (True, False, False, "e"),
    (1, 3): (False, True, False, "a"),
    (2, 3): (False, True, False, "u"),
    (3, 3): (False, False, False, ""),
    (4, 3): (False, False, False, "y"),
    (1, 4): (True, False, False, "a"),
    (2, 4): (False, False, False, "ø"),
    (3, 4): (False, False, False, "e"),
    (4, 4): (False, False, False, "ee"),
}


@dataclass(frozen=True)
class Conjugation:
    lemma: str
    doing: int
    receiving: int
    form: str


def split_root(word: str) -> tuple[str, str] | None:
    """Stem + last consonant. None if the word cannot take a relational infix."""
    last_c = -1
    for i in range(len(word) - 1, -1, -1):
        if word[i] in CONSONANTS:
            last_c = i
            break
    if last_c <= 0:
        return None
    return word[:last_c], word[last_c:]


def _round_stem(stem: str) -> str:
    for i in range(len(stem) - 1, -1, -1):
        if stem[i] in ROUND:
            return stem[:i] + ROUND[stem[i]] + stem[i + 1 :]
    return stem


def _metal_stem(stem: str) -> str:
    for i in range(len(stem) - 1, -1, -1):
        if stem[i] in METAL:
            return stem[:i] + METAL[stem[i]] + stem[i + 1 :]
    return stem


def _metal_last(last: str) -> str:
    ch = last[0]
    if ch in METAL:
        return METAL[ch] + last[1:]
    return last


def inflect(lemma: str, doing: int, receiving: int) -> str | None:
    """Spell ``lemma`` for subject ``doing`` and object ``receiving`` (1–4)."""
    parts = split_root(lemma)
    if parts is None:
        return None
    stem, last = parts
    round_s, metal_s, metal_l, insert = _CELLS[doing, receiving]
    if round_s:
        stem = _round_stem(stem)
    if metal_s:
        stem = _metal_stem(stem)
    if metal_l:
        last = _metal_last(last)
    return stem + insert + last


def _build_table() -> dict[str, Conjugation]:
    table: dict[str, Conjugation] = {}
    for lemma in VERBS:
        for doing in range(1, 5):
            for receiving in range(1, 5):
                form = inflect(lemma, doing, receiving)
                if form is None or form == lemma:
                    continue
                if form in VERBS or form in MARKERS or form in CONSTANTS:
                    continue
                existing = table.get(form)
                if existing is not None and existing.lemma != lemma:
                    continue
                if existing is None:
                    table[form] = Conjugation(lemma, doing, receiving, form)
    return table


CONJUGATIONS: dict[str, Conjugation] = _build_table()


def lemma_of(word: str) -> str | None:
    """Lemma if ``word`` is a dictionary verb or a conjugation of one."""
    if word in VERBS:
        return word
    found = CONJUGATIONS.get(word)
    return found.lemma if found else None


def describe_person(n: int) -> str:
    return PERSON[n]
