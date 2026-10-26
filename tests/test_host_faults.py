"""Host faults that must stay Phyrexian: Ctrl-C, memory, and nesting."""

from __future__ import annotations

import contextlib
import io
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path

from phyx.cli import main

ROOT = Path(__file__).resolve().parent.parent
EQ = "\u01c6'ynpp"
# The print sits in the loop, so the first line of output means the body is running.
SPIN = f'^baxu\u03c6-1-1-{EQ}:\n    !"start".\n'
# Measured on 3.14 with the default recursion ceiling of 1000: nested ``ba``
# overflows the parser at 248, and a ``ťewn`` / ``babg`` chain overflows lint
# at 1000 and ``dis`` at 246. These sit above that, with room for 3.11–3.13.
# ``run`` compiles on a 16384 ceiling, so those commands lower PHYX_RECURSION
# to 1000 and the same sources overflow there too.
NEST_IFS = 300
NEST_CHAIN = 1500
RUN_RECURSION = "1000"
MEMORY = textwrap.dedent(
    """\
    ^"ab"-t-\u0163\u0259''.
    ^a\u03c7\u0259w'-i-dl-21-ron\u0263:
        ^t-t-babg-t-\u0163\u0259''.
    !t-samk.
    """
)
MEMORY_CAUGHT = textwrap.dedent(
    """\
    ^"ab"-t-\u0163\u0259''.
    ^baqilx:
        ^a\u03c7\u0259w'-i-dl-21-ron\u0263:
            ^t-t-babg-t-\u0163\u0259''.
    ^qit:
        !"caught".
    """
)


def _env(treewalk: bool | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PHYX_TREEWALK", None)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    if treewalk:
        env["PHYX_TREEWALK"] = "1"
    return env


def _cli(
    args: list[str],
    src: str | None = None,
    stdin: str | None = None,
    recursion: str | None = None,
):
    """Run one phyx command in this process.

    A fresh interpreter per command was most of the suite time. The command
    still goes through ``main``, so a traceback fails the test the same way.
    """
    previous_recursion = os.environ.get("PHYX_RECURSION")
    previous_tree = os.environ.get("PHYX_TREEWALK")
    os.environ.pop("PHYX_TREEWALK", None)
    if recursion is None:
        os.environ.pop("PHYX_RECURSION", None)
    else:
        os.environ["PHYX_RECURSION"] = recursion
    out, err = io.StringIO(), io.StringIO()
    old_in = sys.stdin
    try:
        with tempfile.TemporaryDirectory() as td:
            argv = list(args)
            if src is not None:
                path = Path(td) / "prog.phyx"
                path.write_text(src, encoding="utf-8", newline="\n")
                argv.append(str(path))
            if stdin is not None:
                sys.stdin = io.StringIO(stdin)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(argv)
    finally:
        sys.stdin = old_in
        if previous_recursion is None:
            os.environ.pop("PHYX_RECURSION", None)
        else:
            os.environ["PHYX_RECURSION"] = previous_recursion
        if previous_tree is None:
            os.environ.pop("PHYX_TREEWALK", None)
        else:
            os.environ["PHYX_TREEWALK"] = previous_tree
    return subprocess.CompletedProcess(argv, code, out.getvalue(), err.getvalue())


class InterruptTests(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "SIGINT delivery differs on Windows")
    def test_sigint_stops_both_engines(self):
        for treewalk in (False, True):
            with self.subTest(treewalk=treewalk):
                proc = subprocess.Popen(
                    [sys.executable, "-m", "phyx", "-c", SPIN],
                    cwd=ROOT,
                    env=_env(treewalk),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                try:
                    if not _signal_on_line(proc, b"start"):
                        proc.kill()
                        self.fail("program did not print start")
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    out, err = proc.communicate()
                    self.fail(f"still running after SIGINT\n{out!r}\n{err!r}")
                text = out.decode("utf-8", "replace") + err.decode("utf-8", "replace")
                self.assertEqual(proc.returncode, 130, text)
                self.assertIn("stopped", text)
                self.assertNotIn("Traceback", text)

    @unittest.skipIf(sys.platform == "win32", "SIGINT delivery differs on Windows")
    def test_repl_survives_sigint_and_keeps_going(self):
        proc = subprocess.Popen(
            [sys.executable, "-m", "phyx", "repl"],
            cwd=ROOT,
            env=_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write((SPIN + "\n").encode())
            proc.stdin.flush()
            if not _signal_on_line(proc, b"start"):
                proc.kill()
                self.fail("repl did not print start")
            proc.stdin.write(b'!"after".\n.quit\n')
            proc.stdin.flush()
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            self.fail(f"repl did not return after SIGINT\n{out!r}\n{err!r}")
        text = out.decode("utf-8", "replace") + err.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 0, text)
        self.assertIn("after", text)
        self.assertNotIn("Traceback", text)

    def test_join_interrupt_stops_the_worker(self):
        import ctypes

        from phyx.limits import call_on_stack

        finished = threading.Event()
        main_id = threading.get_ident()

        def spin() -> None:
            try:
                while True:
                    # An empty ``pass`` loop does not take an async exception
                    # on Python 3.11 or 3.12. A short sleep does, on 3.11–3.13.
                    time.sleep(0.001)
            finally:
                finished.set()

        def poke() -> None:
            time.sleep(0.3)
            api = ctypes.pythonapi.PyThreadState_SetAsyncExc
            api.argtypes = (ctypes.c_ulong, ctypes.py_object)
            api.restype = ctypes.c_int
            api(ctypes.c_ulong(main_id), ctypes.py_object(KeyboardInterrupt))

        threading.Thread(target=poke, daemon=True).start()
        with self.assertRaises(KeyboardInterrupt):
            call_on_stack(spin)
        self.assertTrue(finished.wait(2), "the worker was still running")

    @unittest.skipIf(sys.platform == "win32", "SIGINT delivery differs on Windows")
    def test_real_sigint_stops_the_ticking_worker(self):
        """A real SIGINT must stop the worker, not only the waiting thread.

        On Python 3.11 and 3.12 ``Thread.is_alive`` is false right after
        ``join`` is interrupted, while the worker is still running. Skipping
        the inject in that case leaves the worker ticking behind the caller.
        """
        from phyx.limits import call_on_stack

        ticks = {"n": 0}

        def spin() -> None:
            while True:
                ticks["n"] += 1
                time.sleep(0.001)

        timer = threading.Timer(0.3, lambda: os.kill(os.getpid(), signal.SIGINT))
        timer.daemon = True
        timer.start()
        try:
            with self.assertRaises(KeyboardInterrupt):
                call_on_stack(spin)
            self.assertGreater(ticks["n"], 0)
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                seen = ticks["n"]
                time.sleep(0.05)
                if ticks["n"] == seen:
                    break
            else:
                self.fail(f"counter still increasing ({ticks['n']})")
            names = [thread.name for thread in threading.enumerate()]
            self.assertNotIn("phyx", names)
        finally:
            timer.cancel()


RLIMIT_AS_SKIP = "RLIMIT_AS is only enforced on Linux (macOS refuses to set it, Windows has no resource module)"


def _rlimit_as_enforced() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    try:
        import resource
    except ImportError:
        return False
    return hasattr(resource, "RLIMIT_AS")


class MemoryTests(unittest.TestCase):
    @unittest.skipUnless(_rlimit_as_enforced(), RLIMIT_AS_SKIP)
    def test_out_of_memory_is_a_fault_on_both_engines(self):
        child = textwrap.dedent(
            """\
            import resource, sys
            cap = 256 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
            if sys.argv[1] == "1":
                import os
                os.environ["PHYX_TREEWALK"] = "1"
            from phyx.cli import main
            raise SystemExit(main(["-c", sys.argv[2]]))
            """
        )
        for flag in ("0", "1"):
            with self.subTest(treewalk=flag):
                proc = subprocess.run(
                    [sys.executable, "-c", child, flag, MEMORY],
                    cwd=ROOT,
                    env=_env(),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                text = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 1, text)
                self.assertIn("the program ran out of memory", text)
                self.assertIn("[runtime]", text)
                self.assertIn("line 3", text)
                self.assertIn("text", text)
                self.assertIn("list", text)
                self.assertIn("number", text)
                self.assertNotIn("Traceback", text)
                self.assertNotIn("MemoryError", text)

    @unittest.skipUnless(_rlimit_as_enforced(), RLIMIT_AS_SKIP)
    def test_handler_can_catch_out_of_memory(self):
        child = textwrap.dedent(
            """\
            import resource, sys
            cap = 256 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
            if sys.argv[1] == "1":
                import os
                os.environ["PHYX_TREEWALK"] = "1"
            from phyx.cli import main
            raise SystemExit(main(["-c", sys.argv[2]]))
            """
        )
        for flag in ("0", "1"):
            with self.subTest(treewalk=flag):
                proc = subprocess.run(
                    [sys.executable, "-c", child, flag, MEMORY_CAUGHT],
                    cwd=ROOT,
                    env=_env(),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                )
                text = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 0, text)
                self.assertIn("caught", text)
                self.assertNotIn("Traceback", text)


def _signal_on_line(proc: subprocess.Popen, needle: bytes) -> bool:
    """Send SIGINT as soon as ``needle`` shows up on the child's stdout."""
    assert proc.stdout is not None
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if needle in proc.stdout.readline():
            proc.send_signal(signal.SIGINT)
            return True
    return False


def _nested_ifs(n: int) -> str:
    src = "\n".join("    " * i + f"^ba-1-1-{EQ}:" for i in range(n))
    return src + "\n" + "    " * n + "!1.\n"


def _nested_lists(n: int) -> str:
    return "!1-" + "1-\u0165ewn-" * n + "samk.\n"


def _nested_adds(n: int) -> str:
    return "!1-" + "1-babg-" * n + "0-babg.\n"


class NestingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ifs = _nested_ifs(NEST_IFS)
        cls.lists = _nested_lists(NEST_CHAIN)
        cls.adds = _nested_adds(NEST_CHAIN)

    def test_deep_source_is_a_grammar_fault(self):
        cases = {
            "ifs": (self.ifs, ("run", "check", "lint", "dis")),
            "lists": (self.lists, ("run", "lint", "dis")),
            "adds": (self.adds, ("run", "lint", "dis")),
        }
        for name, (src, commands) in cases.items():
            for command in commands:
                with self.subTest(name=name, command=command):
                    recursion = RUN_RECURSION if command == "run" and name != "ifs" else None
                    proc = _cli([command], src, recursion=recursion)
                    text = proc.stdout + proc.stderr
                    self.assertEqual(proc.returncode, 1, text)
                    self.assertIn("[grammar]", text)
                    self.assertIn("this program is nested too deeply", text)
                    self.assertIn("line 1", text)
                    self.assertNotIn("Traceback", text)
            with self.subTest(name=name, command="repl"):
                recursion = None if name == "ifs" else RUN_RECURSION
                proc = _cli(
                    ["repl"],
                    stdin=src + '\n!"ok".\n.quit\n',
                    recursion=recursion,
                )
                text = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 0, text)
                self.assertIn("[grammar]", text)
                self.assertIn("this program is nested too deeply", text)
                self.assertIn("ok", text)
                self.assertNotIn("Traceback", text)

    def test_flat_commands_do_not_traceback(self):
        for src in (self.lists, self.adds):
            for command in ("check", "fmt"):
                with self.subTest(command=command):
                    proc = _cli([command], src)
                    text = proc.stdout + proc.stderr
                    self.assertNotIn("Traceback", text)
                    self.assertEqual(proc.returncode, 0, text)
        proc = _cli(["fmt"], self.ifs)
        self.assertNotIn("Traceback", proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_deep_value_is_a_runtime_fault(self):
        from tests.test_engine_parity import assertParity, run_both

        source = (
            "^1-1-\u0165ewn-xs-\u0163\u0259''.\n"
            "^a\u03c7\u0259w'-i-dl-5000-ron\u0263:\n"
            "    ^xs-1-\u0165ewn-xs-\u0163\u0259''.\n"
            "!xs.\n"
        )
        compiled, walked = run_both(source)
        for result in (compiled, walked):
            self.assertEqual(
                result[1],
                ("RuntimeFault", "this value is nested too deeply", 4, "a list or book this deep cannot be shown or compared"),
                result,
            )
        assertParity(source)
        equal = source.replace("!xs.", f"!xs-xs-{EQ}.")
        compiled, walked = run_both(equal)
        for result in (compiled, walked):
            self.assertEqual(result[1][0], "RuntimeFault", result)
            self.assertEqual(result[1][1], "this value is nested too deeply", result)
        assertParity(equal)


if __name__ == "__main__":
    unittest.main()
