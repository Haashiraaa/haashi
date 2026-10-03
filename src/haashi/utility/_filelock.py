

# src/haashi/utility/_filelock.py

"""Cross-process advisory file lock (standard library only)."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from .exceptions import LoggingError

_POLL_START = 0.001  # first retry after 1 ms ...
_POLL_MAX = 0.02     # ... backing off to 20 ms


def _timed_out(lock_path: Path, timeout: float) -> LoggingError:
    return LoggingError(
        f"Timed out after {timeout:g}s waiting for lock {lock_path}")


if sys.platform == "win32":
    import msvcrt

    def _try_lock(fd: int) -> bool:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _release(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:  # held by someone else; anything else propagates
            return False

    def _release(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _acquire(fd: int, lock_path: Path, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    delay = _POLL_START
    while not _try_lock(fd):
        if time.monotonic() >= deadline:
            raise _timed_out(lock_path, timeout)
        time.sleep(delay)
        delay = min(delay * 2, _POLL_MAX)


@contextmanager
def file_lock(target: Path, timeout: float = 10.0) -> Generator[None]:
    """Hold an exclusive lock for ``target`` across threads *and* processes.

    Waits up to ``timeout`` seconds, then raises ``LoggingError``. The OS drops
    the lock if the holder dies, so a crashed worker cannot wedge the others.

    The lock lives on a sibling ``<name>.lock`` file that is never renamed or
    deleted, so it stays valid while ``target`` is rotated or replaced.
    Advisory locks are unreliable on network filesystems (NFS/SMB).
    """
    lock_path = target.with_name(target.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        _acquire(fd, lock_path, timeout)
        try:
            yield
        finally:
            _release(fd)
    finally:
        os.close(fd)
