# src/haashi/aio/errorlogger.py

"""Async ErrorLogger: same names as ``haashi.utility.ErrorLogger``."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..utility._types import JSONType, PathLike
from ..utility.logger import ErrorLogger as _SyncErrorLogger


class ErrorLogger:
    """Async twin of :class:`haashi.utility.ErrorLogger`.

    The read-modify-write on the JSON file runs in a worker thread under the
    same lock the sync class uses, so ``asyncio.gather`` over many
    ``log_error`` calls loses no entries, and mixing sync and async callers
    in one process is safe.

    Example:
        >>> errors = ErrorLogger(log_dir="/var/log/myapp")
        >>> try:
        ...     await handle_request()
        ... except Exception as exc:
        ...     await errors.log_error(exc, context="POST /orders")
    """

    def __init__(self, log_dir: PathLike | None = None) -> None:
        """
        Args:
            log_dir: Directory relative log paths resolve under
                (see :class:`haashi.utility.ErrorLogger`).
        """
        self._sync = _SyncErrorLogger(log_dir)
        self.log_dir = self._sync.log_dir

    async def log_error(
        self,
        exception: BaseException,
        context: str | None = None,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        utc_offset_hours: float = 0,
        max_entries: int = 100,
    ) -> Path:
        """Append an error entry to the JSON log and return the file's path."""
        return await asyncio.to_thread(
            self._sync.log_error, exception, context, path,
            use_script_dir, utc_offset_hours, max_entries)

    async def view_error_entries(
        self,
        path: PathLike | None = None,
        limit: int | None = 10,
        use_script_dir: bool = True,
    ) -> list[JSONType]:
        """Return the most recent ``limit`` entries (``None`` for all)."""
        return await asyncio.to_thread(
            self._sync.view_error_entries, path, limit, use_script_dir)

    async def clear_errors(
        self,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        *,
        confirm: bool = True,
    ) -> bool:
        """Delete the error log. Returns True if a file was deleted.

        ``confirm=True`` needs an interactive terminal and raises
        ``LoggingError`` otherwise. Servers should pass ``confirm=False``.
        """
        return await asyncio.to_thread(
            self._sync.clear_errors, path, use_script_dir, confirm=confirm)
