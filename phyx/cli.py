"""Command line interface for φyrx (PhyrxScript / PhyrexianScript).

``python -m phyx <command> …``, or ``phyx`` / ``phyrx`` / ``phyrxscript`` /
``phyrexianscript`` once installed.  A path with no subcommand is a program::

    phyx examples/01_welcome.phyx
    phyx run examples/10_command.phyx red blue
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Iterable

from . import LANGUAGE, LANGUAGE_ALIASES, __version__
from .errors import PhyrexianError, format_error
from .compiler import compile_to_python
from .interpreter import Interpreter, run_source
from .values import format_number
from .lexer import transliterate, untransliterate
from .parser import parse
from .fonts import (
    FONT_FAMILY,
    ensure_basilica,
    ensure_font,
    install_user_font,
    is_font_file,
    local_font,
)
from .render import render_html
from .repl import Repl
from .vertical import from_vertical, to_vertical
from .fmt import format_source
from .hints import explain_missing, explain_word, search_lexicon
from .lint import format_notes, lint_program
from .paths import stdlib_dir
from .scaffold import create as create_scaffold
from .testing import run_suite
from .vocabulary import CONSTANTS, MARKERS, VERBS
from .lsp import serve as serve_lsp
from . import ast as phyx_ast

SUBCOMMANDS = {
    "run", "check", "render", "transpose", "translit",
    "fetch", "lookup", "words", "repl", "eval", "bench", "dis",
    "explain", "fmt", "lint", "test", "lib", "new", "lsp",
}

DICT_REMOTE = "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/gh-pages/_data/PhyrexianAPI.json"
VERTICAL_EXT = ".vphyx"


def assets_dir() -> Path:
    env = os.environ.get("PHYX_ASSETS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "assets"


def local_dictionary() -> Path:
    return assets_dir() / "dictionary.json"


def _utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            try:
                stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            except Exception:
                pass


def load_source(path: str, ascii_mode: bool, vertical: bool | None) -> str:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if vertical is None:
        vertical = p.suffix == VERTICAL_EXT
    if vertical:
        text = from_vertical(text)
    if ascii_mode:
        text = transliterate(text)
    return text


def _exit_code(err: SystemExit) -> int:
    code = err.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


def _run_program(source: str, root: Path, ascii_mode: bool, argv: list[str]) -> int:
    try:
        program = parse(source, base_dir=root)
        Interpreter(
            base_dir=root,
            ascii_mode=ascii_mode,
            argv=argv,
        ).run(program)
    except PhyrexianError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
    except SystemExit as err:
        return _exit_code(err)
    return 0


# ----------------------------------------------------------------- commands
def cmd_run(args: argparse.Namespace) -> int:
    source = load_source(args.file, args.ascii, args.vertical)
    root = Path(args.file).resolve().parent
    return _run_program(source, root, bool(args.ascii), list(args.script_args or []))


def cmd_eval(args: argparse.Namespace) -> int:
    source = args.code
    if args.ascii:
        source = transliterate(source)
    return _run_program(source, Path.cwd(), bool(args.ascii), list(args.script_args or []))


def cmd_check(args: argparse.Namespace) -> int:
    source = load_source(args.file, args.ascii, args.vertical)
    try:
        program = parse(source, base_dir=Path(args.file).resolve().parent)
    except PhyrexianError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
    print(f"{args.file}: {len(program)} top-level sentence{'s' if len(program) != 1 else ''}, grammar is sound")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    unknown = 0
    for word in args.words:
        text = explain_word(word)
        if text is None:
            print(explain_missing(word), file=sys.stderr)
            unknown += 1
        else:
            print(text)
            print()
    return 1 if unknown else 0


def cmd_fmt(args: argparse.Namespace) -> int:
    source = Path(args.file).read_text(encoding="utf-8")
    try:
        formatted = format_source(source)
    except PhyrexianError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
    if args.in_place:
        Path(args.file).write_text(formatted, encoding="utf-8")
        if formatted != source:
            print(f"rewrote {args.file}")
        return 0
    if args.output:
        Path(args.output).write_text(formatted, encoding="utf-8")
        print(f"wrote {args.output}")
        return 0
    sys.stdout.write(formatted)
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    source = load_source(args.file, args.ascii, args.vertical)
    try:
        program = parse(source, base_dir=Path(args.file).resolve().parent)
    except PhyrexianError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
    notes = lint_program(program)
    if not notes:
        print(f"{args.file}: no notes")
        return 0
    print(format_notes(notes, args.file))
    return 1


def cmd_dis(args: argparse.Namespace) -> int:
    source = load_source(args.file, args.ascii, args.vertical)
    try:
        program = parse(source, base_dir=Path(args.file).resolve().parent)
        sys.stdout.write(compile_to_python(program))
    except PhyrexianError as err:
        print(format_error(err, source), file=sys.stderr)
        return 1
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    source = load_source(args.file, args.ascii, args.vertical)
    title = args.title or Path(args.file).name
    try:
        font = ensure_font()
    except OSError as err:
        font = local_font()
        print(f"warning: could not fetch Phyrexian Regular ({err})", file=sys.stderr)
    page = render_html(source, title=title, local_font=font, size=args.size)
    out = Path(args.output) if args.output else Path(args.file).with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    note = (
        f"embedded {FONT_FAMILY}"
        if is_font_file(font)
        else "font loaded from the Phyrexian Dictionary CDN"
    )
    print(f"wrote {out} ({note})")
    return 0


def cmd_transpose(args: argparse.Namespace) -> int:
    p = Path(args.file)
    text = p.read_text(encoding="utf-8")
    to_vert = args.to_vertical or (not args.to_horizontal and p.suffix != VERTICAL_EXT)
    result = to_vertical(text, gap=args.gap) if to_vert else from_vertical(text, gap=args.gap)
    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(result)
    return 0


def cmd_translit(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8")
    result = untransliterate(text) if args.reverse else transliterate(text)
    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(result)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    print("fetching Phyrexian Regular (official card font, family name: Phyrexian)")
    font = ensure_font()
    print(f"  -> {font}")
    print("fetching Basilica (native hexadecimal glyphs)")
    basilica = ensure_basilica()
    print(f"  -> {basilica}")
    dest = local_dictionary()
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetching {DICT_REMOTE}")
    req = urllib.request.Request(DICT_REMOTE, headers={"User-Agent": "phyx-font-fetch"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https URLs
        dest.write_bytes(resp.read())
    print(f"  -> {dest}")
    for path, family in ((font, FONT_FAMILY), (basilica, "Basilica")):
        installed = install_user_font(path, family)
        if installed:
            print(f"installed {family} for this user: {installed}")
    print("done. Phyrexian Regular is GPL-3.0 (Wizards / dictionary repo); Basilica is CC-BY.")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Time compiled abilities against the same Python (parse/compile once)."""
    import time

    n = max(8, int(args.size))
    loops = max(1000, int(args.loops))
    hex_n = format_number(n)
    hex_loops = format_number(loops)
    fib_src = (
        "^ťe-n-fib:\n"
        "    ^ba-n-ķu-grmɒɣg:lo-n-'iţpənn.\n"
        "    ^lo-n-'ii-mɒɣg-fib-n-ķu-mɒɣg-fib-babg-'iţpənn.\n"
        f"!{hex_n}-fib.\n"
    )
    loop_src = (
        "^ťe-k-sum:\n"
        "    ^xe-0-s-ţə''.\n"
        "    ^xe-0-i-ţə''.\n"
        "    ^baxuφ-i-k-grmɒɣg:\n"
        "        ^xe-s-i-babg-s-ţə''.\n"
        "        ^xe-i-1-babg-i-ţə''.\n"
        "    ^lo-s-'iţpənn.\n"
        f"!{hex_loops}-sum.\n"
    )

    def py_fib(k):
        if k < 2:
            return k
        return py_fib(k - 1) + py_fib(k - 2)

    def py_loop(k):
        s = i = 0
        while i < k:
            s += i
            i += 1
        return s

    def best(fn, repeats=4):
        fn()
        t = 1e9
        for _ in range(repeats):
            t0 = time.perf_counter()
            fn()
            t = min(t, time.perf_counter() - t0)
        return t

    def load_ability(src, name):
        # bench measures the compiled engine even when PHYX_TREEWALK=1.
        interp = Interpreter(stdout=io.StringIO(), treewalk=False)
        interp.run(parse(src))
        ability = interp.globals.vars[name]
        return interp, ability.impl

    fib_rt, fib_impl = load_ability(fib_src, "fib")
    sum_rt, sum_impl = load_ability(loop_src, "sum")

    pf = best(lambda: py_fib(n))
    cf = best(lambda: fib_impl(fib_rt, n))
    pl = best(lambda: py_loop(loops))
    cl = best(lambda: sum_impl(sum_rt, loops))
    print(f"φyrx {__version__}  (compiles to CPython; timed after compile)")
    print(f"fib({n})   python {pf*1000:7.2f} ms   φyrx {cf*1000:7.2f} ms   {cf/pf:4.1f}×")
    print(f"loop {loops} python {pl*1000:7.2f} ms   φyrx {cl*1000:7.2f} ms   {cl/pl:4.1f}×")
    print("bench always times the compiled engine.")
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    lex_hits: list[tuple[str, str, str, str]] = []
    for query in args.words:
        lex_hits.extend(search_lexicon(query))

    dict_hits: list[dict] = []
    path = local_dictionary()
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = list(data["dictionary"].values())
        for query in args.words:
            q = query.lower()
            q_phy = transliterate(query)
            for e in entries:
                phy = e.get("phyrexian") or ""
                tr = (e.get("translation") or "").lower()
                if q in tr or q in phy or q_phy in phy:
                    dict_hits.append(e)

    if not lex_hits and not dict_hits:
        print("nothing found")
        return 1

    seen_lex: set[tuple[str, str]] = set()
    for word, gloss, kind, extra in lex_hits:
        key = (word, kind)
        if key in seen_lex:
            continue
        seen_lex.add(key)
        print(f"{word:<18} {gloss:<28} {kind:<14} {extra}")

    if dict_hits:
        if lex_hits:
            print()
            print("dictionary")
        seen_dict: set[tuple[str, str]] = set()
        for e in dict_hits:
            key = (e["phyrexian"], e["translation"])
            if key in seen_dict:
                continue
            seen_dict.add(key)
            plural = e.get("plural")
            plural_s = "" if plural in (None, "FALSE") else f"  pl. {plural}"
            print(
                f"{e['phyrexian']:<18} {e['translation']:<28} {e.get('class') or '':<14} "
                f"{e.get('type') or '':<10} {e.get('confidence') or ''}{plural_s}"
            )
    return 0


def cmd_repl(args: argparse.Namespace) -> int:
    ascii_mode = bool(getattr(args, "ascii", False))
    return Repl(ascii_mode=ascii_mode).run()


def cmd_words(args: argparse.Namespace) -> int:
    print("MOOD MARKERS (first word of a phrase)")
    for w, (kind, gloss) in MARKERS.items():
        print(f"  {w:<10} {kind:<8} {gloss}")
    print("\nVERBS (objects first, verb last)")
    for v in VERBS.values():
        ar = "N…" if v.arity == -1 else str(v.arity)
        print(f"  {v.word:<16} {ar:<3} {v.gloss:<14} {v.doc}")
    print("\nCONSTANTS")
    for w, val in CONSTANTS.items():
        print(f"  {w:<10} {val!r}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    paths = list(args.paths) if getattr(args, "paths", None) else ["tests"]
    roots = [Path(p) for p in paths]
    if not any(r.exists() for r in roots):
        roots = [Path(".")]
    return run_suite(roots, ascii_mode=bool(getattr(args, "ascii", False)))


def _walk_stmts(stmts: list) -> Iterable:
    for stmt in stmts:
        yield stmt
        body = getattr(stmt, "body", None)
        if body:
            yield from _walk_stmts(body)
        orelse = getattr(stmt, "orelse", None)
        if orelse:
            yield from _walk_stmts(orelse)
        handler = getattr(stmt, "handler", None)
        if handler:
            yield from _walk_stmts(handler)


def cmd_new(args: argparse.Namespace) -> int:
    folder = Path(args.directory) if getattr(args, "directory", None) else Path.cwd()
    program, test = create_scaffold(
        args.name,
        ascii_mode=bool(getattr(args, "ascii", False)),
        directory=folder,
    )
    print(program)
    print(test)
    return 0


def cmd_lsp(args: argparse.Namespace) -> int:
    _ = args
    return serve_lsp()


def cmd_lib(args: argparse.Namespace) -> int:
    folder = stdlib_dir()
    print(f"standard library: {folder}")
    print("bukð looks in: the file's directory, the working directory, PHYX_PATH, then here.")
    print('A name without a suffix is tried as .phyx then .vphyx:  ^lo-"asərθ"-bukð.')
    if not folder.is_dir():
        print("no phyx/lib directory in this install", file=sys.stderr)
        return 1
    for path in sorted(folder.glob("*.phyx")):
        program = parse(path.read_text(encoding="utf-8"), base_dir=path.parent)
        defs: list[str] = []
        casts: list[str] = []
        for stmt in _walk_stmts(program):
            if isinstance(stmt, phyx_ast.FuncDef):
                defs.append(f"{stmt.name}/{len(stmt.params)}")
            exprs = getattr(stmt, "exprs", None) or []
            for expr in exprs:
                if (
                    isinstance(expr, phyx_ast.Call)
                    and expr.verb.word == "bukð"
                    and expr.args
                    and isinstance(expr.args[0], phyx_ast.Literal)
                ):
                    casts.append(str(expr.args[0].value))
        print(f"\n  {path.name}")
        if casts:
            print(f"    casts {', '.join(casts)}")
        for name in defs:
            print(f"    {name}")
        if not defs and not casts:
            print("    (empty)")
    return 0


# ----------------------------------------------------------------- main
def normalize_argv(argv: list[str]) -> list[str]:
    """``phyx FILE`` runs a program; ``phyx -c CODE`` evaluates a string."""
    if not argv:
        return ["repl"]
    if argv[0] in ("-h", "--help", "-V", "--version"):
        return argv
    if argv[0] == "-c":
        return ["eval", *argv[1:]]
    if argv[0] == "--ascii":
        rest = argv[1:]
        if not rest:
            return ["repl", "--ascii"]
        if rest[0] == "-c":
            return ["eval", "--ascii", *rest[1:]]
        if rest[0] in SUBCOMMANDS:
            return [rest[0], "--ascii", *rest[1:]]
        return ["run", "--ascii", *rest]
    if argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        return ["run", *argv]
    return argv


def build_parser() -> argparse.ArgumentParser:
    also = " / ".join(LANGUAGE_ALIASES)
    prog = Path(sys.argv[0]).stem or "phyx"
    ap = argparse.ArgumentParser(
        prog=prog,
        description=f"{LANGUAGE} ({also}) — a programming language written in Phyrexian.",
    )
    ap.add_argument(
        "-V", "--version",
        action="version",
        version=f"{LANGUAGE} {__version__} ({also})",
    )
    sub = ap.add_subparsers(dest="command")

    def source_opts(p: argparse.ArgumentParser) -> None:
        p.add_argument("file", help="program file (.phyx, or .vphyx for vertical layout)")
        p.add_argument("--ascii", action="store_true",
                       help="source uses ASCII capitals for special letters (see `translit`)")
        grp = p.add_mutually_exclusive_group()
        grp.add_argument("--vertical", dest="vertical", action="store_true", default=None,
                         help="source is laid out vertically (columns)")
        grp.add_argument("--horizontal", dest="vertical", action="store_false",
                         help="source is laid out as text rows (default for .phyx)")

    p = sub.add_parser("run", help="run a program")
    source_opts(p)
    p.add_argument("script_args", nargs="*", metavar="ARG",
                   help="bound to the verb 'uxq (command) inside the program")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("eval", help="run a program from a string (also: phyx -c CODE)")
    p.add_argument("--ascii", action="store_true",
                   help="source uses ASCII capitals for special letters")
    p.add_argument("code", help="complete φyrx sentences")
    p.add_argument("script_args", nargs="*", metavar="ARG",
                   help="bound to 'uxq")
    p.set_defaults(fn=cmd_eval)

    p = sub.add_parser("check", help="parse a program without running it")
    source_opts(p)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("dis", help="print the CPython a φyrx program compiles to")
    source_opts(p)
    p.set_defaults(fn=cmd_dis)

    p = sub.add_parser("explain", help="describe a marker, verb, constant, or English word")
    p.add_argument("words", nargs="+")
    p.set_defaults(fn=cmd_explain)

    p = sub.add_parser("fmt", help="rewrite a program with canonical separators and 4-space indent")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("-i", "--in-place", action="store_true")
    p.set_defaults(fn=cmd_fmt)

    p = sub.add_parser("lint", help="name traps (dropped return, unused objects, English words)")
    source_opts(p)
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("render", help="render a program as vertical Phyrexian script (HTML)")
    source_opts(p)
    p.add_argument("-o", "--output", help="output .html (default: next to the source)")
    p.add_argument("--title", help="page title")
    p.add_argument("--size", type=int, default=34, help="glyph size in px (default 34)")
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("transpose", help="convert between row layout (.phyx) and column layout (.vphyx)")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("--gap", type=int, default=1, help="blank columns between lines (default 1)")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--to-vertical", action="store_true")
    grp.add_argument("--to-horizontal", action="store_true")
    p.set_defaults(fn=cmd_transpose)

    p = sub.add_parser("translit", help="ASCII capitals -> Phyrexian letters (or back with --reverse)")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    p.add_argument("--reverse", action="store_true")
    p.set_defaults(fn=cmd_translit)

    p = sub.add_parser(
        "fetch",
        help="download Phyrexian Regular + Basilica + dictionary (installs the font for this user on Windows)",
    )
    p.set_defaults(fn=cmd_fetch)

    p = sub.add_parser("lookup", help="search the lexicon (and the fetched dictionary if present)")
    p.add_argument("words", nargs="+")
    p.set_defaults(fn=cmd_lookup)

    p = sub.add_parser("words", help="list the markers, verbs and constants of the language")
    p.set_defaults(fn=cmd_words)

    p = sub.add_parser("bench", help="time φyrx against the same algorithm in Python")
    p.add_argument("--size", type=int, default=16, help="fibonacci argument (decimal, default 16)")
    p.add_argument("--loops", type=int, default=20000, help="tight-loop iterations (default 20000)")
    p.set_defaults(fn=cmd_bench)

    p = sub.add_parser("repl", help="interactive session (default when no command is given)")
    p.add_argument("--ascii", action="store_true",
                   help="type special letters as ASCII capitals")
    p.set_defaults(fn=cmd_repl)

    p = sub.add_parser("test", help="run φyrx tests (test_*.phyx; ǩaπa and optional .expected)")
    p.add_argument("paths", nargs="*", help="files or directories (default: tests/)")
    p.add_argument("--ascii", action="store_true",
                   help="source uses ASCII capitals for special letters")
    p.set_defaults(fn=cmd_test)

    p = sub.add_parser("lib", help="list the shipped standard herds")
    p.set_defaults(fn=cmd_lib)

    p = sub.add_parser("new", help="write NAME.phyx and a sibling test_NAME.phyx")
    p.add_argument("name", help="ability and file name (letters, digits, underscore)")
    p.add_argument("-d", "--directory", help="folder to write into (default: current directory)")
    p.add_argument("--ascii", action="store_true",
                   help="write ASCII capitals for special letters")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("lsp", help="language server (stdin/stdout JSON-RPC)")
    p.set_defaults(fn=cmd_lsp)
    return ap


def main(argv: list[str] | None = None) -> int:
    _utf8_streams()
    if argv is None:
        argv = sys.argv[1:]
    argv = normalize_argv(list(argv))
    try:
        args = build_parser().parse_args(argv)
        if getattr(args, "command", None) is None:
            return cmd_repl(argparse.Namespace(ascii=False))
        return args.fn(args)
    except PhyrexianError as err:
        print(str(err), file=sys.stderr)
        return 1
    except FileNotFoundError as err:
        print(f"ɬšeɴazv: no such file: {err.filename}", file=sys.stderr)
        return 1
    except FileExistsError as err:
        print(f"ɬšeɴazv: already exists: {err.filename or err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"ɬšeɴazv: {err}", file=sys.stderr)
        return 1
    except ValueError as err:
        print(f"ɬšeɴazv: {err}", file=sys.stderr)
        return 1
    except SystemExit as err:
        return _exit_code(err)
    except KeyboardInterrupt:
        print("\nɬšeɴazv: stopped", file=sys.stderr)
        return 130
