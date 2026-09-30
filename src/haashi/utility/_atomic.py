

# src/haashi/utility/_atomic.py

"""Crash-safe file writing shared by ErrorLogger and FileHandler."""

from __future__ import annotations

import contextlib
import os
import threading
import time
from pathlib import Path

_REPLACE_RETRIES = 5


def _replace(src: Path, dst: Path) -> None:
    """``os.replace`` with a short retry for transient Windows file locks."""
    for attempt in range(_REPLACE_RETRIES):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            # Windows: the target may be briefly held open (antivirus, indexer).
            if os.name != "nt" or attempt == _REPLACE_RETRIES - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


def _fsync_dir(directory: Path) -> None:
    """Best-effort fsync of the directory so the rename itself is durable."""
    if os.name != "posix":
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        with contextlib.suppress(OSError):
            os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` to ``path`` without ever leaving a half-written file.

    Writes to a temporary sibling file, flushes it to disk, then swaps it into
    place with ``os.replace``. Readers see either the old content or the new
    content, never a mix. Symlinks are written through (the link is kept), and
    an existing file's permission bits are preserved.
    """
    target = Path(os.path.realpath(path))
    try:
        mode: int | None = target.stat().st_mode & 0o7777
    except FileNotFoundError:
        mode = None

    tmp = target.with_name(
        f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        _replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    _fsync_dir(target.parent)
