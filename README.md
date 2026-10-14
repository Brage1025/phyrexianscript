# φyrx

**Also known as PhyrxScript and PhyrexianScript.**

φyrx is a programming language written in Phyrexian. Its orthography, vocabulary, and grammar are not invented: they come from the community [Phyrexian Dictionary](https://fxbuson.github.io/PhyrexianDictionary/) (tutorial chapters 1–3). A program is a sequence of Phyrexian sentences. The verb comes last. Numbers are hexadecimal. Text is read in vertical columns.

The toolchain is a small Python 3.11+ interpreter with no third-party dependencies. The language and interpreter are **MIT**. The optional font and dictionary JSON are **GPL-3.0** and are fetched, not vendored. Source: [github.com/Brage1025/phyrexianscript](https://github.com/Brage1025/phyrexianscript).

```
python -m phyx examples/01_welcome.phyx
```

```
šdeχd-keθəɢð
x: 5 x+10: 15
jnaķm
```

---

## Names

| Name | Use |
| --- | --- |
| **φyrx** | native short name (romanised `phyx`) |
| **PhyrxScript** | English name of the language |
| **PhyrexianScript** | full English name; also this project’s folder |

All three name the same language. After `pip install -e .` the commands `phyx`, `phyrx`, `phyrxscript`, and `phyrexianscript` are the same toolchain.

---

## Install

```
pip install phyx
phyx examples/01_welcome.phyx
```

From this folder, without the index:

```
cd PhyrexianScript
python -m phyx examples/01_welcome.phyx     # no install required
pip install -e .                            # optional: phyx on PATH
phyx examples/01_welcome.phyx
```

Cursor / VS Code: [φyrx on the Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=brage1025.phyx) (`brage1025.phyx`). Local install from `editors/` is in [editors/README.md](editors/README.md).

Typing `ţ` is painful. `--ascii` lets a capital stand for the special letter it resembles (`TTE''` → `ţə''`):

```
python -m phyx --ascii examples/07_ascii.phyx
python -m phyx fetch                        # official Phyrexian font + dictionary
python -m phyx render examples/01_welcome.phyx -o welcome.html   # embeds the font
```

---

## A program is a file

```
python -m phyx                              # interactive session
python -m phyx examples/09_sieve.phyx
python -m phyx examples/10_command.phyx red blue
python -m phyx -c "!1-2-babg."
python -m phyx words                        # every marker, verb, constant
python -m phyx explain if                   # English → Phyrexian (ba)
python -m phyx lookup add
python -m phyx fmt examples/01_welcome.phyx
python -m phyx lint examples/12_sort.phyx
python -m phyx lib                          # shipped herds (asərθ, ťewn, compleat)
python -m phyx test                         # tests written in φyrx (tests/phyx/)
python -m phyx new NAME                     # shebang program + test_NAME.phyx
python -m phyx lsp                          # language server (editor extension starts this)
python -m phyx bench
python -m phyx dis examples/03_abilities.phyx
```

Inside a program, `'uxq` (command) is the list of arguments. A first line `#! /usr/bin/env phyx` is ignored. `naķm` (work) quotes an ability so a zero-parameter `ťe` can be stored and activated.

```
^ťe-greet:
    !"šdeχd".
^xe-greet-naķm-fn-ţə''.
^lo-0-ťewn-fn-čtəčpliɣn.
```

---

## Documentation

| Document | Contents |
| --- | --- |
| [docs/index.md](docs/index.md) | Map of every page |
| [docs/tour.md](docs/tour.md) | First program, no Phyrexian assumed |
| [docs/guide.md](docs/guide.md) | How to write and how to think in φyrx |
| [docs/stdlib.md](docs/stdlib.md) | Shipped herds (`abs`, `sort`, `map`, …) and `bukð` search path |
| [docs/spec.md](docs/spec.md) | Language specification (normative) |
| [docs/reference.md](docs/reference.md) | Types, verbs, sentences, grammar, errors |
| [docs/python.md](docs/python.md) | Map from Python (what is the same, what is not) |
| [docs/cookbook.md](docs/cookbook.md) | Short recipes |
| [docs/toolchain.md](docs/toolchain.md) | CLI, REPL, modules, tests, vertical script, ASCII |
| [docs/rationale.md](docs/rationale.md) | Why the language is this shape |
| [docs/remaining.md](docs/remaining.md) | What still needs to be done |
| [CHANGELOG.md](CHANGELOG.md) | What changed |
| [editors/README.md](editors/README.md) | TextMate and Vim grammars |

Worked programs live in `examples/`: welcome through a Turing machine, list sort, file notes, a command-line script, and `compleat`. The standard library is `phyx/lib/`; `examples/lib_*.phyx` are aliases.

```
python -m phyx test
python -m unittest discover -s tests -v
```

---

## Status

φyrx 1.6.3 (PhyrxScript / PhyrexianScript) is a Turing-complete language that compiles to CPython. Unbounded lists, `baxuφ`, and recursive `ťe` run a Turing machine (`examples/11_machine.phyx`). Pure abilities compile to ordinary Python `def` with nested `return fib(n-1)+fib(n-2)` and `while i < n:`. After compile, `python -m phyx bench` is typically within a small factor of CPython on recursive `fib` and a tight loop (equality and ordering keep Phyrexian kinds, so they are not raw Python `==`).

The standard library is φyrx: `phyx/lib/` is on the `bukð` search path. `python -m phyx test` runs tests written in φyrx (`ǩaπa` is the assertion; a sibling `.expected` file is exact stdout). `python -m phyx lookup` searches the lexicon without a fetch. TextMate and Vim grammars live in `editors/`.

Faults name the fix and the ability stack. `python -m phyx explain if` answers in Phyrexian. `fmt` and `lint` keep a file canonical and catch a dropped `'iţpənn`.

It has binding, closures, first-class abilities, lists and books, modules, UTF-8 notes on disk (`brøtjt` / `mɴyrx`), program arguments, a REPL, vertical rendering in the official Phyrexian font, a [language spec](docs/spec.md), a [tour](docs/tour.md) for someone who has never seen Phyrexian, and docs aimed at someone arriving from Python.

Verbs may take chapter-3 person inflection (`babeg` is `babg`); tense is the mood marker. Numerals may be Arabic hex or Basilica Mathematical Monospace.

Phyrexian script, romanisation, grammar and lexicon: [fxbuson/PhyrexianDictionary](https://fxbuson.github.io/PhyrexianDictionary/). See [docs/reference.md](docs/reference.md#provenance) for the mapping and the licence split.
