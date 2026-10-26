# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## Unreleased

### Added

- The specification now defines every standard verb (arity, result, and faults) in section 5. `tests/test_spec_verbs.py` checks that each lexicon verb has a row and runs an example of each row on both engines.
- `docs/releasing.md` is the release checklist: which files hold a version, how to rename Unreleased, and what the two publish workflows run.
- `tests/test_versions.py` checks the version rule. `phyx.__version__` must match `pyproject.toml`, the spec heading must be the language major.minor, `## Unreleased` must be first, the next version heading must be the package version, and `editors/package.json` must be an `X.Y.Z` of its own.
- CI runs the suite on Ubuntu, Windows, and macOS, and adds the tree-walker, `ruff check .`, a 3000-program fuzz, coverage on Ubuntu 3.13 with no threshold, and a wheel and sdist install outside the checkout.
- A program runs on a thread with a 64 MiB stack. `PHYX_RECURSION` (decimal, default `16384`) is the host recursion ceiling, enough for a compiled ability about 8000 calls deep and capped at what that stack can hold. Deeper recursion is still `the abilities called each other too deeply`.

### Changed

- `phyx.__version__` is the installed distribution's version (`importlib.metadata`). When the package is not installed, it is the `version` in `pyproject.toml` (`tomllib`). When neither can be read, it is `0+unknown`. An editable install keeps the previous metadata until `python -m pip install -e ".[dev]"` is run again.
- The specification heading names the language version (1.6), the first two numbers of the toolchain version.
- The Development Status classifier is Beta. The license field is the SPDX expression `MIT` and `license-files` lists `LICENSE`. The build requires setuptools >= 77.0.0. The OSI license classifier is removed. `include-package-data` is off, so the `phyx.lib` directory stays package data (`lib/*.phyx`) and setuptools no longer warns that `phyx.lib` is absent from `packages`.
- Behaviour change: `'iţpənn` outside an ability, and `lups` or `ɢnagɮ` outside a loop, are grammar faults with a line and a hint. The parser raises them, so neither engine can reach them at run time. A loop that only calls an ability does not make `lups` or `ɢnagɮ` in that ability legal. A legal use still passes through `baqilx`.
- Behaviour change: the tree-walker reports `the abilities called each other too deeply` with no line, the same as the compiled engine. The `in abilities:` stack stays.
- The compiled engine no longer treats a `'u` name as a local for the whole ability. A read before that `'u` sees the outer binding, or is an unknown word when there is none; the `'u` then fixes a local.
- The ability-stack line of a fault collapses consecutive repeats (`cnt x1000`). The first and last abilities stay visible.
- `tøwp` on text or a list, and `ronɣ`, stop at `100000` items (1,048,576). A longer result is a runtime fault, including `!"x"-100000000000-tøwp-samk`. An empty value repeated any number of times, and a negative count, stay empty.
- Behaviour change: a `qit` handler runs in the enclosing scope, the same scope as the tried body. `dekp` is assigned there and stays bound after the handler, and a name or ability bound in the handler stays bound.
- `'u` in an ability fixes a name of that ability and may shadow an outer name. A later plain assignment of that local constant is a fault (`was fixed in the past ('u) and cannot change`).
- A read of a name that is not bound yet is an unknown word, with the usual hint and line. That includes a read before a later assignment, a read after an untaken `ba`, a read after an empty `aχəw'`, and a sentence that is only a name or a literal. A compiled block that would otherwise be empty is `pass`.
- An ability rebinds a module name, a name of an enclosing ability, a loop item, or a question target when that binding already exists, and otherwise creates a local. An ability defined in the handler rebinds `dekp`. The compiled engine decides this when the assignment runs, so a name assigned later in the file, inside `ba` / `baxuφ` / `aχəw'`, or by an earlier persistent sentence, matches the tree-walker.
- Operands are evaluated left to right. When a later operand needs statements, each earlier operand that is not a literal is copied into a temporary first. `y-bump-babg` reads `y` before `bump` runs, in an ability and at module level.

### Fixed

- Ctrl-C stops a running program again. The process prints `ɬšeɴazv: stopped` and exits `130`. In the REPL the same interrupt ends the sentence and returns to the prompt.
- A host `MemoryError` is the runtime fault `the program ran out of memory`. `baqilx` / `qit` can catch it.
- Source nested too deeply to lex, parse, compile, format, or lint is the grammar fault `this program is nested too deeply`, on the line where the nesting starts. Showing or comparing a value nested too deeply is the runtime fault `this value is nested too deeply`.
- `python -m phyx bench` always measures the compiled engine, including when `PHYX_TREEWALK=1`.
- Pure abilities no longer compile arithmetic to raw Python operators. Divide by zero, a bad kind, a negative `lu'f`, and adding a truth are `RuntimeFault`s with the tree-walker's message and hint, so `baqilx` can catch them. `əx` uses `truthy()`. The type test is skipped only when both objects are provably numbers.
- A negative number literal is parenthesised in the generated Python, so `əx2-2-lu'f` is 4 (`(-2) ** 2`), not `-(2 ** 2)`.

## 1.6.4

Extension icon. The language is still **1.6**.

- `brage1025.phyx` has a hex badge: `phyx-original` (white / gray-white split), `phyx-plain` (solid white hex, oil ϕ), `phyx-line` (white hex ring + ϕ). Closed **ϕ**, not the Wizards mana SVG.

## 1.6.3

Toolchain DX. The language is still **1.6**. `pip install phyx` and `brage1025.phyx` are 1.6.3.

- `phyx new NAME` writes a shebang program and a sibling `test_NAME.phyx`.
- `phyx lsp` is a stdlib JSON-RPC language server: complete markers/verbs/constants/`ťe` names, jump to `ťe`, hover. The editor extension starts it when `phyx` is on PATH.
- No extra book/text herds: the dictionary already names those operations as verbs.
- The same 1.6.3 VSIX is on [Open VSX](https://open-vsx.org/extension/brage1025/phyx) so Cursor’s in-editor marketplace can find it.

## 1.6.2

Marketplace listing text. The language and `pip install phyx` stay **1.6.1**.

- `brage1025.phyx` 1.6.2: the VSIX README names the live Marketplace listing instead of saying it is not on a marketplace.

## 1.6.1

The four consistency gaps, plus the shipping surface: git, CI, PyPI layout, and a Cursor / VS Code extension.

- `tests/phyx/` covers abilities, loops, list counts, and `ǩaπa`. A sibling `test_*.expected` file is exact UTF-8 stdout; without one, a file still passes when it finishes without a fault.
- `brøtjt` searches like a read: file directory, working directory, `PHYX_PATH`. It does not search `phyx/lib/` (herds are programs). `mɴyrx` writes next to the program and never searches, so a short name cannot clobber the library.
- `python -m phyx lookup` searches `phyx/vocabulary.py` (and conjugations). The fetched dictionary is extra when present.
- `editors/package.json` is a Cursor / VS Code extension (`brage1025.phyx`) on the Visual Studio Marketplace.
- GitHub Actions run `python -m unittest discover -s tests -v` and `python -m phyx test`. `pip install phyx` is on PyPI (1.6.1).

## 1.6.0

Phyrexian person inflection and Basilica numerals — still the dictionary, not English tense.

- Verbs accept tutorial chapter 3 conjugation (vowel before the last consonant; 1 me / 2 you / 3 they / 4 one). The lemma is 3→3. `babeg` is `babg`. Tense stays on `xe` / `'u` / `ba`. `python -m phyx explain babeg` names the persons.
- The lexer reads Basilica Mathematical Monospace hex digits as the same numerals as `0–9a–f`. ASCII `a` is still a name.

## 1.5.0

A complete language: shipped standard library, tests written in φyrx, editor grammars, and docs that start from zero.

- `bukð` searches the file's directory, the working directory, `PHYX_PATH`, then `phyx/lib/`. A name without a suffix is tried as `.phyx` then `.vphyx`.
- Shipped herds: `asərθ.phyx` (abs, gcd, min, max, sum), `ťewn.phyx` (map, filter, reverse, sort), `compleat.phyx` (both). `examples/lib_*` remain aliases.
- `python -m phyx test` runs `test_*.phyx`; `ǩaπa` is the assertion. `python -m phyx lib` lists the herds.
- TextMate and Vim grammars in `editors/`, generated from the lexicon.
- Docs: [docs/index.md](docs/index.md), [docs/tour.md](docs/tour.md), [docs/stdlib.md](docs/stdlib.md). Language tests live in `tests/phyx/`.

## 1.4.1

Bugs and documentation that had drifted from the language.

- Pure abilities no longer use Python `==` / `<` / `>`: `1-əxbytp-ǆ'ynpp` is false, and a number cannot be ordered against a truth. `bench` is a small factor over CPython, not 1.000×, because those checks remain.
- `lint` no longer flags `fn` (a stored ability) as English. Only statement keywords (`if`, `return`, …) are notes.
- A `xe` / `lo` sentence that opens a body (`:`) names `ťe` and `--ascii` (`Te` for `ťe`).
- Windows consoles: stdout/stderr prefer UTF-8 and will not crash on Phyrexian letters.
- Docs: `əx` as marker vs verb; `xə` / `ʁšθakɴ` evaluate every object; kinds of `ǆ'ynpp`; `--ascii` on lint/check; troubleshooting in the guide. Tests fail if a verb or CLI command disappears from the docs.

## 1.4.0

The language is the same Phyrexian. The toolchain now treats faults, explanation, and compiled shape as part of being a language.

- Faults carry a **hint** (what to do next) and an **ability stack** when they arise inside `ťe`.
- English mood words (`if`, `while`, `def`, …) in marker position are a grammar fault that names the Phyrexian marker.
- Unknown names suggest a nearby lexicon word or the English → Phyrexian mapping.
- `python -m phyx explain WORD` — markers, verbs, constants, punctuation, English aliases (`explain if` → `ba`).
- `python -m phyx fmt FILE` — canonical `-` separators and 4-space indent; notes and shebang kept. `--in-place` / `-o`.
- `python -m phyx lint FILE` — dropped `'iţpənn`, unused objects, English names used as names.
- Compiler emits nested Python expressions: `return fib(n-1)+fib(n-2)`, `while i < n:` (no ANF temps, no `while True`/`break` on a pure condition). After compile, `phyx bench` is ~1× CPython on recursive `fib`.
- REPL `.explain`.
- Spec: [docs/spec.md](docs/spec.md). Decisions: [docs/rationale.md](docs/rationale.md).

## 1.3.0

Turing-complete on CPython. Pure abilities compile to raw integer operators. `brøtjt` / `mɴyrx` for UTF-8 notes. Herds `min` / `max` / `sum` / `sort` / `reverse`. `phyx bench`, `phyx dis`. Docs for someone arriving from Python.

## 1.2.0

Named φyrx / PhyrxScript / PhyrexianScript. Modules (`bukð`), `'uxq`, `naķm`, shebang, official Phyrexian font family name.

## 1.1.0

Vertical script, ASCII transliteration, REPL, first-class abilities, lists and books.
