

# src/haashi/aio/jsonl_errorlogger.py

"""Async JsonlErrorLogger: same names as ``haashi.utility.JsonlErrorLogger``."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..utility._types import JSONType, PathLike
from ..utility.logger import JsonlErrorLogger as _SyncJsonlErrorLogger


class JsonlErrorLogger:
    """Async twin of :class:`haashi.utility.JsonlErrorLogger`.

    Appends run in a worker thread under the same thread and cross-process
    locks as the sync class, so ``asyncio.gather`` over many ``log_error``
    calls, other threads, and other worker processes never lose entries.

    Example:
        >>> errors = JsonlErrorLogger(log_dir="/var/log/myapp", max_bytes=5_000_000)
        >>> try:
        ...     await handle_request()
        ... except Exception as exc:
        ...     await errors.log_error(exc, context="POST /orders")
    """

    def __init__(
        self,
        log_dir: PathLike | None = None,
        *,
        max_bytes: int | None = None,
        backups: int = 3,
        fsync: bool = False,
        lock_timeout: float = 10.0,
    ) -> None:
        self._sync = _SyncJsonlErrorLogger(
            log_dir, max_bytes=max_bytes, backups=backups,
            fsync=fsync, lock_timeout=lock_timeout)
        self.log_dir = self._sync.log_dir

    async def log_error(
        self,
        exception: BaseException,
        context: str | None = None,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        utc_offset_hours: float = 0,
    ) -> Path:
        """Append an error entry and return the path of the file written."""
        return await asyncio.to_thread(
            self._sync.log_error, exception,
            context=context, path=path, use_script_dir=use_script_dir,
            utc_offset_hours=utc_offset_hours)

    async def view_error_entries(
        self,
        path: PathLike | None = None,
        limit: int | None = 10,
        use_script_dir: bool = True,
    ) -> list[JSONType]:
        """Return the most recent ``limit`` entries (``None`` for all)."""
        return await asyncio.to_thread(
            self._sync.view_error_entries,
            path=path, limit=limit, use_script_dir=use_script_dir)

    async def clear_errors(
        self,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        *,
        confirm: bool = True,
    ) -> bool:
        """Delete the log and its backups. Servers should pass ``confirm=False``."""
        return await asyncio.to_thread(
            self._sync.clear_errors,
            path=path, use_script_dir=use_script_dir, confirm=confirm)
