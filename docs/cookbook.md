# φyrx cookbook

Short programs. Copy, change the objects, keep the verb last. Hexadecimal throughout. Stuck on a word? `python -m phyx explain if`. New to the language? [tour.md](tour.md).

---

## Person on the verb, tense on the marker

```
!1-2-babg.
!1-2-babeg.
```

Both add. `babeg` is they→one (chapter 3). Past would be `^'u-1-2-babg.`, not a different verb. `python -m phyx explain babeg`.

---

## Bind, speak, ask

```
^xe-5-x-ţə''.
!x.
?"name: "-nɒqč.
!nɒqč.
```

`ţə''` is put: **value then place**. `!` speaks; `?` asks and binds the last word.

---

## Count, branch, loop

```
^xe-0-n-ţə''.
^baxuφ-n-5-grmɒɣg:
    ^xe-n-'ii-babg-n-ţə''.
    ^ba-n-ķu-geft:
        !"odd",n.
    ^qit:
        !"even",n.
```

`grmɒɣg` is `<`. `geft` is remainder. `qit` is instead.

---

## Lists and books

```
^xe-1-2-3-3-ťewn-xs-ţə''.
^xe-xs-4-bɬølπ.
!xs-samk,xs-0-tapq.
^xe-9-xs-1-tapq-ţə''.

^xe-"a"-1-"b"-2-2-tekt-book-ţə''.
!book-"a"-tapq,book-rukxtekt.
```

The numeral immediately before `ťewn` / `tekt` is the **count**. Empty list: `0-ťewn`.

---

## Abilities

```
^ťe-a-b-babgķus'ər:
    ^lo-a-b-babg-ķus'ər-'iţpənn.
!3-4-babgķus'ər.
```

Recursive Fibonacci (hex `0a` is ten):

```
^ťe-n-fib:
    ^ba-n-ķu-grmɒɣg:lo-n-'iţpənn.
    ^lo-n-'ii-mɒɣg-fib-n-ķu-mɒɣg-fib-babg-'iţpənn.
!0a-fib.
```

Store a zero-parameter ability with `naķm`, activate with `čtəčpliɣn`:

```
^ťe-greet:
    !"šdeχd".
^xe-greet-naķm-fn-ţə''.
^lo-0-ťewn-fn-čtəčpliɣn.
```

---

## Cast a herd, sort a list

```
^lo-"compleat.phyx"-bukð.
!3-1-4-1-5-5-ťewn-sort.
!1-2-3-3-ťewn-sum.
```

`bukð` first, then call. See `examples/12_sort.phyx` and [stdlib.md](stdlib.md).

---

## Notes on disk

```
^lo-"šdeχd"-"hi.txt"-mɴyrx.
!"hi.txt"-brøtjt.
```

`mɴyrx` (spread) writes UTF-8 next to the program (it never searches). `brøtjt` (research) reads: program directory, working directory, then `PHYX_PATH` — not `phyx/lib/`. Absolute paths are used as written. `examples/13_notes.phyx`.

---

## Command-line arguments

```
#! /usr/bin/env phyx
^aχəw'-w-dl-'uxq:
    !w.
```

```
python -m phyx examples/10_command.phyx red blue
```

---

## Catch a mistake

```
^baqilx:
    ^xe-1-0-χɬkevk.
^qit:
    !dekp.
```

`dekp` is the blame: the value of `ɬšeɴazv`, or the fault message.

---

## A Turing machine

`examples/11_machine.phyx` adds unary `1^m 0 1^n` on a tape. Unbounded `ťewn` + `baxuφ` + `ťe` is enough.

---

## Assert in φyrx

`ǩaπa` is *must*. Put tests in `tests/phyx/test_*.phyx` and run `python -m phyx test`. A sibling `test_foo.expected` is exact stdout when the file speaks.

```
^lo-"asərθ.phyx"-bukð.
^ǩaπa-əx0a-abs-0a-ǆ'ynpp.
```

---

## When it breaks

```
python -m phyx explain if          # English → ba
python -m phyx lint FILE           # dropped 'iţpənn, unused objects
python -m phyx --ascii FILE        # Te is ťe, TTE'' is ţə''
```

`xə` / `ðə` / `ʁšθakɴ` always evaluate every object (there is no skipped arm). `1-əxbytp-ǆ'ynpp` is false: number and truth are different kinds.

---

## See the CPython

```
python -m phyx dis examples/03_abilities.phyx
python -m phyx bench
python -m phyx render examples/01_welcome.phyx -o welcome.html
python -m phyx explain babg
python -m phyx lint examples/03_abilities.phyx
```
