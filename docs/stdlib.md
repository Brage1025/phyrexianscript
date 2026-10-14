# Standard library

The dictionary does not have verbs for *min*, *sort*, or *map*. Those are **herds**: ordinary `ťe` abilities shipped in `phyx/lib/` and cast with `bukð` (play/cast). They are φyrx, not host Python.

```
^lo-"compleat.phyx"-bukð.
!3-1-2-3-ťewn-sort.
!əx0a-abs.
```

```
python -m phyx lib
```

---

## Search path

`bukð` looks for a text in this order:

1. The directory of the file that contains the `bukð` (the working directory in the REPL)
2. The current working directory
3. Each directory in `PHYX_PATH` (the platform path separator)
4. The shipped library, `phyx/lib/` next to the interpreter

A name without a suffix is tried as `.phyx`, then `.vphyx`. Absolute paths are used as written.

Cycles (`a.phyx` casts `b.phyx` which casts `a.phyx`) are a grammar fault.

Notes on disk are not herds. `brøtjt` (research) *reads*: file directory, working directory, `PHYX_PATH` — not `phyx/lib/`. The path is used as written. `mɴyrx` (spread) *writes* next to the program that contains it and never searches, so a short name cannot land in the shipped library.

**Cast first, then call.** The parser reads included `ťe` names so you may write them as verbs; the included sentences run when `bukð` itself is evaluated.

`examples/lib_asərθ.phyx` and `examples/lib_ťewn.phyx` are aliases of the shipped herds, so older programs that cast those names still run.

---

## `asərθ.phyx` — numbers

Cast: `^lo-"asərθ.phyx"-bukð.` or `^lo-"asərθ"-bukð.`

| Ability | Objects | Result |
| --- | --- | --- |
| `abs` | `n` | `n` if `n ≥ 0`, otherwise `0 − n` |
| `ǩeznasərθ` | `a` `b` | greatest common divisor (Euclid; remaining / `geft` until `b` is 0) |
| `min` | `a` `b` | the lesser (`grmɒɣg`) |
| `max` | `a` `b` | the greater (`korxgr`) |
| `sum` | `xs` | add every item of the list, starting from 0 |

```
^lo-"asərθ.phyx"-bukð.
!əx0a-abs.
!30-12-ǩeznasərθ.
!ķi-9-min,ķi-9-max.
!1-2-3-3-ťewn-sum.
```

Speaks: `0a`, `6`, `3 9`, `6`.

---

## `ťewn.phyx` — lists

Cast: `^lo-"ťewn.phyx"-bukð.`

| Ability | Objects | Result |
| --- | --- | --- |
| `map` | `xs` `fn` | `fn` applied to each item |
| `filter` | `xs` `fn` | items for which `fn` is true |
| `reverse` | `xs` | the list, last item first |
| `sort` | `xs` | insertion sort, least first (`grmɒɣg`) |

`map` and `filter` want an **ability**, not a call. A zero-parameter `ťe` must be quoted with `naķm` (work). A `ťe` that takes objects is quoted the same way when you pass it as an object:

```
^lo-"ťewn.phyx"-bukð.
^ťe-n-dub:
    ^lo-n-ķus'ər-'iţpənn.
^ťe-n-odd:
    ^lo-n-ķu-geft-'iţpənn.

!1-2-3-3-ťewn-dub-naķm-map.
!1-2-3-3-ťewn-odd-naķm-filter.
!3-1-2-3-ťewn-sort.
```

`odd` returns the remainder modulo two, which is true when the number is odd.

`sort` copies the list (`tluxt`) and does not change the original.

---

## `compleat.phyx` — both herds

Cast: `^lo-"compleat.phyx"-bukð.`

This file only casts `asərθ.phyx` and `ťewn.phyx`. After it, `abs`, `sum`, `sort`, `map`, and the rest are all verbs.

See `examples/12_sort.phyx` and `examples/14_compleat.phyx`.

---

## Tests of the herds

The herds are programs, so they are tested as programs:

```
python -m phyx test tests/phyx
```

`tests/phyx/test_*.phyx` uses `ǩaπa` (must). Core sentences (abilities, loops, list counts) live next to the herd tests. A sibling `.expected` file is exact stdout when the test speaks. Adding a herd means adding a `ťe` in `phyx/lib/` and a `ǩaπa` in `tests/phyx/`.

Your own herds belong on `PHYX_PATH` or next to the file that casts them. Do not invent lexicon verbs for operations the dictionary does not name; write a `ťe` and cast it.
