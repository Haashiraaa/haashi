# src/haashi/utility/_atomic.py

"""Crash-safe file writing shared by ErrorLogger and FileHandler."""

from __future__ import annotations

import os
import threading
from pathlib import Path


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` to ``path`` without ever leaving a half-written file.

    Writes to a temporary sibling file, flushes it to disk, then swaps it
    into place with ``os.replace`` (atomic on POSIX and Windows). Readers see
    either the old content or the new content, never a mix.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
