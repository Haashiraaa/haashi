# src/haashi/utility/logger.py

"""Console logging plus optional JSON persistence of errors."""

from __future__ import annotations

import itertools
import json
import logging
import os
import sys
import traceback
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, TextIO, cast

from ._datetime import DateTime
from ._paths import detect_script_dir
from ._types import JSONType, PathLike
from .exceptions import LoggingError
from .uiux import Colors

DEFAULT_ERROR_LOG_PATH = Path("logs/errors_log.json")

_logger_ids = itertools.count()  # unique per Logger, never reused (unlike id())


def _color_enabled(stream: TextIO, color: bool | None) -> bool:
    """Decide whether to emit ANSI colors.

    ``color=True/False`` forces it. Otherwise colors are used only when the
    stream is a terminal and the ``NO_COLOR`` environment variable
    (https://no-color.org) is unset, so log files and CI output stay clean.
    """
    if color is not None:
        return color
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return stream.isatty()
    except (AttributeError, ValueError):  # missing or closed stream
        return False


class _ColorFormatter(logging.Formatter):
    """Paints each formatted record with the matching ``Colors`` helper."""

    _PAINTERS: ClassVar[dict[int, Callable[[str], str]]] = {
        logging.DEBUG: Colors.debug,
        logging.INFO: Colors.info,
        logging.WARNING: Colors.warning,
        logging.ERROR: Colors.error,
        logging.CRITICAL: Colors.error,
    }

    def __init__(self, fmt: str, use_color: Callable[[], bool]) -> None:
        super().__init__(fmt)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        painter = self._PAINTERS.get(record.levelno)
        if painter is None or not self._use_color():
            return text
        return painter(text)


class ErrorLogger:
    """Persist errors to a rotating JSON file.

    Every method that takes ``path`` and ``use_script_dir`` resolves the file
    the same way, so what ``log_error`` writes is what ``view_error_entries``
    and ``clear_errors`` read.

    Example:
        >>> error_logger = ErrorLogger()
        >>> try:
        ...     1 / 0
        ... except ZeroDivisionError as exc:
        ...     error_logger.log_error(exc, context="math")
        >>> error_logger.view_error_entries(limit=5)
    """

    @staticmethod
    def _resolve_path(path: PathLike | None, use_script_dir: bool) -> Path:
        error_path = Path(path) if path is not None else DEFAULT_ERROR_LOG_PATH
        return detect_script_dir() / error_path if use_script_dir else error_path

    @staticmethod
    def _read_error_entries(path: Path) -> list[JSONType]:
        """Read existing entries; a missing or corrupt file yields ``[]``."""
        if not path.exists():
            return []
        try:
            with open(path, encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            warnings.warn(
                f"Corrupted error log at {path} ({exc}); starting a fresh log. "
                f"The old file is overwritten on the next write.",
                RuntimeWarning,
                stacklevel=3,
            )
            return []
        if not isinstance(entries, list):
            warnings.warn(
                f"Error log at {path} is not a JSON list; starting a fresh log.",
                RuntimeWarning,
                stacklevel=3,
            )
            return []
        return cast("list[JSONType]", entries)

    @staticmethod
    def _write_error_entries(entries: list[JSONType], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=4, default=str),
                        encoding="utf-8")

    @staticmethod
    def _traceback_string(exception: BaseException) -> str:
        return "".join(traceback.format_exception(exception))

    def log_error(
        self,
        exception: BaseException,
        context: str | None = None,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        utc_offset_hours: float = 0,
        max_entries: int = 100,
    ) -> Path:
        """Append an error entry to the JSON log and return the file's path.

        Args:
            exception: The exception to record.
            context: Free-form label such as "data_loading".
            path: Log file (default ``logs/errors_log.json``).
            use_script_dir: Resolve ``path`` relative to the running script's
                directory instead of the current working directory.
            utc_offset_hours: UTC offset used for the timestamp (-12 to +14).
            max_entries: Keep only the most recent N entries.

        Raises:
            ValueError: If ``max_entries`` < 1 or the offset is out of range.
        """
        if max_entries < 1:
            raise ValueError(f"max_entries must be at least 1, got {max_entries}")

        error_path = self._resolve_path(path, use_script_dir)
        entries = self._read_error_entries(error_path)

        entry: dict[str, JSONType] = {
            "timestamp": DateTime.get_current_time(
                utc_offset_hours, string_format=False).isoformat(),
            "type": type(exception).__name__,
            "message": str(exception),
            "context": context or "unspecified",
            "traceback": self._traceback_string(exception),
        }
        entries.append(entry)
        self._write_error_entries(entries[-max_entries:], error_path)
        return error_path

    def view_error_entries(
        self,
        path: PathLike | None = None,
        limit: int | None = 10,
        use_script_dir: bool = True,
    ) -> list[JSONType]:
        """Return the most recent ``limit`` entries (``None`` for all)."""
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1 or None, got {limit}")
        entries = self._read_error_entries(
            self._resolve_path(path, use_script_dir))
        return entries if limit is None else entries[-limit:]

    def clear_errors(
        self,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        *,
        confirm: bool = True,
    ) -> bool:
        """Delete the error log. Returns True if a file was deleted.

        Args:
            confirm: Ask on the terminal first. Needs an interactive session;
                pass ``confirm=False`` in scripts, CI, or servers.

        Raises:
            LoggingError: If ``confirm=True`` but stdin is not interactive.
        """
        error_path = self._resolve_path(path, use_script_dir)
        if not error_path.exists():
            return False

        if confirm:
            if not sys.stdin.isatty():
                raise LoggingError(
                    "clear_errors(confirm=True) needs an interactive terminal; "
                    "pass confirm=False in non-interactive code."
                )
            answer = input(
                f"Delete all entries in {error_path}? This cannot be undone. [y/N] ")
            if answer.strip().lower() not in {"y", "yes"}:
                return False

        error_path.unlink()
        return True


class Logger:
    """Console logger with optional JSON persistence for errors.

    Each instance owns an independent logger, so one instance's level never
    affects another's, and nothing is configured on the root logger.

    Output is colored by level using :class:`~haashi.utility.Colors` (debug
    cyan, info blue, warning yellow, error red) when writing to a terminal.
    It is plain text in files, pipes and CI, and when ``NO_COLOR`` is set.

    Example:
        >>> logger = Logger(level=logging.INFO)
        >>> logger.info("Processing started")
        >>> try:
        ...     risky()
        ... except Exception as exc:
        ...     logger.error("risky() failed", exception=exc, save_to_json=True)
    """

    def __init__(self, level: int = logging.WARNING, color: bool | None = None) -> None:
        """
        Args:
            level: Logging level (logging.INFO, logging.DEBUG, ...).
            color: ``None`` (default) colors output only on a terminal;
                ``True`` / ``False`` force colors on / off.
        """
        self.logger = logging.getLogger(f"haashi.{next(_logger_ids)}")
        self.logger.setLevel(level)
        self.logger.propagate = False

        handler = logging.StreamHandler()
        handler.setFormatter(_ColorFormatter(
            "[%(levelname)s] %(message)s",
            lambda: _color_enabled(handler.stream, color),
        ))
        self.logger.addHandler(handler)

    def info(self, message: Any) -> None:
        """Log an informational message."""
        self.logger.info(str(message))

    def debug(self, message: Any) -> None:
        """Log a debug message (visible only at DEBUG level)."""
        self.logger.debug(str(message))

    def warning(self, message: Any) -> None:
        """Log a warning."""
        self.logger.warning(str(message))

    @staticmethod
    def _persist(
        exception: BaseException,
        error_logger: ErrorLogger | None,
        path: PathLike | None,
        use_script_dir: bool,
        context: str | None,
    ) -> Path:
        return (error_logger or ErrorLogger()).log_error(
            exception, context=context, path=path, use_script_dir=use_script_dir)

    def error(
        self,
        message: Any = "Error occurred!",
        error_logger: ErrorLogger | None = None,
        path: PathLike | None = None,
        exception: BaseException | None = None,
        save_to_json: bool = False,
        use_script_dir: bool = True,
        context: str | None = None,
    ) -> None:
        """Log an error and optionally persist it to JSON.

        Args:
            message: The message to log.
            error_logger: ErrorLogger to persist with (a default one is
                created when omitted).
            path: JSON log file (default ``logs/errors_log.json``).
            exception: The exception to persist.
            save_to_json: Persist ``exception`` to the JSON log.
            use_script_dir: Resolve ``path`` next to the running script.
            context: Free-form label stored with the entry.

        Raises:
            LoggingError: If ``save_to_json=True`` without an ``exception``.
        """
        text = str(message)
        if save_to_json:
            if exception is None:
                raise LoggingError("save_to_json=True requires an `exception` argument")
            saved_to = self._persist(
                exception, error_logger, path, use_script_dir, context)
            text = f"{text}\nSee {saved_to} for details"
        self.logger.error(text)

    def exception(
        self,
        message: Any = "Exception occurred!",
        error_logger: ErrorLogger | None = None,
        save_to_json: bool = False,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        context: str | None = None,
    ) -> None:
        """Log the exception currently being handled, with its traceback.

        Call from inside an ``except`` block.

        Raises:
            LoggingError: If called outside an active exception handler.

        Example:
            >>> try:
            ...     risky()
            ... except Exception:
            ...     logger.exception("risky() failed", save_to_json=True)
        """
        exc = sys.exc_info()[1]
        if exc is None:
            raise LoggingError("logger.exception() must be called inside an `except` block")

        self.logger.error(str(message), exc_info=True)  # noqa: LOG014
        if save_to_json:
            saved_to = self._persist(
                exc, error_logger, path, use_script_dir, context)
            self.logger.info(f"Exception logged to {saved_to}")
