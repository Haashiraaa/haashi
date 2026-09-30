# src/haashi/aio/filehandler.py

"""Async FileHandler: same names as ``haashi.utility.FileHandler``, awaitable IO."""

# The wrappers deliberately reach into the sync class's helpers so the caller
# frame lookup keeps pointing at *user* code.
# pyright: reportPrivateUsage=false

from __future__ import annotations

import asyncio
from pathlib import Path

from ..utility._types import JSONType, PathLike
from ..utility.filehandler import FileHandler as _SyncFileHandler
from ..utility.logger import Logger


class FileHandler:
    """Async twin of :class:`haashi.utility.FileHandler`.

    Disk IO runs in a worker thread (``asyncio.to_thread``), so the event loop
    is never blocked. Writes are atomic, so concurrent tasks can safely write
    different files; concurrent writes to the *same* file resolve last-write-wins.

    Methods that only compute paths (``get_script_dir``, ``get_parent_path``,
    ``get_ancestor_by_name``) stay plain synchronous methods: they do no
    meaningful IO, so there is nothing to await.

    Example:
        >>> fh = FileHandler()
        >>> await fh.save_json({"status": "ok"}, "data/output.json")
        >>> await fh.read_json("data/output.json")
        {'status': 'ok'}
    """

    def __init__(self, logger: Logger | None = None) -> None:
        self._sync = _SyncFileHandler(logger)
        self.logger = self._sync.logger

    # ---- path helpers (no IO worth awaiting) --------------------------------

    def get_script_dir(self) -> Path:
        """Directory of the executed main script (cwd if undetectable)."""
        return self._sync.get_script_dir()

    def get_parent_path(
        self,
        levels_up: int = 1,
        start_path: PathLike | None = None,
    ) -> Path:
        """Directory ``levels_up`` above the caller's script (see sync docs)."""
        if start_path is None:
            start_path = self._sync._resolve_start_dir(None)
        return self._sync.get_parent_path(levels_up, start_path)

    def get_ancestor_by_name(
        self,
        folder_name: str,
        start_path: PathLike | None = None,
        max_levels: int = 10,
    ) -> Path | None:
        """Find an ancestor directory by exact name (see sync docs)."""
        if start_path is None:
            start_path = self._sync._resolve_start_dir(None)
        return self._sync.get_ancestor_by_name(folder_name, start_path, max_levels)

    # ---- filesystem checks --------------------------------------------------

    async def ensure_writable_path(self, path: PathLike) -> Path:
        """Create parent directories for ``path`` and return it as a Path."""
        return await asyncio.to_thread(self._sync.ensure_writable_path, path)

    async def ensure_readable_file(self, path: PathLike) -> Path:
        """Return ``path`` if it is an existing file."""
        return await asyncio.to_thread(self._sync.ensure_readable_file, path)

    # ---- JSON ---------------------------------------------------------------

    async def save_json(
        self,
        data: JSONType,
        path: PathLike,
        indent: int = 4,
    ) -> None:
        """Save JSON-serializable data to a file (atomic)."""
        await asyncio.to_thread(self._sync.save_json, data, path, indent)

    async def read_json(self, path: PathLike) -> JSONType:
        """Read a JSON file."""
        return await asyncio.to_thread(self._sync.read_json, path)

    # ---- text ---------------------------------------------------------------

    async def save_txt(
        self,
        data: str,
        path: PathLike,
        mode: str = "w",
        add_newline_prefix: bool = True,
    ) -> None:
        """Save a string to a text file (``"w"`` overwrite, ``"a"`` append)."""
        await asyncio.to_thread(
            self._sync.save_txt, data, path, mode, add_newline_prefix)

    async def read_txt(self, path: PathLike) -> str:
        """Read a text file."""
        return await asyncio.to_thread(self._sync.read_txt, path)
