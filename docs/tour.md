# A tour of φyrx

This page assumes you have never read Phyrexian and have never opened this repository. After it you can write a file, run it, cast the standard library, and fail a test on purpose.

The language is **φyrx** (PhyrxScript / PhyrexianScript). Its grammar is the community [Phyrexian Dictionary](https://fxbuson.github.io/PhyrexianDictionary/), not a C-family syntax with a font on top.

---

## 0. Run something

From the project folder, with Python 3.11 or newer:

```
python -m phyx examples/01_welcome.phyx
```

You should see three lines of output, the first of which is Phyrexian for a greeting. No install step. `pip install -e .` only puts `phyx` on your PATH.

Typing special letters is painful. This is the same program in ASCII capitals (a capital stands for the special letter it resembles):

```
python -m phyx --ascii examples/07_ascii.phyx
```

`python -m phyx explain if` prints the Phyrexian word for *if*. Keep that command nearby.

---

## 1. A program is sentences

Every sentence starts with `^` (statement), `!` (speak / print), or `?` (ask), and ends with `.` (or `:` if a body follows).

Words are separated by `-`. The **verb is last**. Numbers are **hexadecimal**: `10` is sixteen, `0a` is ten. Basilica Mathematical Monospace digits are the same hex, not a second syntax. A conjugated verb (`babeg`) is still the lemma (`babg`); tense is `xe` / `'u`, never the verb.

```
!"šdeχd".
^xe-1-2-babg-x-ţə''.
!x.
```

Read the middle sentence as: *indicative — 1, 2, add, x, put*. `x` becomes three.

A comma is a fence: values to its left cannot be objects of verbs to its right. There is no operator precedence, because there are no operators.

`^rukx` through end of line is a note (a comment).

Save the file as UTF-8 with the extension `.phyx`.

---

## 2. The first word picks the statement

Phyrexian phrases open with a mood. In φyrx that mood **is** the statement form:

| Write | Means |
| --- | --- |
| `^xe-…` | evaluate (you may omit `xe` after `^`) |
| `^ba-cond:` … `^qit:` | if / else |
| `^baxuφ-cond:` | while |
| `^aχəw'-item-dl-xs:` | for each `item` in `xs` |
| `^ťe-n-fib:` | define the ability `fib` |
| `^ǩaπa-cond.` | must — assertion |
| `^lo-value-'iţpənn.` | return `value` from an ability |

```
^ťe-n-dub:
    ^lo-n-ķus'ər-'iţpənn.

!5-dub.
```

`ķus'ər` is *twice*. The program speaks `0a` (ten).

A body after `:` is indented, or written on the same line: `^ba-n:lo-n-'iţpənn.`

---

## 3. Lists, then a count, then the verb

`ťewn` means *list*. Phyrexian is SOV, so the items come first, the length next to the verb, the verb last:

```
^xe-3-1-4-3-ťewn-xs-ţə''.
!xs.
```

That is the list `[3, 1, 4]`. Empty: `0-ťewn`. `!1-ťewn` is a count of one with no item — a grammar fault, not a singleton.

---

## 4. Cast the standard library

`bukð` means *play / cast*. It runs another `.phyx` file in this session. Ability names in that file become verbs here. **Cast first, then call.**

```
^lo-"compleat.phyx"-bukð.
!3-1-4-1-5-5-ťewn-sort.
!əx0a-abs.
```

Search order for that path: the directory of the file that is casting, the working directory, the environment variable `PHYX_PATH`, then the shipped library `phyx/lib/`. You may omit `.phyx`.

```
python -m phyx lib
```

lists every shipped herd. Details: [stdlib.md](stdlib.md).

---

## 5. Test in φyrx

`ǩaπa` is *must*. A false condition is a runtime fault. Put tests in `tests/phyx/test_*.phyx`:

```
^lo-"asərθ.phyx"-bukð.
^ǩaπa-əx0a-abs-0a-ǆ'ynpp.
```

```
python -m phyx test
```

discovers those files and reports `ok` or `FAIL`. A test passes when the file finishes without a fault. A sibling `.expected` file, if present, must match stdout exactly.

---

## 6. What to read next

| Page | Why |
| --- | --- |
| [guide.md](guide.md) | the rest of the language, including faults |
| [reference.md](reference.md) | every verb, with arities |
| [python.md](python.md) | `if` is `ba`, `def` is `ťe`, `import` is `bukð` |
| [toolchain.md](toolchain.md) | `fmt`, `lint`, `dis`, `repl`, vertical script |
| [spec.md](spec.md) | what a conforming implementation must do |

`python -m phyx words` is the lexicon in your terminal. `python -m phyx explain WORD` is the lexicon at the moment you need it.
