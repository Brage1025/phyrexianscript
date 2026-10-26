# Roadmap

The language and toolchain versions are in the [README](../README.md#status) and [pyproject.toml](../pyproject.toml); the same file's classifiers name the supported Python versions. CI runs on Linux, macOS, and Windows ([.github/workflows/ci.yml](../.github/workflows/ci.yml)).

Nothing below is a promise, and nothing below adds a word or a form the Phyrexian dictionary does not have. Design constraints: [rationale.md](rationale.md).

## Already shipped

- Grammar: SOV postfix, hex numerals, mood markers, dictionary punctuation
- Chapter-3 verb person inflection; Basilica Mathematical Monospace numerals
- Turing-complete (`baxuφ`, unbounded lists, recursive `ťe`) — [examples/11_machine.phyx](../examples/11_machine.phyx)
- Compile to CPython (`PHYX_TREEWALK=1` is the tree-walker)
- Standard library `phyx/lib/` (`asərθ`, `ťewn`, `compleat`) and `bukð` search path
- `python -m phyx test` / `python -m phyx lib` / lexicon `lookup`
- `phyx new` and `phyx lsp`
- Docs: [tour](tour.md), [index](index.md), [stdlib](stdlib.md), [spec](spec.md), [guide](guide.md), [reference](reference.md)
- `fmt`, `lint`, `explain`, `dis`, `bench`, REPL, render, fetch
- TextMate and Vim grammars generated from the lexicon
- Git history on the public repository, CI, `pip install phyx`, the Visual Studio Marketplace listing, and Open VSX (`brage1025.phyx`)

## Known issues

- **`'u` on a name already bound in the same ability.** The compiled engine and the tree-walker still disagree in a few cases. Pinned as expected failures `test_BUG_R_enclosing_loop_name_persistent`, `test_BUG_S_fix_in_handler_of_try_name`, and `test_BUG_T_second_fix_message` in [tests/test_parity_fuzz.py](../tests/test_parity_fuzz.py) (`BUG_R`, `BUG_S`, `BUG_T`). GitHub: [#24](https://github.com/Brage1025/phyrexianscript/issues/24)
- **`phyx lint` and abilities brought in with `bukð`.** A short call of an ability defined in the same file is a note. A short call of an ability brought in with `bukð` is not: `lint` collects arities from this file's `ťe` sentences only ([phyx/lint.py](../phyx/lint.py)). GitHub: [#25](https://github.com/Brage1025/phyrexianscript/issues/25)
- **Guarded arithmetic.** Compiled programs keep a kind guard on operators, so arithmetic-heavy code is slower than the same code in CPython. `python -m phyx bench` prints the ratio. On the defaults (`--size 16`, `--loops 20000`) the ratio is typically two to four times and varies by machine. A specialised fast path is a possible optimisation. It is unscheduled. Compiling ordering to raw Python `<` stays rejected: `1 == True` is not Phyrexian (1.4.1). GitHub: [#26](https://github.com/Brage1025/phyrexianscript/issues/26)
- **Ctrl-C and out-of-memory on CI.** Both are tested only where the platform supports the check. Ctrl-C tests skip on Windows (`SIGINT` delivery differs). The out-of-memory fault is tested on Linux only: macOS does not enforce `RLIMIT_AS`, and Windows has no `resource` module ([docs/toolchain.md](toolchain.md), [tests/test_host_faults.py](../tests/test_host_faults.py)). Windows CI therefore does not run either check. GitHub: [#27](https://github.com/Brage1025/phyrexianscript/issues/27)
- **Publish workflows.** Whether the Marketplace accepts the OIDC publish is unverified ([docs/releasing.md](releasing.md)). GitHub: [#28](https://github.com/Brage1025/phyrexianscript/issues/28)

## Planned work

Unscheduled. Taking an item up is a later decision.

- An optional `--safe` flag for running other people's programs. Today a program can read and write files, cast other files, and exit the process ([SECURITY.md](../SECURITY.md)).
- Fixes for the known issues above, if one of them is taken up. The arithmetic fast path, if it is ever written, still has to keep Phyrexian kinds.

## Will not be added

Floats, classes, infix `+`, decimal literals, `async`, comprehensions, `json` / `re` as host builtins.

Extra book and text herds were not added. The dictionary already has `tekt` (book), `rukx` (note), `rukxtekt` (notebook), `tluxt` (copy), `ťewn` (list), and verbs for split, join, length, and slice. `min` / `sort` are herds because the dictionary has no such words.

If a change needs a word the dictionary does not have, the change is wrong, or the dictionary grew and the mapping can be revisited in the open. The record of that rule is [rationale.md](rationale.md).

## How language decisions are made

The language is the Phyrexian dictionary's grammar and lexicon. A proposal is judged against [rationale.md](rationale.md). Anything that needs a word or a form the dictionary lacks is out of scope. A behaviour change goes through [spec.md](spec.md), [reference.md](reference.md), and [CHANGELOG.md](../CHANGELOG.md) in one branch, with a parity test that runs both engines. The maintainer decides.
