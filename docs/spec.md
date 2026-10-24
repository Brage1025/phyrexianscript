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
- `ťe` — define an ability. `'iţpənn` returns. Missing return yields void. `'iţpənn` outside an ability is a grammar fault on that line.
- `lups` leaves the innermost `baxuφ` or `aχəw'` written in the same ability. `ɢnagɮ` skips to its next turn. Either word outside such a loop is a grammar fault on that line. A loop that only calls the ability does not make the word legal.
- `ǩaπa` — assert; a false condition is a runtime fault.
- `baqilx` / `qit` — try / catch. `dekp` is the blame in the handler.
- `!` — speak each value, separated by a space, then a newline. Numbers are hexadecimal.
- `?` — ask; store the line in the last name.

`'u` constants cannot be rebound. Assignment is an expression and yields the value. Order is **value then place**.

### Scope

An assignment looks for a binding of that name that already exists, starting in the scope that is running and walking outward through each enclosing ability to the file. A parameter is a binding of its ability from the moment the body runs.

If a binding is found, the assignment rebinds it. Rebinding a name that was fixed with `'u` is a fault. If none is found, the assignment creates a local of the scope that is running. This choice is made when the assignment runs, not when the ability is defined.

A name is a binding of a scope once an assignment in that scope has run, including an assignment inside `ba`, `baxuφ`, `aχəw'`, or `baqilx`. The tried body and the `qit` handler share the scope that contains the sentence. An ability rebinds that name only after the assignment has run. Before then the ability's assignment is a local, and a read of the outer name is an unknown word.

`'u` fixes a name in the scope that is running. It does not walk outward, so it may shadow an outer name. A read of that name before the `'u` runs still sees the outer binding, or is an unknown word when there is none; the `'u` then fixes a local. A later assignment of that local constant is a fault: the name was fixed in the past (`'u`) and cannot change. Fixing a name that already has a value in the running scope is also a fault.

The item of `aχəw'` and the target of `?` are bindings of the scope that contains the sentence, once the loop or the question has run. An empty loop does not bind the item. The `qit` handler runs in that same scope: `dekp` is assigned there and stays bound after the handler, and so does any other name or ability bound in the handler.

In a persistent session the file's bindings survive from one sentence to the next, so a later ability rebinds a name an earlier sentence already bound.

An ability applied to fewer objects than its arity is the ability value, not a call. A zero-parameter ability is always a call; quote it with `naķm`.

Lists and books take a **plain numeral count** immediately before the verb: `1-2-3-3-ťewn`. Empty: `0-ťewn`.

`tøwp` repeats text or a list. The result is at most `100000` items (1,048,576). A longer repetition is a runtime fault. An empty text or an empty list repeated by any count, including a negative count, is empty. `ronɣ` is the list `[0, n)` and is at most `100000` numbers; a larger `n` is a runtime fault. A negative `n` is empty. Multiplying two numbers is not subject to this bound.

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

A run of the same ability on that stack is written once, with a count (`cnt x1000`). The first and last abilities stay visible, so `go` then a thousand `cnt` then `boom` is `go → cnt x1000 → boom`.

A program the host cannot keep in memory is a runtime fault (`the program ran out of memory`). `baqilx` / `qit` can catch it. Showing or comparing a list or book that is nested too deeply for the host is a runtime fault (`this value is nested too deeply`). Source that is itself nested too deeply for the reader — the parser, the compiler, the formatter, or the linter — is a grammar fault (`this program is nested too deeply`) on the line where that nesting starts.

English mood words (`if`, `while`, `def`, …) in marker position are a grammar fault naming the Phyrexian marker.

Unknown names at runtime suggest a nearby lexicon word, or the English → Phyrexian mapping.

## 8. Host

A conforming toolchain may compile a program to CPython. Observable behaviour must match this specification, including fault messages' meaning (wording may grow hints). `PHYX_TREEWALK=1` selects a tree-walker with the same semantics.

Integer overflow does not occur: host integers are unbounded.

Calling abilities deeper than the host recursion ceiling is a runtime fault (`the abilities called each other too deeply`). It has no line: the fault is raised inside the recursion, and a line would not say which call failed. The ability stack is still reported. The ceiling is `PHYX_RECURSION`; see [toolchain.md](toolchain.md).

## 9. Versioning

The language version is the first two numbers of the toolchain version (`1.6.1` → language 1.6). Additions that stay inside the dictionary are minor. Inventing non-dictionary syntax is not an allowed change.
