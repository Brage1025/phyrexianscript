# φyrx language reference

PhyrxScript / PhyrexianScript. Companion to [guide.md](guide.md). First program: [tour.md](tour.md). Herds: [stdlib.md](stdlib.md). Source files are UTF-8. A leading BOM is ignored. Letters are the dictionary’s romanisation.

---

## Lexical structure

**Letters.** Vowels `i y e a ɒ o ø u ə`. Consonants `m n ŋ ɴ s š z ž ɬ ɮ l r č ǆ w j ẅ ' h p f π φ b v t θ ť ţ d ð k x ǩ ķ g ɣ q χ ǧ ǥ ɢ ʁ`. Names you bind may use these letters freely; they must not be a reserved marker, verb, or constant.

**Strings.** `"…"` on one line. Escapes: `\\` `\"` `\n` `\t`.

**Comments.** `^rukx` through end of line. Dropped before parsing.

**Shebang.** A first line starting with `#!` is dropped. Line numbers of the remaining text are unchanged.

**Whitespace.** Spaces inside a word are not allowed. Use `-` or a newline between words.

---

## Types and values

| Kind | Type word (`πøkk`) | Written | Truth |
| --- | --- | --- | --- |
| number | `asərθ` | hexadecimal (`0a`, `əx10`) | non-zero |
| text | `rukx` | `"…"` | non-empty |
| truth | `wija'x` | `əxbytp` / `bytp` | itself |
| void | `əixiww` | `əixiww` | no |
| list | `ťewn` | `1-2-3-3-ťewn` | non-empty |
| book (map) | `tekt` | `"a"-1-"b"-2-2-tekt` | non-empty |
| ability | `ɣwi't` | `naķmname` when spoken | yes |

There are no floats. Division (`χɬkevk`) is integer (floored). `asərθ` parses hexadecimal text; `xušv` is the inverse for any value.

`bytp` is false. True is **not-false**: `əxbytp`. Void is `əixiww`. Number-words: `'ii` (1), `ķu` (2), `ķi` (3).

---

## Expressions

Evaluation is a stack. Each verb pops its objects (left-to-right as written) and pushes the result.

**Comparisons you compose**, as Phyrexian composes words:

| Want | Write |
| --- | --- |
| `a = b` | `a-b-ǆ'ynpp` |
| `a ≠ b` | `a-b-ǆ'ynpp-əx` |
| `a < b` | `a-b-grmɒɣg` |
| `a > b` | `a-b-korxgr` |
| `a ≤ b` | `a-b-korxgr-əx` |
| `a ≥ b` | `a-b-grmɒɣg-əx` |
| `a and b` | `a-b-xə` |
| `a or b` | `a-b-ðə` |
| `not a` | `a-əx` |
| `b if a else c` | `a-b-c-ʁšθakɴ` |

---

## Mood markers

The first word after `^` selects the sentence. If it is omitted, it is `xe`. `!` and `?` do not take a marker.

| Word | Role |
| --- | --- |
| `xe` | indicative — evaluate |
| `'u` | past indicative — assignment is constant |
| `lo` | imperative — evaluate (conventionally “do”) |
| `ba` | conditional — if |
| `bu` | negative conditional — unless |
| `əx` | as a **marker** (first word): unless. Later in a phrase: the verb *not* |
| `qit` | instead — else / catch |
| `baxuφ` | whenever — while |
| `aχəw'` | each — for (`ITEM` `dl` collection) |
| `ťe` | potential — define an ability |
| `ǩaπa` | jussive — must (assert) |
| `baqilx` | if would — try |

`əx` is the only word that is both a marker and a verb. `^əx-n:` is unless `n`; `^xe-n-əx.` is not `n`.

---

## Sentences

```
^xe-… .                    evaluate
^'u-… ţə''.                constant binding
^lo-… .                    imperative evaluate
! … .                      speak (print), space-separated, then newline
? prompt… name.            ask; bind the line of input (or void at EOF)
^ba-cond: body             if
^bu-cond: body             unless
^qit: body                 else (must follow ba / baqilx)
^qit-ba-cond: body         else-if
^baxuφ-cond: body          while
^aχəw'-x-dl-xs: body       for each x in xs
^ťe-a-b-name: body         define
^ǩaπa-cond.                assert
^ǩaπa-cond,"message".
^baqilx: body              try
^qit: body                 catch; the blame is bound to dekp
```

**Loops.** `lups` (stop) leaves the loop. `ɢnagɮ` (next) skips to the next turn. The loop has to be a `baxuφ` or `aχəw'` in the same ability; a caller that is in a loop does not count. Outside one, either word is a grammar fault on that line, with a hint. `aχəw'` walks a list, the keys of a book, or the characters of text. The item name remains bound after the loop (to the last item). `'u` constants cannot be overwritten by the loop variable.

**Try.** `baqilx` without a following `qit` *ignores* the mistake and continues. With `qit`, `dekp` holds the raised value (for `ɬšeɴazv`) or the fault message (for runtime faults). A legal `lups` / `'iţpənn` / `ɢnagɮ` is not a mistake; it passes through `baqilx`. `'iţpənn` outside an ability is a grammar fault, so `baqilx` never sees it.

**Scope.** An assignment rebinds a name that is already bound in the running scope or an enclosing one, and otherwise creates a local. It decides when it runs. A name assigned in the file or in an ability — including inside `ba`, `baxuφ`, `aχəw'`, or `baqilx` — is a binding of that scope once the assignment has run. The tried body and the `qit` handler share that scope, so `dekp` and any other name or ability bound in the handler stay bound afterwards. The item of `aχəw'` and the target of `?` are the same kind of binding; an empty loop does not bind the item. `'u` fixes a name in the running scope and may shadow an outer name. A read before that `'u` sees the outer binding, or is an unknown word when there is none. A later assignment of that local constant is a fault, and so is fixing a name that already has a value there. In a persistent session, a later sentence sees the bindings of earlier ones.

---

## Standard verbs

Objects are listed in writing order. `N` is a literal count sitting immediately before the verb. `python -m phyx words` prints this table from the running interpreter.

### Arithmetic

| Word | Objects | Meaning |
| --- | --- | --- |
| `babg` | a b | add (numbers, text, lists) |
| `mɒɣg` | a b | reduce (subtract) |
| `tøwp` | a b | times (also repeats text/lists, at most `100000` items) |
| `χɬkevk` | a b | distribute (floor divide) |
| `geft` | a b | remaining (modulo) |
| `ķus'ər` | a | twice |
| `əxķus'ər` | a | half, rounded down |
| `lu'f` | a b | energize (`a ** b`, `b ≥ 0`) |
| `'uɬč` | n | astray — random integer in `[0, n)` |

### Logic and binding

| Word | Objects | Meaning |
| --- | --- | --- |
| `ǆ'ynpp` | a b | equal (same kind; `1` is not `əxbytp`) |
| `grmɒɣg` | a b | less than (two numbers, or two texts) |
| `korxgr` | a b | more than (two numbers, or two texts) |
| `əx` | a | not (verb). As the first word after `^`, `əx` is unless |
| `xə` | a b | and — yields truth; **both** objects run |
| `ðə` | a b | or — yields truth; **both** objects run |
| `ʁšθakɴ` | cond a b | choose a if cond else b; **all three** objects run |
| `ţə''` | value place | put |

### Speak, convert

| Word | Objects | Meaning |
| --- | --- | --- |
| `pihš` | a | speak (print, yield a) |
| `krepg` | a | reveal in source form |
| `'ətsxn` | prompt | ask a line of input |
| `asərθ` | a | to number |
| `xušv` | a | to text |
| `πøkk` | a | type word |

### Collections

| Word | Objects | Meaning |
| --- | --- | --- |
| `ťewn` | x₁ … xₙ n | list of n items |
| `tekt` | k₁ v₁ … kₙ vₙ n | book of n entries |
| `ronɣ` | n | turns — `[0, n)`, at most `100000` numbers |
| `tapq` | coll key | get (`-1` is the last item) |
| `bɬølπ` | list item | fill (append; yields the list) |
| `čxət'` | coll key | exile (remove and yield) |
| `'iixtfu'q` | coll | beginning |
| `ǩeǆylqitsodrm` | coll | bottom |
| `samk` | coll | long (length) |
| `dl` | item coll | in |
| `rukxtekt` | book | notebook (keys) |
| `tluxt` | coll | copy (shallow) |
| `ɣɒzɢ` | coll start end | flay (slice); `əixiww` is an open end |
| `pən'g` | text sep | break (split); empty sep splits characters |
| `raφoj` | list sep | link (join) |

### Control, modules, process

| Word | Objects | Meaning |
| --- | --- | --- |
| `'iţpənn` | (value)? | return |
| `lups` | — | stop the loop |
| `ɢnagɮ` | — | next turn |
| `ɬšeɴazv` | a | raise a program mistake |
| `qab'` | code | kill the process with that exit code |
| `bukð` | path | play/cast — run another `.phyx` / `.vphyx` file |
| `čtəčpliɣn` | args ability | activate a stored ability |
| `naķm` | ability | work — the ability itself (quote) |
| `'uxq` | — | command — list of program arguments (text) |
| `brøtjt` | path | research — read UTF-8 text (file dir, cwd, `PHYX_PATH`; not `phyx/lib/`) |
| `mɴyrx` | text path | spread — write UTF-8 next to the program (never searches); yield the text |

---

## Grammar

```
program     := sentence*
sentence    := start marker? phrase ('.' | ':' body)
start       := '^' | '!' | '?'
body        := sentence          on the same line
             | INDENT sentence+  on following lines
phrase      := clause (',' clause)*
clause      := atom ('-' atom)*
atom        := numeral | string | word
```

A `word` that is a known verb is a call. A scanned `ťe` name followed by `naķm` is a name (the ability as a value). Otherwise a `ťe` name is a call when at least as many objects as its arity sit before it; with fewer objects it is a name. Zero-arity `ťe` names are calls unless quoted with `naķm`. Any other word is a name. Markers may only begin a phrase. `ťewn` / `tekt` take a literal count immediately before the verb, then that many items (or key/value pairs) before the count.

---

## Errors

Faults are `ɬšeɴazv`. They name a stage (`symbols`, `grammar`, `runtime`, `program`), a line, the offending source, a **hint** (what to write instead), and the **ability stack** when the fault sat inside `ťe`. A run of the same ability is one entry with a count (`cnt x1000`); the first and last abilities stay visible.

```
ɬšeɴazv [grammar] (line 1, col 2): 'if' is English, not Phyrexian. The mood marker you want is 'ba'.
     1 | ^if-x:
       |  ^
  hint: python -m phyx explain ba
```

`python -m phyx explain WORD` describes any marker, verb, constant, or English alias. Raise your own with `ɬšeɴazv`. Catch with `baqilx` / `qit`. `dekp` is the blame.

---

## Standard herds

Cast with `bukð` before calling. Files live in `phyx/lib/` and are found by the `bukð` search path (file dir, cwd, `PHYX_PATH`, then that library). A name without a suffix is enough. `python -m phyx lib` lists them. Details: [stdlib.md](stdlib.md).

| File | Abilities |
| --- | --- |
| `asərθ.phyx` | `abs`, `min`, `max`, `sum`, `ǩeznasərθ` (gcd) |
| `ťewn.phyx` | `map`, `filter`, `reverse`, `sort` (insertion, least first) |
| `compleat.phyx` | both herds |

`map` / `filter` take a list and an ability (`name-naķm`). `examples/lib_*.phyx` are aliases of the same herds.

## Execution

A program is compiled to Python and run by CPython. `ťe` becomes a nested `def`; `baxuφ` / `aχəw'` become `while` / `for`; `ţə''` is assignment. Verbs keep Phyrexian faults (`cannot add`, division by zero) instead of raw `TypeError`.

Set `PHYX_TREEWALK=1` to walk the AST instead (slower; same results). `python -m phyx bench` times compiled φyrx against the same code in Python, and it measures that compiled engine even when `PHYX_TREEWALK=1`. `PHYX_RECURSION` (decimal, default `16384`) is the host recursion ceiling for a program thread with a 64 MiB stack. Passing it is `the abilities called each other too deeply`, with no line, and the ability stack is still reported. See [toolchain.md](toolchain.md).

A host `MemoryError` is `the program ran out of memory` and can be caught with `baqilx`. A value nested too deeply to show or compare is `this value is nested too deeply`. Source nested too deeply to parse, compile, format, or lint is a grammar fault, `this program is nested too deeply`, on the line where the nesting starts. Ctrl-C exits `130`.

## Turing completeness

The language has unbounded integers, unbounded lists (`bɬølπ` grows a tape in either direction by concatenating), conditional `ba` / `bu`, unbounded `baxuφ`, and recursive `ťe`. That set can simulate a Turing machine. `examples/11_machine.phyx` is a unary adder: state + head + tape, transition table `δ`, halt when the state is `3`.

## Provenance

Phyrexian script, romanisation, grammar and lexicon: [fxbuson/PhyrexianDictionary](https://fxbuson.github.io/PhyrexianDictionary/), itself a compilation of the community reading of Wizards of the Coast’s Phyrexian. The font and dictionary JSON are **GPL-3.0**; this toolchain does not vendor them. φyrx (PhyrxScript / PhyrexianScript) the language and interpreter are **MIT**.

Reserved words are dictionary entries. The mapping of mood markers onto statement forms, and of verbs onto operations, is the language design: it is consistent, but it is still a mapping.

**Verb conjugation** (tutorial chapter 3) inflects a lexicon verb for person: a vowel before the last consonant, 1 me / 2 you / 3 they / 4 one. The lemma is 3→3 (`babg`, `qab'`). `babeg` is they→one of `babg` and still adds. Tense is the mood marker (`xe` / `'u`), never the verb. Chapter 4 unclear particles are not lexicon.

**Basilica numerals** (tutorial chapter 1) are Mathematical Monospace hex digits. They tokenise as the same hexadecimal numbers as `0–9a–f`.
