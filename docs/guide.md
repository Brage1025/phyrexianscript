# Writing φyrx (PhyrxScript)

This is the programming guide. New to Phyrexian? Start at [tour.md](tour.md). The verb list lives in [reference.md](reference.md). The commands live in [toolchain.md](toolchain.md). The shipped herds live in [stdlib.md](stdlib.md).

φyrx is not a C-family language with Phyrexian paint. If you reach for parentheses, infix `+`, or `if (x) {`, the parser will not meet you there. Write *sentences* whose grammar is the dictionary’s grammar.

---

## 1. A sentence is one thought

Every sentence starts with a start symbol and ends with `.` (or `:` if it opens a body):

| Symbol | Role |
| --- | --- |
| `^` | statement |
| `!` | exclamation — **speak** (print) the phrase |
| `?` | question — **ask**, store the reply in the last word |
| `.` | end of sentence |
| `:` | end of header; the next sentence is the body |
| `-` | word separator (a line break also separates words) |
| `,` | phrase separator; values to the left cannot be taken as later objects |
| `^rukx …` | a note (comment) to the end of the line |
| `#! …` | shebang on line 1; ignored |

```
!"šdeχd-keθəɢð".
^xe-5-x-ţə''.
```

Save files as **UTF-8**. Extensions: `.phyx` (one Phyrexian line per text row) or `.vphyx` (true vertical columns).

---

## 2. The verb comes last

Phyrexian is SOV. Objects are written first, the verb last. φyrx is therefore **postfix**.

```
^xe-1-2-babg-x-ţə''.
```

Read: *indicative — 1, 2, add, x, put*. The value `1 + 2` is put into `x`.

A phrase is a stack. Each verb pops the objects sitting immediately before it and pushes a result. There is no operator precedence, because there are no operators.

```
1-2-babg-3-tøwp     (1 + 2) × 3
1,2-babg            wrong: the comma fences 1 off
```

The dictionary lemma is **3→3** (they / them): `babg`, `qab'`, `ţə''`. Tutorial chapter 3 inserts a vowel before the last consonant for other persons (`babeg` is they-add-one). That is **who acts**, not when. Tense and mood stay on the first word (`xe` present, `'u` past). `1-2-babeg` is the same add as `1-2-babg`. `python -m phyx explain babeg` names the persons.

---

## 3. The first word selects the kind of sentence

The dictionary puts a **mood/tense marker** at the beginning of every phrase. In φyrx that marker *is* the statement form:

| Marker | Dictionary | Statement |
| --- | --- | --- |
| `xe` | indicative | evaluate the phrase |
| `'u` | past indicative | assignment is **constant** |
| `lo` | imperative | same as `xe`; conventionally “do” |
| `ba` | conditional | **if** |
| `bu` / `əx` | negative conditional | **unless** (as the first word; later, `əx` is the verb *not*) |
| `qit` | instead | **else** / **catch**; may be `qit-ba` (else-if) |
| `baxuφ` | if + when = whenever | **while** |
| `aχəw'` | each | **for each** `ITEM` `dl` (in) `COLLECTION` |
| `ťe` | potential (“X can Y”) | **define** ability Y |
| `ǩaπa` | jussive (“must”) | **assert** |
| `baqilx` | if would | **try**; `qit` is the catch |

If the marker is omitted after `^`, `xe` is assumed. `əx` is unless only when it is that first word: `^əx-n:` is “unless n”. In `^xe-n-əx.` it is the verb *not*.

```
^ba-x-0-korxgr:
    !x.
^qit:
    !"void".
```

The body may sit on the same line: `^ba-x:lo-1-'iţpənn.` Indent with spaces (a tab counts as four). The body must be deeper than its header.

---

## 4. Numbers are hexadecimal

Phyrexian counts in base 16. `10` is sixteen, `0a` is ten, `0ff` is 255. Output is hexadecimal too, so it can be pasted back into a program. Negative numerals glue the negative prefix `əx` onto the digits: `əx1a` is −26.

The number-words `'ii` (1), `ķu` (2), `ķi` (3) are constants. There is no decimal mode.

---

## 5. Names, verbs, and reserved words

A word is a **verb** if it is in the standard lexicon (`babg`, `ţə''`, `'uxq`, …) or a `ťe` name in this file (or in a file this file `bukð`s). Otherwise it is a **name**, and must already have been bound with `ţə''` when the sentence runs.

You may not bind a reserved word. `python -m phyx words` is the authoritative list; `python -m phyx explain if` maps English to the marker; `python -m phyx lookup add` searches the lexicon (no fetch required). `python -m phyx lint FILE` names a dropped `'iţpənn` and unused objects.

```
^xe-5-x-ţə''.         x = 5
^'u-5-x-ţə''.         x = 5 forever
^xe-1-xs-0-tapq-ţə''. xs[0] = 1
```

`ţə''` takes **value then place**. Assignment is an expression: it yields the value.

---

## 6. Lists and books: the count comes last

`ťewn` and `tekt` are variadic. The **plain numeral immediately before the verb is the length**, not an element:

```
1-2-3-3-ťewn          list [1, 2, 3]
0-ťewn                empty list
"k"-5-1-tekt          book { "k": 5 }
```

`!1-ťewn` is a mistake: the `1` is the *count*, so the list still wants one item in front of it. Write `1-1-ťewn` or `0-ťewn`.

The count must be a numeral in the source. When the length is computed, build with `bɬølπ` (fill).

---

## 7. Abilities

`ťe` — potential mood, “these objects can *name*”:

```
^ťe-a-b-šχa'θbabg:
    ^lo-a-b-babg-ķus'ər-'iţpənn.
!3-4-šχa'θbabg.
```

- The last word is the ability’s name; the words before it are parameter names.
- Call site uses the same order: objects, then the name.
- Definitions are visible throughout the file (you may call an ability above its `ťe`).
- Nested `ťe` closes over the surrounding names.
- `'iţpənn` returns the object before it, or void if there is none.

An ability is a value. Written with fewer objects than its arity, the word *is* the ability rather than a call:

```
^xe-šχa'θbabg-fn-ţə''.
!3-4-2-ťewn-fn-čtəčpliɣn.
```

A **zero-parameter** ability is always a call. To hold onto it, quote it with `naķm` (make/work — “the work itself”):

```
^ťe-greet:
    !"šdeχd".
^xe-greet-naķm-fn-ţə''.
^lo-0-ťewn-fn-čtəčpliɣn.
```

`čtəčpliɣn` (activate) takes a list of objects and an ability.

---

## 8. Modules and arguments

`bukð` (play/cast) runs another file in the current session. Ability *names* from that file are visible to the parser; the file’s sentences still run when `bukð` is evaluated. **Cast first, then call.**

Search order: this file’s directory, the working directory, `PHYX_PATH`, then the shipped library (`phyx/lib`). A name without `.phyx` is enough.

```
^lo-"compleat.phyx"-bukð.
!30-12-ǩeznasərθ.
!3-1-2-3-ťewn-sort.
```

`python -m phyx lib` lists the herds. Tests of those herds and of core sentences: `python -m phyx test`. Details: [stdlib.md](stdlib.md).

UTF-8 notes: `mɴyrx` writes next to this file; `brøtjt` reads from this file’s directory, the working directory, or `PHYX_PATH` (not `phyx/lib/`).

`'uxq` (command) is the list of text arguments given to the program. Empty in the REPL.

```
python -m phyx examples/10_command.phyx red blue
```

```
^aχəw'-w-dl-'uxq:
    !w.
```

---

## 9. A worked translation

Python:

```python
n = 0
while n < 5:
    n = n + 1
    print(n)
```

φyrx:

```
^xe-0-n-ţə''.
^baxuφ-n-5-grmɒɣg:
    ^xe-n-'ii-babg-n-ţə''.
    !n.
```

A function:

```python
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

```
^ťe-n-fib:
    ^ba-n-ķu-grmɒɣg:lo-n-'iţpənn.
    ^lo-n-'ii-mɒɣg-fib-n-ķu-mɒɣg-fib-babg-'iţpənn.
!0a-fib.
```

`ťe` is “can”: *n can fib*. Objects come first when you define it and when you call it: `0a-fib`.

---

## 10. What will not parse

| You might write | Why it fails | Write |
| --- | --- | --- |
| `1 + 2` | infix is not Phyrexian | `1-2-babg` |
| `(1-2-babg)` | no parentheses | word order |
| `if x:` | English keywords | `^ba-x:` |
| `!1-ťewn` | `1` is the length | `1-1-ťewn` or `0-ťewn` |
| `1,2-babg` | comma fences `1` off | `1-2-babg` |
| `xe-1-x-ţə''.` | every sentence needs `^` `!` or `?` | `^xe-1-x-ţə''.` |
| `babg` as a name | reserved | pick an unused word |
| `^xe-greet-fn-ţə''.` for a 0-parameter `ťe` | that *calls* greet | `^xe-greet-naķm-fn-ţə''.` |

Worked programs: `examples/01_welcome.phyx` through `examples/15_conjugation.phyx`. Coming from Python: [python.md](python.md). Recipes: [cookbook.md](cookbook.md). Normative grammar: [spec.md](spec.md). Why these choices: [rationale.md](rationale.md). Docs map: [index.md](index.md).

---

## 11. Turing-complete, running on CPython

φyrx is Turing-complete in the ordinary sense: `baxuφ` loops while a condition holds, lists grow with `bɬølπ`, and `ťe` abilities may call themselves. That is the WHILE language plus a tape. `examples/11_machine.phyx` is a Turing machine that adds `1^m 0 1^n` on a tape.

The toolchain compiles each program to Python and lets CPython execute it. Write Phyrexian; the hot path is a Python `while` and Python integers (unbounded, like Python’s). `python -m phyx bench` prints that side by side with the same Fibonacci and loop in Python.

---

## 12. When a sentence fails

A fault is `ɬšeɴazv`. It names the line, shows it, and — when it can — tells you what to write next.

| You see | It means | Next |
| --- | --- | --- |
| `'if' is English` | a Python keyword in marker position | `^ba-…:` — `python -m phyx explain if` |
| `xe` sentence does not take `:` | you opened a body on an evaluate sentence | ability marker is `ťe`. ASCII files: `--ascii` (`Te` is `ťe`) |
| `unknown word` | the name is not bound | `^xe-VALUE-name-ţə''.` or `python -m phyx words` |
| `wants N objects` | the verb is missing its objects | objects first, then the verb; a comma fences values off |
| `computes a value and drops it` (`lint`) | a `ťe` body never `'iţpənn` | end with `'iţpənn` if you meant to give a value back |
| `'fn' is English` | — | it is not. `fn` is a fine name for a stored ability |

```
python -m phyx explain WORD
python -m phyx lint FILE
python -m phyx --ascii FILE          # ASCII-capital spelling (examples/07_ascii.phyx)
```
