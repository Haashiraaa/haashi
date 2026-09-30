# src/haashi/utility/filehandler.py

"""File operations with validation and script-relative path helpers."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from ._atomic import atomic_write_text
from ._paths import detect_script_dir
from ._types import JSONType, PathLike, dump_json
from .exceptions import FileOperationError
from .logger import Logger


class FileHandler:
    """JSON/TXT file I/O plus helpers for locating paths relative to your script.

    Example:
        >>> fh = FileHandler()
        >>> fh.save_json({"key": "value"}, "data/output.json")
        >>> fh.read_json("data/output.json")
        {'key': 'value'}
    """

    def __init__(self, logger: Logger | None = None) -> None:
        """
        Args:
            logger: Optional Logger. The default only shows warnings.
        """
        self.logger = logger or Logger()

    # ---- path helpers -------------------------------------------------

    def _resolve_start_dir(self, start_path: PathLike | None) -> Path:
        """Directory to start walking from: ``start_path`` or the caller's file dir."""
        if start_path is not None:
            return Path(start_path).resolve()

        frame = inspect.currentframe()
        try:
            # frame -> this method; f_back -> public method; f_back.f_back -> caller
            public = frame.f_back if frame else None
            caller = public.f_back if public else None
            caller_file = caller.f_globals.get("__file__") if caller else None
        finally:
            del frame

        if caller_file:
            return Path(caller_file).resolve().parent
        self.logger.debug("Could not detect caller file, using cwd")
        return Path.cwd()

    def get_script_dir(self) -> Path:
        """Directory of the executed main script (cwd if it can't be detected)."""
        return detect_script_dir(self.logger)

    def get_parent_path(
        self,
        levels_up: int = 1,
        start_path: PathLike | None = None,
    ) -> Path:
        """Get the directory ``levels_up`` above the caller's script.

        Args:
            levels_up: How many parents to climb (>= 0).
            start_path: Start here instead of the caller's script directory.

        Raises:
            ValueError: If ``levels_up`` is negative.

        Example:
            >>> # script: my-project/src/scripts/process.py
            >>> FileHandler().get_parent_path(levels_up=2)
            PosixPath('/home/user/my-project')
        """
        if levels_up < 0:
            raise ValueError(f"levels_up must be non-negative, got {levels_up}")

        current = self._resolve_start_dir(start_path)
        for _ in range(levels_up):
            current = current.parent
        self.logger.debug(f"Navigated up {levels_up} levels to: {current}")
        return current

    def get_ancestor_by_name(
        self,
        folder_name: str,
        start_path: PathLike | None = None,
        max_levels: int = 10,
    ) -> Path | None:
        """Find an ancestor directory by exact (case-sensitive) name.

        Returns the path, or None if not found within ``max_levels``.

        Example:
            >>> # script: my-project/src/modules/analysis.py
            >>> FileHandler().get_ancestor_by_name("my-project")
            PosixPath('/home/user/my-project')
        """
        current = self._resolve_start_dir(start_path)
        candidates = [current, *current.parents]
        for level, candidate in zip(range(max_levels), candidates, strict=False):
            if candidate.name == folder_name:
                self.logger.debug(
                    f"Found ancestor '{folder_name}' at: {candidate} "
                    f"({level} levels up)")
                return candidate

        self.logger.warning(
            f"Folder '{folder_name}' not found within {max_levels} levels up")
        return None

    def ensure_writable_path(self, path: PathLike) -> Path:
        """Create parent directories for ``path`` and return it as a Path.

        Raises:
            FileOperationError: If the directories can't be created.
        """
        file_path = Path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FileOperationError(
                f"Failed to create path {file_path}: {exc}") from exc
        return file_path

    def ensure_readable_file(self, path: PathLike) -> Path:
        """Return ``path`` as a Path if it is an existing file.

        Raises:
            FileNotFoundError: If it doesn't exist.
            FileOperationError: If it exists but isn't a file.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise FileOperationError(f"Not a file: {file_path}")
        return file_path

    # ---- JSON ----------------------------------------------------------

    def save_json(self, data: JSONType, path: PathLike, indent: int = 4) -> None:
        """Save JSON-serializable data to a file (overwrites).

        Raises:
            InvalidJsonFormatError: If ``data`` isn't JSON-serializable
                (nothing is written in that case).
            FileOperationError: If the file can't be written.
        """
        payload = dump_json(data, indent=indent)  # validate before touching disk
        file_path = self.ensure_writable_path(path)
        try:
            atomic_write_text(file_path, payload)
        except OSError as exc:
            raise FileOperationError(
                f"Failed to save JSON to {file_path}: {exc}") from exc
        self.logger.debug(f"JSON saved -> {file_path}")

    def read_json(self, path: PathLike) -> JSONType:
        """Read a JSON file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            FileOperationError: If the JSON is invalid or the read fails.
        """
        file_path = self.ensure_readable_file(path)
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise FileOperationError(f"Invalid JSON in {file_path}: {exc}") from exc
        except OSError as exc:
            raise FileOperationError(
                f"Failed to read JSON from {file_path}: {exc}") from exc

    # ---- text ----------------------------------------------------------

    def save_txt(
        self,
        data: str,
        path: PathLike,
        mode: str = "w",
        add_newline_prefix: bool = True,
    ) -> None:
        """Save a string to a text file.

        Args:
            data: Content to write.
            path: Destination file.
            mode: ``"w"`` to overwrite or ``"a"`` to append.
            add_newline_prefix: Write a newline before the content.

        Raises:
            ValueError: If ``mode`` is not ``"w"`` or ``"a"``.
            FileOperationError: If the file can't be written.
        """
        if mode not in ("w", "a"):
            raise ValueError(f"mode must be 'w' or 'a', got {mode!r}")
        file_path = self.ensure_writable_path(path)
        try:
            if mode == "w":
                atomic_write_text(file_path, ("\n" if add_newline_prefix else "") + data)
            else:
                with open(file_path, "a", encoding="utf-8") as f:
                    if add_newline_prefix:
                        f.write("\n")
                    f.write(data)
        except OSError as exc:
            raise FileOperationError(
                f"Failed to save TXT to {file_path}: {exc}") from exc
        self.logger.debug(f"TXT saved -> {file_path}")

    def read_txt(self, path: PathLike) -> str:
        """Read a text file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            FileOperationError: If the read fails.
        """
        file_path = self.ensure_readable_file(path)
        try:
            return file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise FileOperationError(
                f"Failed to read TXT from {file_path}: {exc}") from exc
