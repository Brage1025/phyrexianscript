"""Host recursion budget and the maximum size of a repeated text, list, or ``ronɣ``.

Programs run on a thread whose stack is 64 MiB. ``PHYX_RECURSION`` is how
many host frames that thread may use. The default, 16384, is enough for a
compiled ability about 8000 calls deep. It is also the highest value the
stack can hold at 4 KiB a frame, so the ceiling is not the largest number
the machine would accept.
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
from collections.abc import Callable

from .errors import RuntimeFault

# Host frames. A compiled ability call is one frame. The tree-walker uses
# several, so the same ceiling is a shallower ability there.
DEFAULT_RECURSION = 16_384
MIN_RECURSION = 64

# Fixed stack for the program thread. Windows refuses 256 MiB; 64 MiB stays
# well under that and under a typical "as large as it will go" probe.
STACK_BYTES = 64 * 1024 * 1024

# C stack reserved per host frame. CPython 3.11 frames are often nearer
# 1–2 KiB; 4 KiB keeps the recursion check ahead of a stack overflow.
BYTES_PER_FRAME = 4 * 1024
MAX_RECURSION = STACK_BYTES // BYTES_PER_FRAME

# Result length of ``tøwp`` on text or a list, and of ``ronɣ``. Written
# ``100000`` in φyrx (1,048,576).
MAX_SPAN = 0x100000
_SPAN_HINT = "the maximum is 100000 items"
_MEMORY_HINT = "a very large text, list, or number is the likely cause"

_LOCAL = threading.local()
_INTERRUPT_WAIT = 1.0


def recursion_limit() -> int:
    """Host-frame ceiling from ``PHYX_RECURSION``, or the default."""
    raw = os.environ.get("PHYX_RECURSION")
    if raw is None or raw.strip() == "":
        return DEFAULT_RECURSION
    text = raw.strip()
    try:
        value = int(text, 10)
    except ValueError:
        raise RuntimeFault(
            f"PHYX_RECURSION must be a decimal integer, not {raw!r}",
            hint=f"the default is {DEFAULT_RECURSION}",
        ) from None
    if value < MIN_RECURSION:
        raise RuntimeFault(
            "PHYX_RECURSION is too small to run a program",
            hint=f"use at least {MIN_RECURSION}, or unset it for {DEFAULT_RECURSION}",
        )
    if value > MAX_RECURSION:
        raise RuntimeFault(
            f"PHYX_RECURSION {value} does not fit in the {STACK_BYTES // (1024 * 1024)} MiB stack",
            hint=f"the safe ceiling is {MAX_RECURSION}",
        )
    return value


def memory_fault(line: int | None = None) -> RuntimeFault:
    """Runtime fault for a host ``MemoryError``. Line 0 means unknown."""
    if not line:
        line = None
    return RuntimeFault("the program ran out of memory", line, hint=_MEMORY_HINT)


def _interrupt_thread(thread: threading.Thread) -> None:
    """Ask ``thread`` to raise ``KeyboardInterrupt`` at the next bytecode.

    ``is_alive`` can be false on Python 3.11 and 3.12 right after ``join``
    was interrupted, while the thread is still running. An id that has
    already ended makes ``SetAsyncExc`` return 0.
    """
    ident = thread.ident
    if ident is None:
        return
    api = ctypes.pythonapi.PyThreadState_SetAsyncExc
    api.argtypes = (ctypes.c_ulong, ctypes.py_object)
    api.restype = ctypes.c_int
    count = api(ctypes.c_ulong(ident), ctypes.py_object(KeyboardInterrupt))
    if count > 1:  # pragma: no cover - more than one thread matched
        api(ctypes.c_ulong(ident), None)


def call_on_stack(fn: Callable[[], None]) -> None:
    """Run ``fn`` on the program thread, with the recursion ceiling applied.

    A call that is already on that thread runs directly, so ``bukð`` does
    not start a second thread.
    """
    if getattr(_LOCAL, "on", False):
        fn()
        return
    limit = recursion_limit()
    box: dict[str, BaseException] = {}
    done = threading.Event()

    def target() -> None:
        _LOCAL.on = True
        try:
            fn()
        except MemoryError:
            box["err"] = memory_fault()
        except BaseException as err:
            box["err"] = err
        finally:
            done.set()

    previous_limit = sys.getrecursionlimit()
    previous_stack = threading.stack_size(STACK_BYTES)
    thread: threading.Thread | None = None
    try:
        try:
            sys.setrecursionlimit(limit)
        except RecursionError:
            raise RuntimeFault(
                "PHYX_RECURSION is too small to run a program",
                hint=f"unset it for the default {DEFAULT_RECURSION}",
            ) from None
        thread = threading.Thread(target=target, name="phyx", daemon=True)
        thread.start()
    finally:
        threading.stack_size(previous_stack)
    try:
        try:
            if thread is not None and thread.ident is not None:
                # Short waits, not one blocking join. A pending Ctrl-C is
                # delivered on the next bytecode, which a single C-level
                # join may not reach until the worker has already exited.
                # ``done`` is set from the worker's finally. ``is_alive``
                # is wrong on 3.11 and 3.12 just after that interrupt.
                while not done.is_set():
                    thread.join(0.05)
            if "err" in box:
                raise box["err"]
        except KeyboardInterrupt:
            if thread is not None:
                _interrupt_thread(thread)
                thread.join(_INTERRUPT_WAIT)
            raise
    finally:
        sys.setrecursionlimit(previous_limit)


def repeat_sequence(seq: str | list, count: int, word: str, line: int | None = None):
    """Repeat text or a list. The result may be at most ``MAX_SPAN`` items.

    A count of zero or less yields an empty result, as does an empty value
    repeated any number of times. The check runs before the host allocates.
    """
    if count > 0 and len(seq) > MAX_SPAN // count:
        raise RuntimeFault(
            f"{word}: the repetition is too great",
            line,
            hint=_SPAN_HINT,
        )
    return seq * count


def take_turns(count: int, line: int | None = None) -> list:
    """``ronɣ``: ``[0, count)``. Longer than ``MAX_SPAN`` is a fault."""
    if count > MAX_SPAN:
        raise RuntimeFault(
            "ronɣ (turns): the count is too great",
            line,
            hint=_SPAN_HINT,
        )
    return list(range(count))
