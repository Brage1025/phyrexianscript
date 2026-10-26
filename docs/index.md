# φyrx documentation

**φyrx** (also **PhyrxScript**, **PhyrexianScript**) is a programming language written in Phyrexian. A program is a sequence of dictionary sentences: the verb comes last, numbers are hexadecimal, mood markers select the kind of statement.

Start here, then pick the page that matches the job.

| If you want to… | Read |
| --- | --- |
| Write a first program today | [tour.md](tour.md) — ten minutes, no Phyrexian assumed |
| Learn the language properly | [guide.md](guide.md) — sentences, verbs, abilities, modules, faults |
| Look up a word | [reference.md](reference.md) — types, markers, verbs, herds |
| Cast `sort` / `abs` / `map` | [stdlib.md](stdlib.md) — search path and every shipped ability |
| Come from Python | [python.md](python.md) |
| Copy a short recipe | [cookbook.md](cookbook.md) |
| Run, test, format, highlight | [toolchain.md](toolchain.md) |
| Know what is normative | [spec.md](spec.md) |
| Know why it is this shape | [rationale.md](rationale.md) |
| See known issues and how decisions are made | [roadmap.md](roadmap.md) |
| See what changed | [../CHANGELOG.md](../CHANGELOG.md) |

φyrx is Turing-complete in the ordinary sense: unbounded lists, `baxuφ`, and recursive `ťe` run a Turing machine (`examples/11_machine.phyx`). The toolchain compiles each program to CPython. An ability becomes a Python function, and arithmetic on a name keeps a kind guard, so a bad kind is still a Phyrexian fault. `PHYX_TREEWALK=1` walks the tree instead.

The standard library is φyrx: `phyx/lib/` is on the `bukð` search path. `python -m phyx test` runs tests written in φyrx (`ǩaπa` is the assertion; a sibling `.expected` file is exact stdout). `python -m phyx lookup` searches the lexicon without a fetch.

Faults name the fix and the ability stack. `python -m phyx explain if` answers in Phyrexian. `fmt` rewrites a file into canonical separators and indent. `lint` names a dropped `'iţpənn`, an unused object, an English keyword used as a name, and a short call of an ability defined in the same file.

A program can bind names, close over them, store abilities, build lists and books, cast modules, read and write UTF-8 notes (`brøtjt` / `mɴyrx`), read program arguments, and run in the REPL. `render` sets the text in vertical columns in the official Phyrexian font.

Verbs may take chapter-3 person inflection (`babeg` is `babg`); tense is the mood marker. Numerals may be Arabic hex or Basilica Mathematical Monospace. The word-to-meaning mapping and the licence split are in [reference.md](reference.md#provenance).

Install nothing to try it:

```
python -m phyx examples/01_welcome.phyx
python -m phyx                          # interactive session
python -m phyx words                    # every marker, verb, constant
python -m phyx explain if               # English → ba
python -m phyx lib                      # shipped herds
python -m phyx test                     # tests written in φyrx
```

Worked programs: `examples/01_welcome.phyx` through `examples/15_conjugation.phyx`. Editor grammars: `editors/` (TextMate and Vim, generated from the lexicon). The dictionary the language follows: [Phyrexian Dictionary](https://fxbuson.github.io/PhyrexianDictionary/).
