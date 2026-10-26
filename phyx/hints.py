"""Fix-it text: English → Phyrexian, did-you-mean, ``phyx explain``.

Error messages are the language's real interface (they are read at the
moment something breaks).  Every unknown word should name the Phyrexian
form, not leave the reader in English.
"""

from __future__ import annotations

from .conjugation import CONJUGATIONS, describe_person, lemma_of
from .lexer import transliterate
from .vocabulary import CONSTANTS, MARKERS, TYPE_WORDS, VERBS

# English (and a few symbols) a Python programmer reaches for first.
# Values are the φyrx word they actually wanted.
ENGLISH_TO_PHYX: dict[str, str] = {
    "if": "ba",
    "else": "qit",
    "elif": "qit-ba",
    "unless": "bu",
    "while": "baxuφ",
    "for": "aχəw'",
    "def": "ťe",
    "fn": "ťe",
    "function": "ťe",
    "assert": "ǩaπa",
    "try": "baqilx",
    "except": "qit",
    "catch": "qit",
    "return": "'iţpənn",
    "break": "lups",
    "continue": "ɢnagɮ",
    "true": "əxbytp",
    "false": "bytp",
    "none": "əixiww",
    "null": "əixiww",
    "and": "xə",
    "or": "ðə",
    "not": "əx",
    "print": "pihš",
    "input": "'ətsxn",
    "len": "samk",
    "length": "samk",
    "range": "ronɣ",
    "list": "ťewn",
    "dict": "tekt",
    "map": "tekt",
    "get": "tapq",
    "put": "ţə''",
    "set": "ţə''",
    "assign": "ţə''",
    "add": "babg",
    "plus": "babg",
    "sub": "mɒɣg",
    "subtract": "mɒɣg",
    "mul": "tøwp",
    "times": "tøwp",
    "div": "χɬkevk",
    "mod": "geft",
    "pow": "lu'f",
    "eq": "ǆ'ynpp",
    "equal": "ǆ'ynpp",
    "lt": "grmɒɣg",
    "gt": "korxgr",
    "in": "dl",
    "import": "bukð",
    "include": "bukð",
    "read": "brøtjt",
    "write": "mɴyrx",
    "open": "brøtjt",
    "exit": "qab'",
    "kill": "qab'",
    "error": "ɬšeɴazv",
    "raise": "ɬšeɴazv",
    "type": "πøkk",
    "str": "xušv",
    "int": "asərθ",
    "copy": "tluxt",
    "slice": "ɣɒzɢ",
    "split": "pən'g",
    "join": "raφoj",
    "append": "bɬølπ",
    "pop": "čxət'",
    "first": "'iixtfu'q",
    "last": "ǩeǆylqitsodrm",
    "keys": "rukxtekt",
    "call": "čtəčpliɣn",
    "quote": "naķm",
    "argv": "'uxq",
}

# Moods a Python programmer writes as the first word after ``^``.
ENGLISH_MARKERS: dict[str, str] = {
    "if": "ba",
    "else": "qit",
    "elif": "qit-ba",
    "unless": "bu",
    "while": "baxuφ",
    "for": "aχəw'",
    "def": "ťe",
    "fn": "ťe",
    "function": "ťe",
    "assert": "ǩaπa",
    "try": "baqilx",
    "except": "qit",
    "catch": "qit",
}

PUNCTUATION_HELP: dict[str, str] = {
    "^": "start a statement (indicative by default)",
    "!": "start an exclamation — speak (print) the phrase",
    "?": "start a question — ask, store the reply in the last word",
    ".": "end this sentence",
    ":": "this sentence opens a body (the next sentences are indented)",
    "-": "word separator (a newline is also a separator)",
    ",": "phrase barrier: values to the left cannot be objects of later verbs",
}

GLOSS_EXTRA: dict[str, str] = {
    "qit-ba": "else-if: write ^qit-ba-COND: after a ba sentence",
}

# Names that are English *statement* keywords.  Bound names such as ``fn``
# (a stored ability) are not mistakes — only these, used as names, are.
ENGLISH_NAME_TRAPS: frozenset[str] = frozenset({
    "if", "else", "elif", "unless", "while", "for", "def", "function",
    "assert", "try", "except", "catch", "return", "break", "continue",
    "true", "false", "none", "null", "and", "or", "not",
    "print", "import", "class", "async", "await", "lambda",
    "from", "with", "yield", "pass", "raise",
})


def search_lexicon(query: str) -> list[tuple[str, str, str, str]]:
    """Rows ``(word, gloss, kind, extra)`` from the running lexicon.

    ``phyx lookup`` uses this so a search does not need ``phyx fetch``.
    Matches the Phyrexian spelling, an English gloss, a conjugation, or
    an English alias from ``ENGLISH_TO_PHYX``.
    """
    needles = {n for n in (query, query.lower(), transliterate(query)) if n}
    hits: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(word: str, gloss: str, kind: str, extra: str = "") -> None:
        key = (word, kind)
        if key in seen:
            return
        seen.add(key)
        hits.append((word, gloss, kind, extra))

    def matches(*parts: object) -> bool:
        hay = " ".join(str(p) for p in parts if p is not None)
        low = hay.lower()
        return any(n in hay or n.lower() in low for n in needles)

    mapped = ENGLISH_TO_PHYX.get(query.lower())
    seeds = list(needles)
    if mapped:
        seeds.append(mapped)

    for w, (kind, gloss) in MARKERS.items():
        if w in seeds or matches(w, kind, gloss):
            add(w, gloss, "marker", kind)
    for v in VERBS.values():
        if v.word in seeds or matches(v.word, v.gloss, v.doc):
            add(v.word, v.gloss, "verb", v.doc)
    for w, val in CONSTANTS.items():
        if w in seeds or matches(w, val):
            add(w, _shown_constant(val), "constant", "")
    for form, conj in CONJUGATIONS.items():
        if form in needles or form in seeds:
            v = VERBS[conj.lemma]
            add(
                form,
                v.gloss,
                "conjugation",
                f"{conj.doing}→{conj.receiving} of {conj.lemma}",
            )
            add(conj.lemma, v.gloss, "verb", v.doc)
    for n in list(needles):
        lemma = lemma_of(n)
        if lemma is not None and lemma in VERBS:
            v = VERBS[lemma]
            add(lemma, v.gloss, "verb", v.doc)
    if mapped:
        if mapped in MARKERS:
            kind, gloss = MARKERS[mapped]
            add(mapped, gloss, "marker", kind)
        elif mapped in VERBS:
            v = VERBS[mapped]
            add(v.word, v.gloss, "verb", v.doc)
        elif mapped in CONSTANTS:
            add(mapped, _shown_constant(CONSTANTS[mapped]), "constant", "")
    return hits


def _shown_constant(val: object) -> str:
    from .values import to_source

    return to_source(val)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def candidates(extra: list[str] | tuple[str, ...] = ()) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for w in (
        list(VERBS)
        + list(MARKERS)
        + list(CONSTANTS)
        + list(TYPE_WORDS.values())
        + list(extra)
    ):
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def did_you_mean(word: str, extra: list[str] | tuple[str, ...] = (), n: int = 3) -> list[str]:
    """Closest lexicon words, cheapest first.  Empty if nothing is close."""
    if not word:
        return []
    pool = candidates(extra)
    scored: list[tuple[int, str]] = []
    low = word.lower()
    for c in pool:
        d = min(levenshtein(word, c), levenshtein(low, c.lower()))
        limit = 1 if len(word) <= 3 else 2 if len(word) <= 6 else 3
        if 0 < d <= limit:
            scored.append((d, c))
    scored.sort()
    return [c for _, c in scored[:n]]


def _label(word: str) -> str:
    if word in VERBS:
        v = VERBS[word]
        return f"'{word}' ({v.gloss})"
    if word in MARKERS:
        return f"'{word}' ({MARKERS[word][1].split(' — ')[0]})"
    if word in CONSTANTS:
        return f"'{word}'"
    return f"'{word}'"


def hint_for_unknown(word: str, extra: list[str] | tuple[str, ...] = ()) -> str:
    """What to do next when a name is not bound."""
    lemma = lemma_of(word)
    if lemma is not None and lemma != word:
        return (
            f"'{word}' is a conjugation of {_label(lemma)}. "
            f"python -m phyx explain {lemma}"
        )
    low = word.lower()
    if low in ENGLISH_TO_PHYX:
        phy = ENGLISH_TO_PHYX[low]
        return (
            f"'{word}' is English, not Phyrexian. Write {_label(phy)}.  "
            f"python -m phyx explain {phy}"
        )
    found = did_you_mean(word, extra)
    if found:
        shown = " or ".join(_label(w) for w in found)
        return f"did you mean {shown}?  python -m phyx explain {found[0]}"
    return (
        f"bind it first: ^xe-VALUE-{word}-ţə''.  "
        "Or run `python -m phyx words` for the lexicon."
    )


def explain_word(query: str) -> str | None:
    """Human description of a marker, verb, constant, or English alias. None if unknown."""
    raw = query.strip()
    if not raw:
        return None
    if raw in PUNCTUATION_HELP:
        return f"{raw}    punctuation\n        {PUNCTUATION_HELP[raw]}"
    key = raw
    via = None
    conj = CONJUGATIONS.get(raw)
    low = raw.lower()
    if conj is not None:
        via = (
            f"{raw} is {conj.lemma} inflected "
            f"{describe_person(conj.doing)}→{describe_person(conj.receiving)} "
            "(tutorial ch. 3); tense is the mood marker, not the verb"
        )
        key = conj.lemma
    elif key not in VERBS and key not in MARKERS and key not in CONSTANTS \
            and key not in TYPE_WORDS.values() and key not in GLOSS_EXTRA:
        if low in ENGLISH_TO_PHYX:
            via = raw
            key = ENGLISH_TO_PHYX[low]
        else:
            guesses = did_you_mean(raw)
            if guesses:
                key = guesses[0]
                via = raw
            else:
                return None
    lines: list[str] = []
    if conj is not None:
        lines.append(via)
        via = None
    elif via is not None and via != key:
        lines.append(f"{via} → {key}   (English / nearby word)")
    if key in MARKERS:
        kind, gloss = MARKERS[key]
        lines.append(f"{key}    mood marker / {kind}")
        lines.append(f"        {gloss}")
        lines.append("        first word of a phrase after ^")
    elif key in VERBS:
        v = VERBS[key]
        ar = "N items, then a count" if v.arity == -1 else (
            "no objects" if v.arity == 0 else
            ("1 object" if v.arity == 1 else f"{v.arity} objects")
        )
        lines.append(f"{v.word}    verb / {ar}    {v.gloss}")
        lines.append(f"        {v.doc}")
        lines.append("        objects first, this word last")
    elif key in CONSTANTS:
        lines.append(f"{key}    constant    {_shown_constant(CONSTANTS[key])}")
    elif key in TYPE_WORDS.values():
        eng = next(k for k, val in TYPE_WORDS.items() if val == key)
        lines.append(f"{key}    type word for {eng} (returned by πøkk)")
    elif key in GLOSS_EXTRA:
        lines.append(f"{key}    {GLOSS_EXTRA[key]}")
    english = sorted(
        en for en, phy in ENGLISH_TO_PHYX.items()
        if phy == key or phy.startswith(key + "-")
    )
    if english:
        lines.append("        English: " + ", ".join(english))
    lines.append("        python -m phyx words    for the full lexicon")
    return "\n".join(lines)


def explain_missing(query: str) -> str:
    guesses = did_you_mean(query)
    extra = f" Nearby: {', '.join(guesses)}." if guesses else ""
    return (
        f"nothing named {query!r} in φyrx.{extra}  "
        "python -m phyx words    python -m phyx lookup " + query
    )
