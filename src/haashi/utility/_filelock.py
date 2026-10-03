

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

if sys.platform == "win32":
    import msvcrt

    _POLL = 0.01

    def _acquire(fd: int, lock_path: Path, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise LoggingError(
                        f"Timed out after {timeout:g}s waiting for lock {lock_path}"
                    ) from None
                time.sleep(_POLL)

    def _release(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _acquire(fd: int, lock_path: Path, timeout: float) -> None:
        # Blocking. The OS drops the lock if the holder dies, so a crashed
        # worker can never wedge the others.
        fcntl.flock(fd, fcntl.LOCK_EX)

    def _release(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def file_lock(target: Path, timeout: float = 10.0) -> Generator[None]:
    """Hold an exclusive lock for ``target`` across threads *and* processes.

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
