# Contributing to φyrx

φyrx (PhyrxScript / PhyrexianScript) is a programming language written in Phyrexian. The language contract is [docs/spec.md](docs/spec.md). Design constraints are in [docs/rationale.md](docs/rationale.md).

## Setup

Python 3.11 or newer, from `requires-python` in [pyproject.toml](pyproject.toml). Create a virtual environment, then install the package with the `dev` extra (`ruff`, `coverage`, `build`, `twine`):

```
python -m venv .venv
```

PowerShell:

```
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

POSIX:

```
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

`.venv/` is gitignored.

## Checks before a pull request

These pass on the compiled engine, which is the default, and again with the tree-walker:

```
python -m unittest discover -s tests -v
python -m phyx test
ruff check .
```

The same two test commands with `PHYX_TREEWALK=1`:

```
PHYX_TREEWALK=1 python -m unittest discover -s tests -v
PHYX_TREEWALK=1 python -m phyx test
```

PowerShell:

```
$env:PHYX_TREEWALK = "1"
python -m unittest discover -s tests -v
python -m phyx test
Remove-Item Env:PHYX_TREEWALK
```

The compiled engine ([phyx/compiler.py](phyx/compiler.py)) and the tree-walker ([phyx/interpreter.py](phyx/interpreter.py)) behave identically. A change to semantics needs a parity test in [tests/test_engine_parity.py](tests/test_engine_parity.py). `assertParity` runs one source on both engines and fails when the results differ.

The out-of-memory fault test runs on Linux only. macOS does not enforce `RLIMIT_AS`, and Windows has no `resource` module. See [docs/toolchain.md](docs/toolchain.md#ci-and-the-index).

## Branch flow

One topic per branch. Fork the repository, use any descriptive branch name, and open a pull request against main. `main` receives the work through a pull request. Write the failing test first, show it failing, then fix it.

Leave the version number in [pyproject.toml](pyproject.toml) alone unless a maintainer asks for a bump. Files are UTF-8 with LF line endings. Do not commit `dist/`, `*.egg-info`, `*.vsix`, `__pycache__/`, `examples/*.html`, or `assets/`.

## Language rules

The language admits dictionary words and dictionary syntax. Floats, classes, infix operators, and decimal literals are outside it. If a change needs a word or a sentence form the dictionary does not have, stop and ask. The constraint is [docs/rationale.md](docs/rationale.md). [AGENTS.md](AGENTS.md) records the same rule for this repository.

The community dictionary is the one named in [docs/reference.md](docs/reference.md#provenance). This repository does not vendor it. The words the interpreter accepts are the lexicon in [phyx/vocabulary.py](phyx/vocabulary.py). `python -m phyx lookup` searches that file. `python -m phyx fetch` downloads the font and the dictionary JSON into `assets/` (gitignored). That download is extra. See [docs/toolchain.md](docs/toolchain.md).

## Behaviour changes

[docs/spec.md](docs/spec.md) is the language contract. A behaviour change updates [docs/spec.md](docs/spec.md), [docs/reference.md](docs/reference.md), and the Unreleased section of [CHANGELOG.md](CHANGELOG.md) in the same branch. Every fault that reaches a person is a Phyrexian error with a hint.

## Add a verb

A new verb is a dictionary word whose meaning fits an operation. See [docs/rationale.md](docs/rationale.md).

1. Add the lemma to `VERBS` in [phyx/vocabulary.py](phyx/vocabulary.py).
2. Implement it in [phyx/builtins.py](phyx/builtins.py) with the `@verb` decorator. A verb that is not in the compiler's inline set is called from that table by both engines. `_INLINE_VERBS` in [phyx/compiler.py](phyx/compiler.py) is `_BIN`, `_UNARY`, and `ʁšθakɴ`, `ťewn`, `tekt`, `ronɣ`. The compiler emits those directly. A change to one of them is made on the compiled path and on the tree-walker path.
3. Add a row to the verb table in [docs/reference.md](docs/reference.md#standard-verbs). [tests/test_docs.py](tests/test_docs.py) fails when a lexicon verb is missing from that page, written in backticks.
4. Add a parity test in [tests/test_engine_parity.py](tests/test_engine_parity.py).
5. Describe the behaviour in [docs/spec.md](docs/spec.md) and add an Unreleased entry in [CHANGELOG.md](CHANGELOG.md).

## Add a herd

A herd is a standard-library file under [phyx/lib/](phyx/lib/). It is ordinary φyrx: `ťe` abilities, cast with `bukð`. `min`, `sort`, and `map` are herds because the dictionary has no such verbs. See [docs/stdlib.md](docs/stdlib.md) and [docs/rationale.md](docs/rationale.md).

1. Add `phyx/lib/<name>.phyx`. The package data glob `lib/*.phyx` in [pyproject.toml](pyproject.toml) ships it. `python -m phyx lib` lists the herds.
2. Add a row to the herd table in [docs/reference.md](docs/reference.md#standard-herds) and a section in [docs/stdlib.md](docs/stdlib.md).
3. Add `tests/phyx/test_<name>.phyx`. Cast the herd with `bukð` and assert with `ǩaπa`. [tests/phyx/test_asərθ.phyx](tests/phyx/test_asərθ.phyx) is the pattern, next to [phyx/lib/asərθ.phyx](phyx/lib/asərθ.phyx).

## Add a test

Python tests live in `tests/test_*.py`. `python -m unittest discover -s tests -v` finds them. A semantic change adds a case to [tests/test_engine_parity.py](tests/test_engine_parity.py) that calls `assertParity` or `run_both`.

φyrx tests are `test_*.phyx` and `test_*.vphyx` under [tests/](tests/). `python -m phyx test` walks that tree. A file passes when it finishes without a fault. `ǩaπa` (must) is the assertion. A sibling file with the same stem and the suffix `.expected` must match stdout exactly, with newlines normalised to `\n`. See [docs/toolchain.md](docs/toolchain.md) and [phyx/testing.py](phyx/testing.py).

## Conduct and security

[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) is the community standard. [SECURITY.md](SECURITY.md) is the trust model and the way to report a vulnerability.
