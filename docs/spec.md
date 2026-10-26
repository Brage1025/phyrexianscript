# φyrx language specification (1.6)

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

`tøwp` repeats text or a list. The result is at most `100000` items (1,048,576). A longer repetition is a runtime fault. A count that is not positive yields an empty text or an empty list, and so does repeating an empty text or an empty list by any count. `ronɣ` is the list `[0, n)` and is at most `100000` numbers; a larger `n` is a runtime fault. A negative `n` is empty. Multiplying two numbers is not subject to this bound.

`ǆ'ynpp` is equal only when both values have the same kind: a number is never equal to a truth. `xə` / `ðə` yield truth and evaluate both objects. `ʁšθakɴ` evaluates the condition and both arms (objects sit before the verb).

### Standard verbs

This subsection defines every verb. The table in [reference.md](reference.md#standard-verbs) is a convenience copy and is not normative.

A phrase is a stack (section 3). The objects column is how many values the verb takes, written before it, left to right. It then leaves one result. `ťewn` and `tekt` are the count form: the value immediately before the verb is a plain numeral `n` (an integer numeral, zero or greater; not a truth, not a negative numeral, not a name). `ťewn` then gathers the `n` items written before that numeral. `tekt` gathers `n` pairs written key then value, which is `2n` values before the numeral. `1-2-3-3-ťewn`, `0-ťewn`, and `0-tekt` are the usual shapes.

`'iţpənn` takes one object when the clause has one before it, and takes none otherwise. `lups` and `ɢnagɮ` take none. `ţə''` takes a value and a place. The place is a name or a `tapq` place.

A fixed-arity verb with fewer objects than that count is a grammar fault, `the verb '…' wants N object(s) before it`. The wording is the same for every such verb and is not repeated on the rows.

Two host faults are named once here. Showing or comparing a value nested too deeply (`pihš`, `krepg`, `xušv`, `raφoj`, `ǆ'ynpp`, and `dl` on a list) raises `this value is nested too deeply` ([section 7](#7-faults)). `babg` raises `the program ran out of memory` when the host cannot allocate the sum ([section 7](#7-faults)). A cell `none` means the verb raises no further fault.

`χɬkevk` is the greatest integer that is not above the real quotient. `geft` is the remainder of that division: `a` equals `(a χɬkevk b)` times `b`, plus `(a geft b)`, and the remainder has the sign of `b`.

Each other fault cell quotes the message text and states when it is raised. The printed fault also carries a kind, a line, and a hint. Hints may grow ([section 8](#8-host)).

#### Arithmetic

| Verb | Objects | Result | Faults |
| --- | --- | --- | --- |
| `babg` | 2: a b | The sum of two numbers, or the joining of two texts, or the joining of two lists. | When the values are not a pair of numbers, a pair of texts, or a pair of lists, the message names those two kinds. A number and a text: `cannot add asərθ (number) and rukx (text)`. The host memory fault named above applies when the sum cannot be allocated. |
| `mɒɣg` | 2: a b | The first number minus the second. | When an object is not a number, the message names the first such object. A text: `'mɒɣg' needs a number, got rukx (text)`. |
| `tøwp` | 2: a b | The product of two numbers. A text or a list, then a number, repeats that text or list. A count that is not positive yields an empty text or an empty list, and so does repeating an empty text or an empty list by any count. Two numbers are not subject to the length limit in section 5. | When the values are not two numbers and not a text or list followed by a number: `cannot multiply rukx (text) and rukx (text)`. When the repeated result would be longer than 100000 items: `tøwp (times): the repetition is too great`. |
| `χɬkevk` | 2: a b | The floor quotient of the two numbers, as defined above. | When the second number is zero: `nothing can be distributed into zero parts`. When an object is not a number, the message names the first such object. A text: `'χɬkevk' needs a number, got rukx (text)`. |
| `geft` | 2: a b | The remainder of the floor division above. | When the second number is zero: `nothing remains when dividing by zero`. When an object is not a number, the message names the first such object. A text: `'geft' needs a number, got rukx (text)`. |
| `ķus'ər` | 1: a | The number times two. | When the object is not a number. A text: `'ķus'ər' needs a number, got rukx (text)`. |
| `əxķus'ər` | 1: a | The number floor-divided by two. | When the object is not a number. A text: `'əxķus'ər' needs a number, got rukx (text)`. |
| `lu'f` | 2: a b | The first number raised to the second. The exponent may be zero, and `0` raised to `0` is `1`. The greatest allowed exponent is the decimal value 10000 (numeral `2710`). | When the exponent is negative: `lu'f (energize) cannot raise to a negative power`. When the exponent is greater than that decimal 10000: `lu'f (energize): the exponent is too great`. When an object is not a number, the message names the first such object. A text: `'lu'f' needs a number, got rukx (text)`. |
| `'uɬč` | 1: n | An integer in the range from 0 up to, and not including, `n`. Which integer a run draws is chosen by that run. | When n is not greater than zero: `'uɬč (astray) needs a bound greater than zero`. When the object is not a number. A text: `''uɬč' needs a number, got rukx (text)`. |

#### Logic and binding

| Verb | Objects | Result | Faults |
| --- | --- | --- | --- |
| `ǆ'ynpp` | 2: a b | Truth. True when the values have the same kind and equal contents. A number and a truth are not equal. | none |
| `grmɒɣg` | 2: a b | Truth. True when the first number is less than the second, or the first text is less than the second in code-point order. | When the values are not two numbers or two texts, the message names both kinds. A text and a number: `'grmɒɣg' cannot order rukx (text) and asərθ (number)`. |
| `korxgr` | 2: a b | Truth. True when the first number is greater than the second, or the first text is greater than the second in code-point order. | When the values are not two numbers or two texts, the message names both kinds. A number and a list: `'korxgr' cannot order asərθ (number) and ťewn (list)`. |
| `əx` | 1: a | Truth. True when the object is not truthy. Section 4 gives what is truthy. | none |
| `xə` | 2: a b | Truth. True when both objects are truthy. Both objects are evaluated. | none |
| `ðə` | 2: a b | Truth. True when at least one object is truthy. Both objects are evaluated. | none |
| `ʁšθakɴ` | 3: cond a b | `a` when `cond` is truthy, and `b` otherwise. All three objects are evaluated. | none |
| `ţə''` | 2: value place | The value, after it is stored. A name is bound as in [Scope](#scope). A `tapq` place stores into that list index or book entry. A new book key is added. The list or book is changed in place. | Grammar fault when the place is not a name or a tapq place: `the target of ţə'' (put) must be a name or a 'tapq' place`. When the place is a text: `text cannot be changed in place; build a new text instead`. When the place is some other value. A number: `cannot put into asərθ (number)`. When a list index is outside the list, the message names the length and the index in source form. A list of one item and index 5: `the list has 1 items; there is no item 5`. When the name was fixed with 'u: `'x' was fixed in the past ('u) and cannot change`. When 'u fixes a name that already holds a value in the running scope: `'x' already has a value here and cannot be fixed in the past ('u)`. When a book key cannot be stored. A list: `a book cannot be keyed by a list ('ţə''')`. |

#### Speak, convert

| Verb | Objects | Result | Faults |
| --- | --- | --- | --- |
| `pihš` | 1: a | The same value, after its spoken form and a newline are written. | none |
| `krepg` | 1: a | The same value, after its source form and a newline are written. | none |
| `'ətsxn` | 1: prompt | The line read after the prompt is written, without the line ending. Void when input has ended. | none |
| `asərθ` | 1: a | A number stays that number. A truth becomes `1` or `0`. Text is read as a hexadecimal numeral, after surrounding space is dropped; a leading `əx` or `-` makes it negative. Basilica digits are accepted, as in section 2. | When text is not such a numeral. The text xyz: `'xyz' is not a hexadecimal numeral`. When the object is any other kind. A list: `cannot turn ťewn (list) into a number`. |
| `xušv` | 1: a | The spoken text of the value. | none |
| `πøkk` | 1: a | The type word of the value, from section 4. | none |

#### Collections

| Verb | Objects | Result | Faults |
| --- | --- | --- | --- |
| `ťewn` | count: items, then numeral n | The list of those items, in the order written. | Grammar fault when the count is not a plain numeral as defined above: `'ťewn' (list) must be preceded by a plain numeral giving how many items to gather`. Grammar fault when fewer items are present. A count of 1 with no item: `'ťewn' (list) wants 1 item before the count 1, but only 0 are there. Write the items first, then the count, then ťewn (empty: 0-ťewn)`. |
| `tekt` | count: pairs, then numeral n | The book of those pairs. A key written again keeps the later value. Keys stay in the order they were first written. A key is stored with host equality, so the number `1` and the truth `əxbytp` are the same key. | Grammar fault when the count is not a plain numeral: `'tekt' (book) must be preceded by a plain numeral giving how many items to gather`. Grammar fault when fewer values are present. A count of 1 with nothing before it: `'tekt' (book) wants 1 entry (key and value each) before the count 1, but only 0 are there. Write the items first, then the count, then tekt (empty: 0-tekt)`. When a key cannot be stored. A list: `a book cannot be keyed by a list ('tekt')`. |
| `ronɣ` | 1: n | The list of numbers from 0 up to, and not including, `n`. Empty when `n` is not positive. At most `100000` numbers, as in section 5. | When n is not a number. A text: `'ronɣ' needs a number, got rukx (text)`. When n is greater than 100000: `ronɣ (turns): the count is too great`. |
| `tapq` | 2: coll key | The list item, the text character, or the book entry at that key. A negative number on a list or a text counts from the end. | When a book has no such entry, the message names the key in source form. A missing text key k: `the book has no entry "k"`. When a list or text index is not a number, the message names the collection kind and the key kind. A text key on text: `'tapq' needs a number to pick from a text, got rukx (text)`. When that index is outside the collection, the message names the kind, the length, and the index in source form. A list of one item and index 5: `the list has 1 items; there is no item 5`. A text of two characters and index 5: `the text has 2 items; there is no item 5`. When the key cannot be a book key. A list: `a book cannot be keyed by a list ('tapq')`. When the collection is any other kind. A number: `cannot get from asərθ (number)`. |
| `bɬølπ` | 2: list item | The same list, with the item appended. | When the first object is not a list. A number: `'bɬølπ' needs a list, got asərθ (number)`. |
| `čxət'` | 2: coll key | The removed list item or book entry. A negative number on a list counts from the end. | When a list index is outside the list. An empty list and index 0: `the list has 0 items; there is no item 0`. When a book has no such entry. A missing text key k: `the book has no entry "k"`. When a book key cannot be stored. A list: `a book cannot be keyed by a list ('čxət'')`. When the collection is any other kind. A text: `cannot exile from rukx (text)`. |
| `'iixtfu'q` | 1: coll | The first item of a list, or the first character of a text. | When the list or text is empty, the message names that kind. An empty list: `an empty list has no beginning`. When the value is any other kind. A number: `asərθ (number) has no beginning`. |
| `ǩeǆylqitsodrm` | 1: coll | The last item of a list, or the last character of a text. | When the list or text is empty, the message names that kind. An empty list: `an empty list has no bottom`. When the value is any other kind. A number: `asərθ (number) has no bottom`. |
| `samk` | 1: coll | The number of list items, text characters, or book entries. | When the value is any other kind. A number: `asərθ (number) has no length`. |
| `dl` | 2: item coll | Truth. True when the item equals an element of the list (same kind and contents), or is a key of the book, or occurs as a substring of the text. The empty text occurs inside every text, including the empty text. | When the collection is text and the item is not text. A number: `only text can be found inside text, not asərθ (number)`. When a book key cannot be stored. A list: `a book cannot be keyed by a list ('dl')`. When the collection is any other kind. A number: `nothing can be inside asərθ (number)`. |
| `rukxtekt` | 1: book | The list of the book's keys, in the order the keys were first written. | When the object is not a book. A list: `'rukxtekt' needs a book, got ťewn (list)`. |
| `tluxt` | 1: coll | A new list or a new book with the same immediate entries. A nested list or book is shared with the original. Any other value is returned as itself. | none |
| `ɣɒzɢ` | 3: coll start end | The list or text from `start` up to, and not including, `end`. `əixiww` leaves that end open. An index past the end yields an empty list or an empty text. A negative index counts from the end in the same way. | When the collection is not a list or a text. A number: `cannot flay asərθ (number)`. When start or end is neither a number nor void. A text: `'ɣɒzɢ' needs a number, got rukx (text)`. |
| `pən'g` | 2: text sep | The list of pieces of the text split on the separator. An empty separator yields one text per character. A separator at the end leaves an empty text at the end of the list. | When either object is not text, the message names both kinds. A number and a text: `'pən'g' breaks text with text, got asərθ (number) and rukx (text)`. |
| `raφoj` | 2: list sep | The text made by joining the spoken form of each item with the separator. An empty list yields an empty text. | When the separator is not text. A number: `'raφoj' links with text, got asərθ (number)`. When the first object is not a list. A text: `'raφoj' needs a list, got rukx (text)`. |

#### Control, modules, process

| Verb | Objects | Result | Faults |
| --- | --- | --- | --- |
| `'iţpənn` | 0, or 1 when a value is written | The ability's result: that value, or void when no value was written. | Grammar fault outside an ability: `'iţpənn (return) used outside of an ability`. |
| `lups` | 0 | No result. Leaves the innermost `baxuφ` or `aχəw'` written in the same ability. | Grammar fault when no such loop contains it: `lups (stop) used outside of a loop`. |
| `ɢnagɮ` | 0 | No result. Skips to the next turn of the innermost `baxuφ` or `aχəw'` written in the same ability. | Grammar fault when no such loop contains it: `ɢnagɮ (next) used outside of a loop`. |
| `ɬšeɴazv` | 1: a | No result. Raises a program fault whose message is the host text of the object. Text is copied unchanged. A number is written in decimal digits, so the numeral `0a` produces the message `10`. A list is written in the host's list form, so the list of 1 and 2 produces `[1, 2]`. A `qit` handler receives the object itself as `dekp`. | A text bad: `bad`. The number ten: `10`. The list of 1 and 2: `[1, 2]`. |
| `qab'` | 1: code | No result. The process ends with that integer as its status and writes no fault. | When the object is not a number. A text: `'qab'' needs a number, got rukx (text)`. |
| `bukð` | 1: path | Void, after that file is run in this session. The search is [section 6](#6-modules-command-notes-on-disk). | When the path is not text. A number: `'bukð' (play/cast) wants a path as text, got asərθ (number)`. When no file is found: `bukð (play/cast): no such text 'nope-probe.phyx'`. When the file is found but cannot be read as UTF-8, the message continues with the host error: `bukð (play/cast) cannot read 'bad.phyx': 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`. A cycle through literal paths is a grammar fault: `bukð (play/cast): 'a.phyx' is already being cast (cycle)`. A cycle reached by a path computed at run time is a runtime fault with the same wording: `bukð (play/cast): 'c.phyx' is already being cast (cycle)`. |
| `čtəčpliɣn` | 2: args ability | Whatever that ability returns. `args` is a list of objects, one per parameter. | When the second object is not an ability. A number: `'čtəčpliɣn' (activate) wants an ability, got asərθ (number)`. When the first object is not a list. A number: `'čtəčpliɣn' wants a list of objects before the ability, got asərθ (number)`. When the list length differs from the parameter count, the message names the ability, how many objects it wants, and the length of the list. One parameter uses the singular word object; every other count uses objects. An ability add of two parameters given one object: `'add' wants 2 objects, this list has 1`. |
| `naķm` | 1: ability | The ability itself. Spoken, it is `naķm` joined to the ability's name. | When the object is not an ability. A number: `'naķm' (work) wants an ability, got asərθ (number)`. |
| `'uxq` | 0 | The list of argument texts given to the program. Empty when none were given. | none |
| `brøtjt` | 1: path | The UTF-8 text of that file. The search is [section 6](#6-modules-command-notes-on-disk). | When the path is not text. A number: `'brøtjt' (research) wants a path as text, got asərθ (number)`. When no file is found: `brøtjt (research) cannot read 'missing-probe.rukx'`. When the file is found but cannot be read as UTF-8, the message continues with the host error: `brøtjt (research) cannot read 'bad.phyx': 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`. |
| `mɴyrx` | 2: text path | The same text, after it is written as UTF-8 at that path. Missing parent directories are created. A relative path is resolved as in [section 6](#6-modules-command-notes-on-disk). | When either object is not text, the message names both kinds. Two numbers: `'mɴyrx' (spread) writes text onto a path, got asərθ (number) and asərθ (number)`. When the host cannot encode or write the file, the message continues with the host error: `mɴyrx (spread) cannot write 'out.rukx': 'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed`. |

## 6. Modules, command, notes on disk

- `bukð` path — run that `.phyx` / `.vphyx` in the current session. A cast cycle is a grammar fault for a literal path and a runtime fault for a path computed at run time, with the same wording. Cast before call.
- Resolution order: directory of the file that contains the `bukð`, working directory, each entry of `PHYX_PATH`, then the shipped library (`phyx/lib`). A name without a suffix is tried as `.phyx` then `.vphyx`. Absolute paths are used as written.
- A conforming implementation ships number and list herds (`asərθ`, `ťewn`, `compleat`) in that library. They are φyrx programs, not host primitives.
- `'uxq` — list of program arguments (text). Empty in the REPL.
- `brøtjt` path — read UTF-8 text. Relative names search: directory of the file that contains the verb, working directory, each entry of `PHYX_PATH`. The path is used as written (no suffix guessing). The shipped library is not searched. Absolute paths are used as written.
- `mɴyrx` text path — write UTF-8 text, yield the text. Missing parent directories are created. Relative names are resolved against the directory of the file that contains the verb (working directory in the REPL). This verb does not search. Absolute paths are used as written.

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
