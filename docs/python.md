# φyrx for Python programmers

φyrx is not a reskin of Python. It is SOV Phyrexian: objects first, verb last, hexadecimal numbers, mood markers instead of keywords. It **runs on CPython** — abilities compile to `def`, loops to `while` / `for`, integers are Python `int` (unbounded). `python -m phyx bench` times that against the same algorithm in Python.

This page is a map, not a second grammar. The grammar lives in [reference.md](reference.md). How to think in sentences lives in [guide.md](guide.md). First program: [tour.md](tour.md). Herds: [stdlib.md](stdlib.md).

---

## What is the same

| Python | φyrx |
| --- | --- |
| `int` unbounded | `asərθ` — same host integers, written in hex |
| `str` | `rukx` (text / note) |
| `list` | `ťewn` |
| `dict` | `tekt` (book) |
| `bool` | `wija'x` — `əxbytp` / `bytp` |
| `None` | `əixiww` |
| `def` / first-class functions | `ťe` / `ɣwi't` — quote with `naķm`, call a stored one with `čtəčpliɣn` |
| `while` / `for` / `if` / `else` | `baxuφ` / `aχəw'` / `ba` / `qit` |
| `return` / `break` / `continue` | `'iţpənn` / `lups` / `ɢnagɮ` |
| `try` / `except` | `baqilx` / `qit` (`dekp` is the blame) |
| `print` / `input` | `!` or `pihš` / `?` or `'ətsxn` |
| `len` / `range` / `in` | `samk` / `ronɣ` / `dl` |
| `open` read / write | `brøtjt` (research) / `mɴyrx` (spread) |
| `sys.argv[1:]` | `'uxq` |
| `import` | `bukð` (play/cast another `.phyx`) |
| CPython eval loop | φyrx compiles to it (`python -m phyx dis FILE`) |

---

## What is different on purpose

| Python | φyrx |
| --- | --- |
| `1 + 2 * 3` and precedence | postfix: `2-3-tøwp-1-babg` — no operators |
| decimal `10` | hex `0a`; `10` is sixteen |
| `if x:` as a keyword | `^ba-x:` — `ba` is the dictionary’s conditional mood |
| `def f(a, b):` | `^ťe-a-b-f:` — objects, then the name |
| `f(1, 2)` | `1-2-f` |
| classes, floats, async, comprehensions | not in the dictionary; model records as books |
| `True` | **not-false**: `əxbytp` |
| `x = 1` | `^xe-1-x-ţə''.` — **value, then place** |
| `# comment` | `^rukx comment` |
| `{` `}` or indentation-only blocks | `:` then a deeper indent, same as Python’s indent rule |
| `a and b` yields `b` if both truthy | `xə` yields **truth** (`əxbytp` / `bytp`); both sides always run |
| `a if c else b` skips the other arm | `ʁšθakɴ` evaluates **cond, a, and b** (postfix objects) |
| `1 == True` | `1-əxbytp-ǆ'ynpp` is false: number and truth are different kinds |
| English tense on the verb (`added`) | person on the verb (`babeg` = they→one of `babg`); tense is `xe` / `'u` |

A program is a sequence of **sentences**. Each starts with `^`, `!`, or `?` and ends with `.` (or `:` if a body follows).

---

## A side-by-side script

```python
from pathlib import Path

xs = [3, 1, 2]
total = 0
for x in xs:
    total += x
Path("out.txt").write_text(str(total), encoding="utf-8")
print(Path("out.txt").read_text(encoding="utf-8"))
```

```
^xe-3-1-2-3-ťewn-xs-ţə''.
^xe-0-total-ţə''.
^aχəw'-x-dl-xs:
    ^xe-total-x-babg-total-ţə''.
^lo-total-xušv-"out.txt"-mɴyrx.
!"out.txt"-brøtjt.
```

`xušv` is “voice”: turn a value into text (hex for numbers). `mɴyrx` spreads that text onto a path next to the program; `brøtjt` researches it back (file dir, cwd, `PHYX_PATH`).

---

## Standard library (cast, don’t import)

Python’s `import math` is a file of abilities here:

```
^lo-"compleat.phyx"-bukð.      abs min max sum ǩeznasərθ map filter reverse sort
```

`bukð` searches the file's directory, the working directory, `PHYX_PATH`, then `phyx/lib/`. You may omit `.phyx`. `python -m phyx lib` lists what is shipped. Details: [stdlib.md](stdlib.md).

---

## Speed

`python -m phyx bench` times the compiled ability, not the parser. Recursive `fib(16)` was 1.6× CPython before the guarded operators and 2.8× after; a 20000-turn loop was 2.2× and is 4.0×. Arithmetic uses Python's operator only when both values are numbers, and `əx` uses φyrx truth, so a fault inside a pure ability is a `RuntimeFault`. Pure abilities are still ordinary Python `def`s. `python -m phyx explain if` is the glossary for someone whose hands still type Python. Sentences that print, read files, or index collections keep Phyrexian type faults.

The old AST walker is `PHYX_TREEWALK=1` — about a hundred times slower, same results.

A name the compiler can prove is bound before the read — a parameter, a hoisted ability, or a local assigned on every path before that read — is a direct Python load. `fib` and a counted loop stay ordinary Python. A name it cannot prove is bound is loaded with a check that raises unknown word, with the hint and line, instead of `UnboundLocalError`. The check is only on those reads.

ASCII-capital spelling (`TTE''` for `ţə''`) is `--ascii`, including on `check`, `lint`, and `dis`. `python -m phyx lint` does not treat `fn` as a mistake: that is the usual name for a stored ability.

---

## What Python still does that φyrx will not

Floats, classes, decorators, async, the C stdlib (`json`, `re`, `pathlib` beyond read/write). Embed φyrx from Python when you need those:

```python
from phyx import run_source, Interpreter

interp = run_source("^xe-1-x-ţə''.")
# interp.globals.vars["x"] == 1
```

Or call out: write a `.phyx` that `mɴyrx`s a note, and let a Python tool consume it.

Rivaling Python means: same integers, same eval loop, same “a file is a program”, a REPL, modules, files, and documentation that does not assume you already speak Phyrexian. It does not mean infix `+`.
