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
| See what is still open | [remaining.md](remaining.md) |
| See what changed | [../CHANGELOG.md](../CHANGELOG.md) |

Install nothing to try it:

```
python -m phyx examples/01_welcome.phyx
python -m phyx                          # interactive session
python -m phyx words                    # every marker, verb, constant
python -m phyx explain if               # English → ba
python -m phyx lib                      # shipped herds
python -m phyx test                     # tests written in φyrx
```

Worked programs: `examples/01_welcome.phyx` through `examples/15_conjugation.phyx`. Editor grammars: `editors/`. The dictionary the language follows: [Phyrexian Dictionary](https://fxbuson.github.io/PhyrexianDictionary/).
