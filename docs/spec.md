# φyrx language specification (1.6.1)

Normative description of **φyrx** (PhyrxScript / PhyrexianScript). The guide ([guide.md](guide.md)) teaches; this page defines. Where they disagree, this page wins. Provenance of every word: [reference.md](reference.md#provenance).

A conforming implementation parses the grammar below, evaluates with the semantics below, and reports faults with a kind, a location, and a next step ([rationale.md](rationale.md)).

---

## 1. Source

- Encoding: UTF-8. A leading BOM is ignored.
- Line endings: LF, CR, or CRLF. Line numbers count newline-terminated rows, 1-based.
- A first line starting with `#!` is a shebang and is dropped. Remaining line numbers are unchanged.
- Extensions: `.phyx` (one Phyrexian line per text row), `.vphyx` (vertical columns; see [toolchain.md](toolchain.md)).

## 2. Lexical structure

**Letters.** Vowels `i y e a ɒ o ø u ə`. Consonants `m n ŋ ɴ s š z ž ɬ ɮ l r č ǆ w j ẅ ' h p f π φ b v t θ ť ţ d ð k x ǩ ķ g ɣ q χ ǧ ǥ ɢ ʁ`. Other Unicode letters are accepted in names.

**Punctuation.**

| Symbol | Token | Role |
| --- | --- | --- |
| `^` `!` `?` | START | begin a sentence |
| `.` | END | end a sentence |
| `:` | COLON | end a header; a body follows |
| `-` | SEP | word separator |
| `,` | COMMA | phrase barrier |
| `"` … `"` | STRING | text; escapes `\\` `\"` `\n` `\t`; one line |

A newline is a SEP. Spaces and tabs separate tokens but are not themselves words. A tab in leading indent counts as four spaces.

**Comments.** `^rukx` through end of line is dropped.

**Numerals.** A token that starts with a digit is hexadecimal. `10` is sixteen, `0a` is ten. The negative prefix `əx` glued onto digits is a negative numeral (`əx1a` = −26). A numeral must not run into a letter without `-`.

Basilica Mathematical Monospace digits (`U+1D7F6…U+1D7FF`, `U+1D670…U+1D675`, `U+1D68A…U+1D68F`) are the same sixteen hex values. They may mix with Arabic digits in one numeral. ASCII `a–f` still do not *start* a numeral (they are letters). `asərθ` on text accepts both spellings.

**ASCII mode.** When enabled, an uppercase letter (or listed digraph) is the special letter it resembles. See [toolchain.md](toolchain.md).

## 3. Grammar

```
program   := sentence*
sentence  := START marker? phrase (END | COLON body)
body      := inline-sentence | INDENT sentence+ DEDENT
phrase    := clause (COMMA clause)*
clause    := atom (SEP atom)*
atom      := WORD | NUMBER | STRING
```

`marker` is one of the mood words in [reference.md](reference.md). If omitted after `^`, it is `xe`. `!` is an exclamation (speak). `?` is a question (ask). `əx` as a marker is unless; `əx` later in a phrase is the verb *not*.

ASCII mode (`--ascii`) is part of the toolchain, not of the grammar: it rewrites source to Phyrexian letters before tokenising. A file written in ASCII capitals (`Te` for `ťe`) is not a valid program without that flag.

A phrase is a stack. Each verb pops its objects (left to right as written) and pushes one result. User-defined abilities behave as verbs of their arity. A comma sets a barrier: values to its left cannot be objects of verbs to its right.

A dictionary verb may be written in any cell of the chapter-3 person table (vowel before the last consonant, with rounding `i→y` / `e→ø` and metallicising `p→π→φ` as in the tutorial). The lemma is 3→3. Inflection does not change the operation and is not tense; tense is the mood marker. A conjugated form of a lexicon verb cannot name a `ťe`.

The last word of a `ťe` phrase is the ability name; the words before it are parameter names.

## 4. Types

| Kind | Type word (`πøkk`) | Host value | Truth |
| --- | --- | --- | --- |
| number | `asərθ` | Python `int` (unbounded) | non-zero |
| text | `rukx` | `str` | non-empty |
| truth | `wija'x` | `bool` | itself |
| void | `əixiww` | `None` | no |
| list | `ťewn` | `list` | non-empty |
| book | `tekt` | `dict` | non-empty |
| ability | `ɣwi't` | `Ability` | yes |

There are no floats, no classes, no decimal literals. `χɬkevk` is floor division.

Constants: `bytp` (false), `əxbytp` (true, “not-false”), `əixiww` (void), `'ii` (1), `ķu` (2), `ķi` (3).

## 5. Evaluation

Sentences run in order. `ťe` names are visible throughout the file (and in files this file `bukð`s, after the include is parsed).

- `xe` / `lo` — evaluate the phrase.
- `'u` — evaluate; each assignment is constant.
- `ba` / `bu` / `əx` (as marker) — if / unless; `qit` attaches as else; `qit-ba` is else-if.
- `baxuφ` — while the condition is truthy.
- `aχəw'-ITEM-dl-COLLECTION` — for each.
- `ťe` — define an ability. `'iţpənn` returns. Missing return yields void.
- `ǩaπa` — assert; a false condition is a runtime fault.
- `baqilx` / `qit` — try / catch. `dekp` is the blame in the handler.
- `!` — speak each value, separated by a space, then a newline. Numbers are hexadecimal.
- `?` — ask; store the line in the last name.

`'u` constants cannot be rebound. Assignment is an expression and yields the value. Order is **value then place**.

An ability applied to fewer objects than its arity is the ability value, not a call. A zero-parameter ability is always a call; quote it with `naķm`.

Lists and books take a **plain numeral count** immediately before the verb: `1-2-3-3-ťewn`. Empty: `0-ťewn`.

`ǆ'ynpp` is equal only when both values have the same kind: a number is never equal to a truth. `xə` / `ðə` yield truth and evaluate both objects. `ʁšθakɴ` evaluates the condition and both arms (objects sit before the verb).

## 6. Modules, command, notes on disk

- `bukð` path — run that `.phyx` / `.vphyx` in the current session. Cycles are a grammar fault. Cast before call.
- Resolution order: directory of the file that contains the `bukð`, working directory, each entry of `PHYX_PATH`, then the shipped library (`phyx/lib`). A name without a suffix is tried as `.phyx` then `.vphyx`. Absolute paths are used as written.
- A conforming implementation ships number and list herds (`asərθ`, `ťewn`, `compleat`) in that library. They are φyrx programs, not host primitives.
- `'uxq` — list of program arguments (text). Empty in the REPL.
- `brøtjt` path — read UTF-8 text. Relative names search: directory of the file that contains the verb, working directory, each entry of `PHYX_PATH`. The path is used as written (no suffix guessing). The shipped library is not searched. Absolute paths are used as written.
- `mɴyrx` text path — write UTF-8 text, yield the text. Relative names are resolved against the directory of the file that contains the verb (working directory in the REPL). This verb does not search. Absolute paths are used as written.

## 7. Faults

Every fault is a `ɬšeɴazv` with a kind (`[symbols]`, `[grammar]`, `[runtime]`, `[program]`), a location, the source line and a caret when known, a **hint** (what to do next), and an **ability stack** when the fault arose inside `ťe`.

English mood words (`if`, `while`, `def`, …) in marker position are a grammar fault naming the Phyrexian marker.

Unknown names at runtime suggest a nearby lexicon word, or the English → Phyrexian mapping.

## 8. Host

A conforming toolchain may compile a program to CPython. Observable behaviour must match this specification, including fault messages' meaning (wording may grow hints). `PHYX_TREEWALK=1` selects a tree-walker with the same semantics.

Integer overflow does not occur: host integers are unbounded.

## 9. Versioning

The language version is the first two numbers of the toolchain version (`1.6.1` → language 1.6). Additions that stay inside the dictionary are minor. Inventing non-dictionary syntax is not an allowed change.
