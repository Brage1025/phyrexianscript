"""Implementations of the built-in verbs (see :mod:`phyx.vocabulary`).

Each implementation receives the interpreter and the already-evaluated
objects, in the order they were written (objects first, verb last)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .errors import RuntimeFault, UserMistake
from .limits import memory_fault, repeat_sequence, take_turns
from .paths import note_hint, resolve_note, resolve_spread
from .values import (
    Ability,
    is_number,
    kind_of,
    parse_number_text,
    to_source,
    to_text,
    truthy,
    type_word,
    values_equal,
)

if TYPE_CHECKING:  # pragma: no cover
    from .interpreter import Interpreter

Impl = Callable[["Interpreter", list], object]
IMPLS: dict[str, Impl] = {}


def verb(word: str):
    def register(fn: Impl) -> Impl:
        IMPLS[word] = fn
        return fn
    return register


def _kinds(*vals: object) -> str:
    return " and ".join(type_word(v) + f" ({kind_of(v)})" for v in vals)


def _need_number(v: object, verb_word: str) -> int:
    if not is_number(v):
        raise RuntimeFault(f"'{verb_word}' needs a number, got {_kinds(v)}")
    return v  # type: ignore[return-value]


def _need_list(v: object, verb_word: str) -> list:
    if not isinstance(v, list):
        raise RuntimeFault(f"'{verb_word}' needs a list, got {_kinds(v)}")
    return v


def _index(coll: list | str, key: object, verb_word: str) -> int:
    if not is_number(key):
        raise RuntimeFault(f"'{verb_word}' needs a number to pick from a {kind_of(coll)}, got {_kinds(key)}")
    n = len(coll)
    i = key if key >= 0 else n + key  # type: ignore[operator]
    if not 0 <= i < n:  # type: ignore[operator]
        raise RuntimeFault(
            f"the {kind_of(coll)} has {to_source(n)} items; there is no item {to_source(key)}")
    return i  # type: ignore[return-value]


def _hashable(key: object, verb_word: str) -> object:
    try:
        hash(key)
    except TypeError:
        raise RuntimeFault(
            f"a book cannot be keyed by a {kind_of(key)} ('{verb_word}')"
        ) from None
    return key


# ---------------------------------------------------------------- arithmetic
@verb("babg")
def _add(interp, args):
    a, b = args
    try:
        if is_number(a) and is_number(b):
            return a + b
        if isinstance(a, str) and isinstance(b, str):
            return a + b
        if isinstance(a, list) and isinstance(b, list):
            return a + b
    except MemoryError:
        raise memory_fault() from None
    raise RuntimeFault(
        f"cannot add {_kinds(a, b)}",
        hint="babg adds two numbers, two texts, or two lists",
    )


@verb("mɒɣg")
def _sub(interp, args):
    a, b = args
    return _need_number(a, "mɒɣg") - _need_number(b, "mɒɣg")


@verb("tøwp")
def _mul(interp, args):
    a, b = args
    if is_number(a) and is_number(b):
        return a * b
    if isinstance(a, (str, list)) and is_number(b):
        return repeat_sequence(a, b, "tøwp (times)")
    raise RuntimeFault(f"cannot multiply {_kinds(a, b)}")


@verb("χɬkevk")
def _div(interp, args):
    a, b = args
    a = _need_number(a, "χɬkevk")
    b = _need_number(b, "χɬkevk")
    if b == 0:
        raise RuntimeFault(
            "nothing can be distributed into zero parts",
            hint="χɬkevk is floor division; the second object is the number of parts and cannot be 0",
        )
    return a // b


@verb("geft")
def _mod(interp, args):
    a, b = args
    a = _need_number(a, "geft")
    b = _need_number(b, "geft")
    if b == 0:
        raise RuntimeFault("nothing remains when dividing by zero")
    return a % b


@verb("ķus'ər")
def _twice(interp, args):
    return _need_number(args[0], "ķus'ər") * 2


@verb("əxķus'ər")
def _half(interp, args):
    return _need_number(args[0], "əxķus'ər") // 2


@verb("lu'f")
def _pow(interp, args):
    a = _need_number(args[0], "lu'f")
    b = _need_number(args[1], "lu'f")
    if b < 0:
        raise RuntimeFault("lu'f (energize) cannot raise to a negative power")
    if b > 10_000:
        raise RuntimeFault("lu'f (energize): the exponent is too great")
    return a ** b


@verb("'uɬč")
def _random(interp, args):
    n = _need_number(args[0], "'uɬč")
    if n <= 0:
        raise RuntimeFault("'uɬč (astray) needs a bound greater than zero")
    return interp.rng.randrange(n)


# ---------------------------------------------------------- comparison/logic
@verb("ǆ'ynpp")
def _eq(interp, args):
    return values_equal(args[0], args[1])


def _ordered(a: object, b: object, word: str) -> tuple:
    if is_number(a) and is_number(b):
        return a, b
    if isinstance(a, str) and isinstance(b, str):
        return a, b
    raise RuntimeFault(f"'{word}' cannot order {_kinds(a, b)}")


@verb("grmɒɣg")
def _lt(interp, args):
    a, b = _ordered(args[0], args[1], "grmɒɣg")
    return a < b


@verb("korxgr")
def _gt(interp, args):
    a, b = _ordered(args[0], args[1], "korxgr")
    return a > b


@verb("əx")
def _not(interp, args):
    return not truthy(args[0])


@verb("xə")
def _and(interp, args):
    return truthy(args[0]) and truthy(args[1])


@verb("ðə")
def _or(interp, args):
    return truthy(args[0]) or truthy(args[1])


@verb("ʁšθakɴ")
def _choose(interp, args):
    cond, a, b = args
    return a if truthy(cond) else b


# -------------------------------------------------------------- input/output
@verb("pihš")
def _speak(interp, args):
    interp.write(to_text(args[0]) + "\n")
    return args[0]


@verb("krepg")
def _reveal(interp, args):
    interp.write(to_source(args[0]) + "\n")
    return args[0]


@verb("'ətsxn")
def _ask(interp, args):
    return interp.read_line(to_text(args[0]))


# ---------------------------------------------------------------- conversion
@verb("asərθ")
def _number(interp, args):
    v = args[0]
    if is_number(v):
        return v
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, str):
        return parse_number_text(v)
    raise RuntimeFault(f"cannot turn {_kinds(v)} into a number")


@verb("xušv")
def _voice(interp, args):
    return to_text(args[0])


@verb("πøkk")
def _type(interp, args):
    return type_word(args[0])


# --------------------------------------------------------------- collections
@verb("ťewn")
def _list(interp, args):
    return list(args)


@verb("tekt")
def _book(interp, args):
    book: dict = {}
    for i in range(0, len(args), 2):
        book[_hashable(args[i], "tekt")] = args[i + 1]
    return book


@verb("ronɣ")
def _turns(interp, args):
    n = _need_number(args[0], "ronɣ")
    return take_turns(n)


@verb("tapq")
def _get(interp, args):
    coll, key = args
    if isinstance(coll, (list, str)):
        return coll[_index(coll, key, "tapq")]
    if isinstance(coll, dict):
        k = _hashable(key, "tapq")
        if k not in coll:
            raise RuntimeFault(f"the book has no entry {to_source(key)}")
        return coll[k]
    raise RuntimeFault(f"cannot get from {_kinds(coll)}")


def put_into(coll: object, key: object, value: object) -> None:
    """``value coll key tapq ţə''`` — assignment into a place."""
    if isinstance(coll, list):
        coll[_index(coll, key, "ţə''")] = value
        return
    if isinstance(coll, dict):
        coll[_hashable(key, "ţə''")] = value
        return
    if isinstance(coll, str):
        raise RuntimeFault("text cannot be changed in place; build a new text instead")
    raise RuntimeFault(f"cannot put into {_kinds(coll)}")


@verb("bɬølπ")
def _fill(interp, args):
    coll, item = args
    _need_list(coll, "bɬølπ").append(item)
    return coll


@verb("čxət'")
def _exile(interp, args):
    coll, key = args
    if isinstance(coll, list):
        return coll.pop(_index(coll, key, "čxət'"))
    if isinstance(coll, dict):
        k = _hashable(key, "čxət'")
        if k not in coll:
            raise RuntimeFault(f"the book has no entry {to_source(key)}")
        return coll.pop(k)
    raise RuntimeFault(f"cannot exile from {_kinds(coll)}")


@verb("'iixtfu'q")
def _first(interp, args):
    coll = args[0]
    if isinstance(coll, (list, str)):
        if not coll:
            raise RuntimeFault(f"an empty {kind_of(coll)} has no beginning")
        return coll[0]
    raise RuntimeFault(f"{_kinds(coll)} has no beginning")


@verb("ǩeǆylqitsodrm")
def _last(interp, args):
    coll = args[0]
    if isinstance(coll, (list, str)):
        if not coll:
            raise RuntimeFault(f"an empty {kind_of(coll)} has no bottom")
        return coll[-1]
    raise RuntimeFault(f"{_kinds(coll)} has no bottom")


@verb("samk")
def _length(interp, args):
    coll = args[0]
    if isinstance(coll, (list, str, dict)):
        return len(coll)
    raise RuntimeFault(f"{_kinds(coll)} has no length")


@verb("dl")
def _in(interp, args):
    item, coll = args
    if isinstance(coll, list):
        return any(values_equal(item, x) for x in coll)
    if isinstance(coll, dict):
        return _hashable(item, "dl") in coll
    if isinstance(coll, str):
        if not isinstance(item, str):
            raise RuntimeFault(f"only text can be found inside text, not {_kinds(item)}")
        return item in coll
    raise RuntimeFault(f"nothing can be inside {_kinds(coll)}")


@verb("rukxtekt")
def _keys(interp, args):
    book = args[0]
    if not isinstance(book, dict):
        raise RuntimeFault(f"'rukxtekt' needs a book, got {_kinds(book)}")
    return list(book.keys())


@verb("tluxt")
def _copy(interp, args):
    v = args[0]
    if isinstance(v, list):
        return list(v)
    if isinstance(v, dict):
        return dict(v)
    return v


@verb("ɣɒzɢ")
def _slice(interp, args):
    coll, start, end = args
    if not isinstance(coll, (list, str)):
        raise RuntimeFault(f"cannot flay {_kinds(coll)}")
    if start is not None:
        _need_number(start, "ɣɒzɢ")
    if end is not None:
        _need_number(end, "ɣɒzɢ")
    return coll[start:end]


@verb("pən'g")
def _split(interp, args):
    text, sep = args
    if not isinstance(text, str) or not isinstance(sep, str):
        raise RuntimeFault(f"'pən'g' breaks text with text, got {_kinds(text, sep)}")
    if sep == "":
        return list(text)
    return text.split(sep)


@verb("raφoj")
def _join(interp, args):
    items, sep = args
    if not isinstance(sep, str):
        raise RuntimeFault(f"'raφoj' links with text, got {_kinds(sep)}")
    return sep.join(to_text(x) for x in _need_list(items, "raφoj"))


# -------------------------------------------------------------------- errors
@verb("ɬšeɴazv")
def _mistake(interp, args):
    raise UserMistake(args[0])


@verb("qab'")
def _kill(interp, args):
    raise SystemExit(_need_number(args[0], "qab'"))


@verb("bukð")
def _cast(interp, args):
    path = args[0]
    if not isinstance(path, str):
        raise RuntimeFault(f"'bukð' (play/cast) wants a path as text, got {_kinds(path)}")
    interp.include(path)
    return None


@verb("naķm")
def _work(interp, args):
    ability = args[0]
    if not isinstance(ability, Ability):
        raise RuntimeFault(f"'naķm' (work) wants an ability, got {_kinds(ability)}")
    return ability


@verb("'uxq")
def _command(interp, args):
    return list(interp.argv)


@verb("čtəčpliɣn")
def _activate(interp, args):
    argv, ability = args
    if not isinstance(ability, Ability):
        raise RuntimeFault(f"'čtəčpliɣn' (activate) wants an ability, got {_kinds(ability)}")
    if not isinstance(argv, list):
        raise RuntimeFault(
            f"'čtəčpliɣn' wants a list of objects before the ability, got {_kinds(argv)}"
        )
    if len(argv) != len(ability.params):
        raise RuntimeFault(
            f"'{ability.name}' wants {len(ability.params)} object"
            f"{'' if len(ability.params) == 1 else 's'}, "
            f"this list has {len(argv)}"
        )
    return interp.call(ability, argv)


@verb("brøtjt")
def _research(interp, args):
    """Read a UTF-8 note from a path (dictionary: research)."""
    path = args[0]
    if not isinstance(path, str):
        raise RuntimeFault(f"'brøtjt' (research) wants a path as text, got {_kinds(path)}")
    p = resolve_note(path, interp.base_dir)
    if p is None:
        raise RuntimeFault(
            f"brøtjt (research) cannot read '{path}'",
            hint=note_hint(path, interp.base_dir),
        )
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as err:
        raise RuntimeFault(
            f"brøtjt (research) cannot read '{path}': {err}",
            hint=note_hint(path, interp.base_dir),
        ) from err


@verb("mɴyrx")
def _spread(interp, args):
    """Write text onto a path (dictionary: fire/spread). Yields the text."""
    text, path = args
    if not isinstance(text, str) or not isinstance(path, str):
        raise RuntimeFault(
            f"'mɴyrx' (spread) writes text onto a path, got {_kinds(text, path)}"
        )
    p = resolve_spread(path, interp.base_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    except (OSError, UnicodeError) as err:
        raise RuntimeFault(f"mɴyrx (spread) cannot write '{path}': {err}") from err
    return text
