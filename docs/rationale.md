# Why φyrx is this shape

Syntax is remembered. The decisions that produced it disappear. This page is the record so a later change has to argue with the original constraint, not with silence.

φyrx is a programming language written in Phyrexian. That sentence is the constraint. Everything else is downstream of it.

---

## The dictionary is the grammar

The community [Phyrexian Dictionary](https://fxbuson.github.io/PhyrexianDictionary/) already has punctuation, SOV word order, mood/tense markers, and hexadecimal numerals. Inventing C-like syntax and painting it with Phyrexian letters would be a different language that happens to use a font.

So:

- A program is sentences (`^` `!` `?` … `.` / `:`), not files of statements in an invented layout.
- The verb comes last. Expressions are postfix. There is no operator precedence because there are no operators.
- The first word of a phrase is a mood marker. `ba` is if because the dictionary's conditional mood is `ba`, not because we like the letters.
- Numbers are hexadecimal because Phyrexian counts in sixteen. Basilica Mathematical Monospace glyphs are those same sixteen digits, not a second literal form.
- The verb inflects for person (tutorial ch. 3). Tense stays on the mood marker. English `-ed` on `babg` would be a different language.
- New verbs are admitted only when a dictionary word's meaning fits. `min` / `sort` are user abilities in a herd, not fake lexicon.

The cost is real: nobody types `ţə''` by accident. `--ascii` and `python -m phyx explain if` exist because of that cost, not instead of the constraint.

## Compile to CPython, do not write a second VM

A tree-walker in Python cannot match CPython: every `+` is a method call and an AST node. A custom bytecode VM would be slower than CPython and twice the code.

φyrx compiles abilities to `def`, loops to `while` / `for`, integers to Python `int`. The host eval loop is the one that already runs Python. An ability that does no input or output is compiled without the interpreter object. Its operators still use the guarded form. Python `+`, `-`, `*`, `//`, `%`, `**`, `<` and `>` run only when both values are numbers (`type(a) is int and type(b) is int`); otherwise a helper raises `RuntimeFault` with the same message and hint as the tree-walker. Division, remainder and power keep their zero and range checks on that path, so a zero divisor is a Phyrexian fault and a negative `lu'f` is a fault rather than a float. `əx` calls `truthy()`, not Python `not`. The type test is left out only when both objects are provably numbers: an integer literal, or the result of an operator that returns a number whenever it returns (`mɒɣg`, `χɬkevk`, `geft`, `lu'f`, `ķus'ər`, `əxķus'ər`). `babg` and `tøwp` count only when their own objects are already numbers, because they can also join text or repeat a list. A name is never that, because a variable can hold any kind. The fault is raised inside the ability, so `baqilx` can catch it.

The tree-walker remains as `PHYX_TREEWALK=1` so semantics can be compared, not because it is the way to run programs.

## `'u` is const, not “old value”

The past indicative means the fact already obtained. Rebinding a past-indicative name is lying about the past. That is a runtime fault, not a new assignment.

## The count comes last on `ťewn`

Phyrexian is SOV: the items are objects, the verb is `ťewn` (list). A language that needs a length to parse a variadic verb has to write that length next to the verb. So `1-2-3-3-ťewn` — three items, then the count, then the verb. `!1-ťewn` looks like a singleton and is not: `1` is the count. The parser says so. `0-ťewn` is empty.

## Zero-parameter `ťe` must be quoted

A name that is an ability of arity 0, written as a verb, is a call: that is what SOV does. To hold the ability itself we need a dictionary verb that means the work, not the doing. That is `naķm`.

## Errors are part of the language

A competent engineer who joined last week and has never read the compiler should understand a fault. Three jobs, in order: what broke, why, what to do next. English `if` in marker position names `ba`. An unknown word offers a nearby lexicon entry. A fault inside `ťe` names the ability stack.

`python -m phyx explain`, `fmt`, and `lint` are the same idea: the toolchain teaches at the moment it is needed.

## Herds, not invented verbs

`min`, `sort`, and `map` are not in the dictionary, so they are not lexicon verbs. They are `ťe` abilities in `phyx/lib/`, cast with `bukð`, tested with `ǩaπa` in `tests/phyx/`. The search path (file dir, cwd, `PHYX_PATH`, shipped library) is how a language has a standard library without pretending the dictionary grew.

A language that cannot test itself in itself is a host API. `python -m phyx test` runs φyrx files; Python's `unittest` still covers the interpreter.

## MIT interpreter, GPL dictionary/font

The language and toolchain are MIT so they can be used like Python. The official Phyrexian Regular font and the dictionary JSON are GPL-3.0 (Wizards / dictionary repo) and are fetched, not vendored. `phyx fetch` installs them for this user. Rendered HTML embeds the font as family `Phyrexian` (the TTF's family name).

## What will not be added

Floats, classes, infix `+`, decimal literals, `async`, comprehensions. Not because they are hard — because they are not Phyrexian. Model a record as a book. Count in hex. Put the verb last.

If a future change needs a word the dictionary does not have, the change is wrong, or the dictionary grew and the mapping can be revisited in the open.
