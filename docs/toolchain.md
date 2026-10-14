# φyrx toolchain

The interpreter, REPL, and script tools for **φyrx** (PhyrxScript / PhyrexianScript). Language pages: [index.md](index.md). Editor extension: [../editors/README.md](../editors/README.md).

---

## Command line

After `pip install phyx` (or `pip install -e .` from this folder), `phyx`, `phyrx`, `phyrxscript`, and `phyrexianscript` are identical. Without install, use `python -m phyx`.

A path with no subcommand is a program. Remaining words after the file are bound to `'uxq`.

```
python -m phyx                              REPL
python -m phyx FILE [ARG…]                  run
python -m phyx --ascii FILE [ARG…]          run with ASCII spelling
python -m phyx -c CODE [ARG…]               run a string of sentences (subcommand: eval)
python -m phyx repl [--ascii]
python -m phyx run FILE [ARG…]              [--ascii] [--vertical | --horizontal]
python -m phyx check FILE [--ascii]
python -m phyx lint FILE [--ascii]
python -m phyx render FILE [-o out.html] [--title …] [--size 34]
python -m phyx transpose FILE [-o out] [--to-vertical | --to-horizontal] [--gap 1]
python -m phyx translit FILE [--reverse]
python -m phyx fetch
python -m phyx lookup WORD…
python -m phyx words
python -m phyx explain WORD…              English or Phyrexian
python -m phyx fmt FILE [-o out | -i]
python -m phyx bench [--size N] [--loops N]
python -m phyx dis FILE [--ascii]
python -m phyx test [PATH…] [--ascii]
python -m phyx lib
python -m phyx -V
```

`explain` is the lexicon at the moment you need it: `explain if` names `ba`; `explain babg` is add. `fmt` rewrites `-` separators and 4-space indent; `^rukx` notes stay. `lint` names a dropped `'iţpənn`, an unused object, or an English *keyword* used as a name (`if`, `return` — not `fn`, which is a normal binding). ASCII-capital files need `--ascii` on `run` / `check` / `lint` / `dis` / `test` (`examples/07_ascii.phyx`).

`test` runs `test_*.phyx` under the given paths (default `tests/`). A file passes when it finishes without a fault; `ǩaπa` (must) is the assertion. If a sibling `test_foo.expected` exists next to `test_foo.phyx`, stdout must match that UTF-8 text exactly. `lookup` searches the running lexicon (`phyx/vocabulary.py`); a fetched dictionary is extra. `lib` lists the shipped herds in `phyx/lib/`.

`bench` times compiled abilities after parse/compile, against the identical algorithms in Python. `dis` prints the CPython a program compiles to. Pure abilities (no I/O) become ordinary `def` with nested integer expressions and `while cond:`. Equality and ordering keep Phyrexian kinds (`1` is not `əxbytp`). `PHYX_TREEWALK=1` restores the AST walker.

A runtime fault prints the source line, a caret, a **hint** (the next command or the Phyrexian word you wanted), and the **ability stack** when the fault sat inside `ťe`.

`run` / implicit run pass `ARG…` to `'uxq`. `qab'` (kill) is the process exit code.

A first source line `#! /usr/bin/env phyx` is a shebang and is ignored.

---

## Interactive session

```
python -m phyx
```

```
φyrx (PhyrxScript / PhyrexianScript) — a programming language written in Phyrexian.
φyrx>
```

A sentence ending in `.` at column zero runs immediately. A body after `:` continues until a blank line. Abilities defined with `ťe` stay in the session.

| Command | Effect |
| --- | --- |
| `.help` | this language in brief |
| `.words` | markers, verbs, constants |
| `.explain WORD` | one marker, verb, or English word |
| `.names` | names currently bound |
| `.load PATH` | cast a `.phyx` file into the session |
| `.ascii` | toggle ASCII-capital spelling |
| `.quit` | leave |

`'uxq` is empty in the REPL. Use `.load` or `bukð` for files.

---

## Modules

`bukð` (play/cast) runs another file in the current session. Cycles are a grammar mistake.

Search order: the directory of the file that contains the `bukð` (the working directory in the REPL), the current working directory, each directory in `PHYX_PATH`, then the shipped library `phyx/lib/`. A name without a suffix is tried as `.phyx` then `.vphyx`.

`brøtjt` uses that order without `phyx/lib/` (notes are not herds). `mɴyrx` writes next to the file and does not search.

The including parser **sees** the included `ťe` names so you may write them as verbs. The included sentences **run** when `bukð` is evaluated, so the `bukð` sentence must appear *before* any sentence that calls those abilities or reads those bindings.

```
^lo-"compleat.phyx"-bukð.
!30-12-ǩeznasərθ.
```

`python -m phyx check FILE` parses (and follows `bukð` for names) but does not execute. `python -m phyx lib` lists the herds. Full ability list: [stdlib.md](stdlib.md).

Shipped libraries (`phyx/lib/`):

| File | Provides |
| --- | --- |
| `asərθ.phyx` | `abs`, `min`, `max`, `sum`, `ǩeznasərθ` (gcd) |
| `ťewn.phyx` | `map`, `filter`, `reverse`, `sort` |
| `compleat.phyx` | both of the above |

`examples/lib_asərθ.phyx` and `examples/lib_ťewn.phyx` are aliases of those herds.

---

## Vertical script

Phyrexian is read **top to bottom, columns left to right**. A `.phyx` file stores one Phyrexian line per text row (editors prefer that). A `.vphyx` file *is* the vertical layout.

```
python -m phyx transpose examples/01_welcome.phyx
python -m phyx examples/08_vertical.vphyx
python -m phyx render examples/09_sieve.phyx -o sieve.html
```

`render` writes a page in the official card font. The file is `Phyrexian-Regular.ttf`; its **family name is `Phyrexian`** (full name `Phyrexian Regular`). That is the name CSS and Windows use. `python -m phyx render` downloads and **embeds** a validated copy so the page cannot flash Latin fallbacks.

`python -m phyx fetch` also pulls **Basilica** (native hexadecimal glyphs, CC-BY) and, on Windows, installs both into the current user’s font folder so editors can select **Phyrexian**. The lexer already reads those Mathematical Monospace digits as the same hex as `0–9a–f`. Assets live in `assets/` (gitignored). Override the directory with `PHYX_ASSETS`.

---

## ASCII spelling

`--ascii` / `.ascii` / `translit`: an **upper-case** letter (or digraph) is the special letter it most resembles. Lower-case is untouched. Quoted text is untouched.

| Type | Meaning |
| --- | --- |
| `A O E` | `ɒ ø ə` |
| `S Z C J W` | `š ž č ǆ ẅ` |
| `TH DH NG NN LH LZ` | `θ ð ŋ ɴ ɬ ɮ` |
| `P PH T TT K KH GG GH` | `π φ ť ţ ǩ ķ ǧ ǥ` |
| `G X Q R` | `ɣ χ ɢ ʁ` |

So `TTE''` is `ţə''`, `aXEw'` is `aχəw'`, `PHyrx` is `φyrx`.

---

## Project layout

```
phyx/           lexer, parser, CPython compiler, evaluator, REPL, render
phyx/lib/       shipped herds (asərθ, ťewn, compleat)
docs/           index, tour, stdlib, guide, spec, reference, python, cookbook, toolchain, rationale
editors/        Cursor / VS Code extension (`package.json`) + Vim grammars
.github/        CI (`unittest` + `phyx test`) and PyPI publish on GitHub Release
examples/       programs, aliases of the herds, Turing machine, sort, file notes
tests/          python -m unittest discover -s tests -v
tests/phyx/     φyrx tests (`python -m phyx test`)
assets/         font + dictionary after `phyx fetch` (gitignored)
```

---

## Embedding

```python
from phyx import parse, Interpreter, run_source

run_source('!"šdeχd".', argv=["ignored-by-this-program"])
```

`Interpreter(argv=[…], base_dir=…, ascii_mode=…, stdin=…, stdout=…)` is the evaluator. `parse` raises `PhyrexianError` subclasses (`LexError`, `ParseError`); running raises `RuntimeFault` / `UserMistake`. `format_error(err, source)` is the human-readable form with a caret.

---

## CI and the index

GitHub Actions (`.github/workflows/ci.yml`) runs `python -m unittest discover -s tests -v` and `python -m phyx test` on Python 3.11–3.14, then `python -m build` / `twine check`.

A GitHub Release triggers `.github/workflows/publish.yml`, which uploads to PyPI with trusted publishing. Configure a pending publisher on pypi.org for this repository before the first release; the package name is `phyx`.

```
pip install phyx
```
