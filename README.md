# φyrx

[![CI](https://img.shields.io/github/actions/workflow/status/Brage1025/phyrexianscript/ci.yml?branch=main)](https://github.com/Brage1025/phyrexianscript/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/phyx)](https://pypi.org/project/phyx/)
[![Python versions](https://img.shields.io/pypi/pyversions/phyx)](https://pypi.org/project/phyx/)
[![Licence](https://img.shields.io/github/license/Brage1025/phyrexianscript?label=licence)](https://github.com/Brage1025/phyrexianscript/blob/main/LICENSE)

<p><img src="editors/phyx-original.svg" width="128" height="128" alt="φyrx"></p>

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

Cursor / VS Code: [Open VSX](https://open-vsx.org/extension/brage1025/phyx) (Cursor’s in-editor marketplace) and the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=brage1025.phyx) (`brage1025.phyx`). Local install from `editors/` is in [editors/README.md](editors/README.md).

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
| [docs/roadmap.md](docs/roadmap.md) | Known issues, and how language decisions are made |
| [CHANGELOG.md](CHANGELOG.md) | What changed |
| [editors/README.md](editors/README.md) | TextMate and Vim grammars |

Worked programs live in `examples/`: welcome through a Turing machine, list sort, file notes, a command-line script, and `compleat`. The standard library is `phyx/lib/`; `examples/lib_*.phyx` are aliases.

```
python -m phyx test
python -m unittest discover -s tests -v
```

---

## Status

Language version: 1.6

The toolchain version is the [PyPI badge](https://pypi.org/project/phyx/) above.

Python 3.11 to 3.14, as the classifiers in `pyproject.toml` say. It runs on Linux, macOS and Windows (see [CI](https://github.com/Brage1025/phyrexianscript/actions/workflows/ci.yml)).

Known issues: [docs/roadmap.md](docs/roadmap.md).

[Specification](docs/spec.md). [Tour](docs/tour.md). [Reference](docs/reference.md).

---

## Fan content

φyrx is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.
