"""Interactive session: write Phyrexian sentence by sentence.

A lone sentence that ends with ``.`` runs immediately.  A sentence that
opens a body with ``:`` keeps reading until a blank line (or a later
sentence that returns to column zero).  Abilities defined with ``ťe``
stay in the session, so you can call them in later sentences.

Dot-commands::

    .help     this text
    .words    list markers, verbs and constants
    .explain  describe one word (Phyrexian or English)
    .names    names currently bound in the session
    .load     cast (include) a .phyx file into the session
    .ascii    toggle ASCII-capital spelling
    .quit     leave
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from typing import IO

from .errors import PhyrexianError, format_error
from .hints import explain_missing, explain_word
from .interpreter import Interpreter
from .parser import parse
from .values import Ability, to_source
from .vocabulary import CONSTANTS, MARKERS, VERBS

BANNER = """φyrx (PhyrxScript / PhyrexianScript) — a programming language written in Phyrexian.
Sentences start with ^  !  ?  and end with .    Bodies follow :
Objects come first, the verb last.  Numbers are hexadecimal.
.help  .words  .explain  .names  .load  .ascii  .quit
"""

HELP = """A sentence is one thought.  Begin it with a start symbol:

  ^xe-5-x-ţə''.          put 5 into x          (indicative)
  !x.                    speak x               (exclamation)
  ?"name: "-nɒqč.        ask, store in nɒqč    (question)

The first word after ^ is a mood/tense marker from the dictionary:

  xe     it is so          ba / qit     if / instead
  'u     it already is     baxuφ        whenever (while)
  ťe     it can            aχəw'        each
  lo     do it             ǩaπa         it must

Objects precede the verb (Phyrexian SOV). Numbers are hexadecimal.
Lists: items, then the count, then ťewn  (empty: 0-ťewn)::

  ^xe-1-2-babg-x-ţə''.   1 2 add, put into x
  ^xe-1-2-3-3-ťewn-xs-ţə''.

A body after : is indented, or written on the same line::

  ^ba-x-0-korxgr:
      !x.
  ^qit:!"void".

Include another file with  ^lo-"path.phyx"-bukð.  or  .load path.phyx
Quote an ability (the work, not a call):  name-naķm
Call a stored ability:     args-list  ability  čtəčpliɣn
Program arguments:         'uxq   (empty in this session)

Dot-commands:  .help  .words  .explain  .names  .load  .ascii  .quit
End a multi-line body with a blank line.
"""


def is_complete(source: str) -> bool:
    """True when ``source`` is ready to parse as a program chunk.

    A trailing blank line always commits.  Otherwise a chunk is complete
    when its last real sentence sits at column zero and ends with ``.``.
    """
    raw = source.replace("\r\n", "\n").replace("\r", "\n")
    if raw.endswith("\n\n") or raw == "\n":
        return True
    lines = raw.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    meaningful = [ln for ln in lines if ln.strip() and not _is_comment(ln)]
    if not meaningful:
        return False
    last = meaningful[-1]
    indent = len(last) - len(last.lstrip(" \t"))
    stripped = last.rstrip()
    if stripped.endswith(":"):
        return False
    if indent > 0:
        return False
    return stripped.endswith(".")


def _is_comment(line: str) -> bool:
    s = line.lstrip(" \t")
    return s.startswith("^rukx") or s.startswith("^ rukx")


class Repl:
    def __init__(
        self,
        stdin: IO[str] | None = None,
        stdout: IO[str] | None = None,
        ascii_mode: bool = False,
        intro: bool = True,
    ):
        self.inp = stdin if stdin is not None else sys.stdin
        self.out = stdout if stdout is not None else sys.stdout
        self.ascii_mode = ascii_mode
        self.intro = intro
        self.done = False
        self.interp = Interpreter(
            stdout=self.out, stdin=self.inp, ascii_mode=ascii_mode, persistent=True
        )

    def write(self, text: str) -> None:
        self.out.write(text)

    def run(self, lines: Iterable[str] | None = None) -> int:
        if self.intro:
            self.write(BANNER)
            if self.ascii_mode:
                self.write("(ASCII spelling is on — capitals stand for special letters.)\n")
        iterator = iter(lines) if lines is not None else None
        buf: list[str] = []
        while True:
            prompt = "φyrx> " if not buf else "  ...> "
            try:
                if iterator is None:
                    self.write(prompt)
                    try:
                        self.out.flush()
                    except Exception:  # pragma: no cover
                        pass
                    line = self.inp.readline()
                    if line == "":
                        self.write("\n")
                        return 0
                    line = line.rstrip("\n\r")
                else:
                    try:
                        line = next(iterator)
                    except StopIteration:
                        if buf:
                            self._flush(buf)
                        return 0
            except KeyboardInterrupt:
                self.write("\n")
                buf = []
                continue
            if not buf and self._command(line.strip()):
                if self.done:
                    return 0
                continue
            buf.append(line)
            text = "\n".join(buf) + "\n"
            if not is_complete(text):
                continue
            self._flush(buf)
            buf = []

    def _command(self, line: str) -> bool:
        if not line.startswith("."):
            return False
        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()
        if cmd in (".quit", ".q", ".exit"):
            self.done = True
            return True
        if cmd in (".help", ".h", ".?"):
            self.write(HELP)
            return True
        if cmd == ".words":
            self.write("markers: " + " ".join(MARKERS) + "\n")
            self.write("verbs:   " + " ".join(VERBS) + "\n")
            self.write("const:   " + " ".join(CONSTANTS) + "\n")
            return True
        if cmd == ".explain":
            word = rest.strip()
            if not word:
                self.write(".explain needs a word, e.g. .explain babg  or  .explain if\n")
                return True
            text = explain_word(word)
            self.write((text if text is not None else explain_missing(word)) + "\n")
            return True
        if cmd == ".names":
            names = [
                f"{k}/{len(v.params)}" if isinstance(v, Ability) else f"{k}={to_source(v)}"
                for k, v in self.interp.globals.vars.items()
            ]
            self.write(("  ".join(names) if names else "(none)") + "\n")
            return True
        if cmd == ".load":
            path = rest.strip().strip('"').strip("'")
            if not path:
                self.write(".load needs a path, e.g. .load examples/01_welcome.phyx\n")
                return True
            try:
                self.interp.include(path)
            except PhyrexianError as err:
                self.write(format_error(err) + "\n")
            return True
        if cmd == ".ascii":
            self.ascii_mode = not self.ascii_mode
            self.interp.ascii_mode = self.ascii_mode
            self.write("ASCII spelling is " + ("on" if self.ascii_mode else "off") + ".\n")
            return True
        self.write(f"unknown command {cmd!r} — try .help\n")
        _ = rest
        return True

    def _flush(self, buf: list[str]) -> None:
        text = "\n".join(buf).strip("\n")
        if not text.strip() or all(_is_comment(ln) or not ln.strip() for ln in buf):
            return
        try:
            program = parse(
                text,
                ascii_mode=self.ascii_mode,
                known_functions=self.interp.known_functions(),
                base_dir=self.interp.base_dir,
            )
            self.interp.run(program)
        except KeyboardInterrupt:
            self.write("\n")
        except PhyrexianError as err:
            self.write(format_error(err, text) + "\n")
        except SystemExit:
            raise
        except Exception as err:  # pragma: no cover - last-resort fence
            self.write(f"ɬšeɴazv: {err}\n")
