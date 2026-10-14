# What remains to be done

Snapshot of **φyrx 1.6.1** (PhyrxScript / PhyrexianScript). The language is finished under the dictionary constraint. Remaining work is shipping it.

Do not invent non-dictionary syntax to “finish” this list. See [rationale.md](rationale.md) for what will not be added.

---

## Do these if other people should use it

None of this changes Phyrexian grammar. Highest leverage.

- [x] **Git.** https://github.com/Brage1025/phyrexianscript — history, `v1.6.1` tag, public remote.
- [x] **First commit** of the 1.6.1 tree.
- [x] **CI** (`.github/workflows/ci.yml`) runs `python -m unittest discover -s tests -v` and `python -m phyx test`.
- [x] **PyPI packaging.** Name `phyx` is free; `python -m build` / `twine check` run in CI. `pip install phyx` from the index after the first trusted-publish Release (configure a pending publisher on pypi.org).
- [x] **Cursor / VS Code extension.** `editors/package.json`. Install from that folder; not on a marketplace yet. See [../editors/README.md](../editors/README.md).

---

## Do these if you want more Phyrexian, not more Python

- [x] **Verb conjugation** from dictionary [tutorial chapter 3](https://fxbuson.github.io/PhyrexianDictionary/tutorial?chapter=3). Lemma is 3→3; other persons are the same verb. Tense stays on the mood marker.
- [x] **Basilica digits in the lexer.** Mathematical Monospace `0–9A–F` tokenise as the same hex as Arabic digits.

---

## Small consistency gaps

Closed in 1.6.1.

- [x] Cover **core sentences** in `tests/phyx/` (abilities, loops, list counts, `ǩaπa`). Herds stay in the same folder; a false `ǩaπa` fails the file.
- [x] **`brøtjt` / `mɴyrx`:** research searches file dir, cwd, `PHYX_PATH` (not `phyx/lib/`). Spread writes next to the program and never searches.
- [x] **`phyx test` expected-output:** sibling `test_*.expected` is exact UTF-8 stdout. Without one, `ǩaπa` / no-fault is still the protocol.
- [x] **`phyx lookup`** searches `phyx/vocabulary.py` (and conjugations) with no fetch. The downloaded dictionary is extra when present.

---

## Optional DX — skip until someone asks

- [ ] Language server (complete markers/verbs, jump to `ťe`).
- [ ] `phyx new` scaffold (shebang + a `test_*.phyx`).
- [ ] Closer-to-1× `bench` by using raw Python `<` on proven ints — rejected in 1.4.1 because `1 == True` is not Phyrexian.
- [ ] Extra herds for books/text. `tekt` and `rukx` already have verbs; `min` / `sort` were herds only because the dictionary has no such words.

---

## Already shipped

Do not treat these as leftovers.

- [x] Grammar: SOV postfix, hex numerals, mood markers, dictionary punctuation
- [x] Chapter-3 verb person inflection; Basilica Mathematical Monospace numerals
- [x] Turing-complete (`baxuφ`, unbounded lists, recursive `ťe`) — `examples/11_machine.phyx`
- [x] Compile to CPython (`PHYX_TREEWALK=1` is the fallback)
- [x] Standard library `phyx/lib/` (`asərθ`, `ťewn`, `compleat`) and `bukð` search path
- [x] `python -m phyx test` / `python -m phyx lib` / lexicon `lookup`
- [x] Docs: [tour](tour.md), [index](index.md), [stdlib](stdlib.md), [spec](spec.md), [guide](guide.md), [reference](reference.md)
- [x] `fmt`, `lint`, `explain`, `dis`, `bench`, REPL, render, fetch
- [x] TextMate and Vim grammars generated from the lexicon

Python and φyrx tests were passing at the 1.6.1 snapshot. CI, the extension manifest, and PyPI packaging landed with the first commit.

---

## Will not be added

Floats, classes, infix `+`, decimal literals, `async`, comprehensions, `json` / `re` as host builtins.

If a change needs a word the dictionary does not have, the change is wrong, or the dictionary grew and the mapping can be revisited in the open.

---

## Next useful move

1. On pypi.org, add a pending trusted publisher for project `phyx`, owner `Brage1025`, repo `phyrexianscript`, workflow `publish.yml`. Then a GitHub Release of `v1.6.1` makes `pip install phyx` work.

Do not start another “make it more like Python” pass.
