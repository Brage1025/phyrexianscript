"""Every keyword of φyrx is a real Phyrexian word.

The translation column references the entry in the Phyrexian Dictionary
(https://fxbuson.github.io/PhyrexianDictionary/).  Markers come from the
mood/tense tables in tutorial chapter 3; verbs are dictionary verbs/nouns whose
meaning fits the operation.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# Mood / tense markers — the first word of a phrase, selecting the statement
# --------------------------------------------------------------------------
# word       : (statement kind, gloss)
MARKERS: dict[str, tuple[str, str]] = {
    "xe": ("expr", "indicative — plain statement"),
    "'u": ("const", "past indicative — it already happened: assignments are constant"),
    "lo": ("expr", "imperative — do it (return / stop / next live here)"),
    "ba": ("if", "conditional — if"),
    "bu": ("unless", "negative conditional — if not"),
    "əx": ("unless", 'negative — "not ..., instead ..."'),
    "qit": ("else", "instead — else / catch"),
    "baxuφ": ("while", "if + when = whenever — loop while"),
    "aχəw'": ("for", "each — iterate over a collection"),
    "ťe": ("def", 'potential — "X can Y" defines the ability Y'),
    "ǩaπa": ("assert", "jussive — must: assertion"),
    "baqilx": ("try", 'if would — try; "qit" gives the instead/catch'),
}

# the preposition used by ``aχəw'`` loops: ``aχəw'-ITEM-dl-COLLECTION``
IN_WORD = "dl"  # spatial modifier "in"

# control verbs recognised by the parser
RETURN_WORD = "'iţpənn"  # return
BREAK_WORD = "lups"  # stop
CONTINUE_WORD = "ɢnagɮ"  # next
PUT_WORD = "ţə''"  # put — assignment
GET_WORD = "tapq"  # get — indexing (also an assignment target)
MISTAKE_WORD = "ɬšeɴazv"  # mistake — raise
BLAME_WORD = "dekp"  # blame — the caught mistake inside a ``qit`` handler
CAST_WORD = "bukð"  # play/cast — include another file
QUOTE_WORD = "naķm"  # make/work — the ability itself, not a call
COMMAND_WORD = "'uxq"  # command — the program's argument list


@dataclass(frozen=True)
class Verb:
    word: str
    arity: int  # -1 = takes a count from the stack (N, then N items)
    gloss: str
    doc: str


def _v(word: str, arity: int, gloss: str, doc: str) -> tuple[str, Verb]:
    return word, Verb(word, arity, gloss, doc)


VERBS: dict[str, Verb] = dict(
    [
        # ---- arithmetic -----------------------------------------------------
        _v("babg", 2, "add", "a b → a + b (numbers, strings, lists)"),
        _v("mɒɣg", 2, "reduce", "a b → a - b"),
        _v("tøwp", 2, "times", "a b → a × b (also repeats strings/lists)"),
        _v("χɬkevk", 2, "distribute", "a b → a ÷ b (floor division)"),
        _v("geft", 2, "remaining", "a b → a mod b"),
        _v("ķus'ər", 1, "twice", "a → a × 2"),
        _v("əxķus'ər", 1, "half", "a → a ÷ 2 (rounded down)"),
        _v("lu'f", 2, "energize", "a b → a ** b (integer power; b ≥ 0)"),
        _v("'uɬč", 1, "astray", "n → random number in [0, n)"),
        # ---- comparison / logic --------------------------------------------
        _v("ǆ'ynpp", 2, "equal", "a b → a = b"),
        _v("grmɒɣg", 2, "less than", "a b → a < b"),
        _v("korxgr", 2, "more than", "a b → a > b"),
        _v("əx", 1, "not", "a → not a"),
        _v("xə", 2, "and", "a b → a and b (word modifier 'and')"),
        _v("ðə", 2, "or", "a b → a or b (word modifier 'or')"),
        _v("ʁšθakɴ", 3, "choose", "cond a b → a if cond else b"),
        # ---- binding ---------------------------------------------------------
        _v(PUT_WORD, 2, "put", "value target → target = value (target: name or list/book tapq)"),
        # ---- input / output ---------------------------------------------------
        _v("pihš", 1, "speak", "a → print a"),
        _v("krepg", 1, "reveal", "a → print a in source form (debug)"),
        _v("'ətsxn", 1, "ask", "prompt → read a line of input"),
        # ---- conversion ------------------------------------------------------
        _v("asərθ", 1, "number", "a → number (hexadecimal text, or 1/0 for truth)"),
        _v("xušv", 1, "voice", "a → text"),
        _v("πøkk", 1, "type", "a → the type word of a"),
        # ---- collections -----------------------------------------------------
        _v("ťewn", -1, "list", "x1 … xN N → list of N items"),
        _v("tekt", -1, "book", "k1 v1 … kN vN N → book (map) of N entries"),
        _v("ronɣ", 1, "turn(s)", "n → list 0 … n-1"),
        _v(GET_WORD, 2, "get", "coll key → coll[key] (negative keys count from the end)"),
        _v("bɬølπ", 2, "fill", "list item → append item, gives the list"),
        _v("čxət'", 2, "exile", "coll key → remove and give coll[key]"),
        _v("'iixtfu'q", 1, "beginning", "coll → first item"),
        _v("ǩeǆylqitsodrm", 1, "bottom", "coll → last item"),
        _v("samk", 1, "long", "coll → length"),
        _v(IN_WORD, 2, "in", "item coll → item is in coll"),
        _v("rukxtekt", 1, "notebook", "book → list of its keys"),
        _v("tluxt", 1, "copy", "coll → shallow copy"),
        _v("ɣɒzɢ", 3, "flay", "coll start end → slice coll[start:end]"),
        _v("pən'g", 2, "break", "text sep → split text"),
        _v("raφoj", 2, "link", "list sep → join items with sep"),
        _v("'iţpənn", 0, "return", "(value) → return from the ability"),
        # ---- control ---------------------------------------------------------
        _v(BREAK_WORD, 0, "stop", "leave the loop"),
        _v(CONTINUE_WORD, 0, "next", "next iteration"),
        _v(MISTAKE_WORD, 1, "mistake", "a → raise an error carrying a"),
        _v("qab'", 1, "kill", "code → exit the program"),
        _v("bukð", 1, "play/cast", "path → run that φyrx file (include)"),
        _v("čtəčpliɣn", 2, "activate", "args ability → call a stored ability with a list of objects"),
        _v(QUOTE_WORD, 1, "work", "ability → the ability itself (quote; needed for zero-parameter ťe)"),
        _v(COMMAND_WORD, 0, "command", "→ list of text arguments given to the program"),
        _v("brøtjt", 1, "research", "path → read that UTF-8 text (file dir, cwd, PHYX_PATH; not phyx/lib)"),
        _v("mɴyrx", 2, "spread", "text path → write UTF-8 next to the program (never searches), yield the text"),
    ]
)

# words that evaluate to a fixed value
CONSTANTS: dict[str, object] = {
    "bytp": False,  # false
    "əxbytp": True,  # not-false
    "əixiww": None,  # void
    "'ii": 1,  # one
    "ķu": 2,  # two
    "ķi": 3,  # three
}

# type words returned by ``πøkk``
TYPE_WORDS = {
    "number": "asərθ",
    "text": "rukx",  # note
    "truth": "wija'x",  # faith (trust)
    "void": "əixiww",
    "list": "ťewn",
    "book": "tekt",
    "ability": "ɣwi't",
}

RESERVED = set(MARKERS) | set(VERBS) | set(CONSTANTS) | {"rukx"}
