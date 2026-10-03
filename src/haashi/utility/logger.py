# src/haashi/utility/logger.py

"""Console logging plus optional JSON persistence of errors."""

from __future__ import annotations

import itertools
import json
import logging
import os
import sys
import threading
import traceback
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, ClassVar, TextIO, cast

from ._atomic import atomic_write_text, replace_file
from ._datetime import DateTime
from ._filelock import file_lock
from ._paths import detect_script_dir, resolve_log_path  # noqa: F401 # type: ignore
from ._types import ErrorWriter, JSONType, PathLike
from .exceptions import LoggingError
from .uiux import Colors

DEFAULT_ERROR_LOG_FILENAME = "errors_log.json"
DEFAULT_ERROR_LOG_FILENAME_JSONL = "errors_log.jsonl"
DEFAULT_ERROR_LOG_PATH = Path("logs") / DEFAULT_ERROR_LOG_FILENAME

_logger_ids = itertools.count()  # unique per Logger, never reused (unlike id())

# Serializes read-modify-write cycles on error-log files across threads.
# (Multiple *processes* writing one file still need external coordination.)
_LOG_LOCK = threading.RLock()

# Cheap in-process exclusion on top of the cross-process file lock.
_THREAD_LOCK = threading.RLock()


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

    Where the file lives:
        * ``log_dir`` set: relative paths (and the default file name) resolve
          under it. Use this for servers and services, where "the script's
          directory" is the server's entry point, not your app.
        * ``log_dir`` not set: relative paths resolve next to the running
          script (``use_script_dir=True``, the default) or the current
          directory (``use_script_dir=False``).
        * An absolute ``path`` is always used as given.

    Example:
        >>> error_logger = ErrorLogger()                       # CLI / scripts
        >>> service_logger = ErrorLogger(log_dir="/var/log/myapp")   # backend
        >>> try:
        ...     1 / 0
        ... except ZeroDivisionError as exc:
        ...     error_logger.log_error(exc, context="math")
        >>> error_logger.view_error_entries(limit=5)
    """

    def __init__(self, log_dir: PathLike | None = None) -> None:
        """
        Args:
            log_dir: Directory that relative log paths resolve under. ``~``
                is expanded. ``None`` keeps the script-relative behavior.
        """
        self.log_dir: Path | None = (
            Path(log_dir).expanduser() if log_dir is not None else None)

    @staticmethod
    def _quarantine(path: Path, problem: str) -> None:
        """Move an unreadable log aside (never overwriting an earlier backup)."""
        backup = path.with_name(path.name + ".corrupt")
        n = 0
        while backup.exists():
            n += 1
            backup = path.with_name(f"{path.name}.corrupt.{n}")
        path.replace(backup)
        warnings.warn(
            f"{problem} at {path}; moved it to {backup} and starting a fresh log.",
            RuntimeWarning,
            stacklevel=4,
        )

    def _resolve_path(self, path: PathLike | None, use_script_dir: bool) -> Path:
        return resolve_log_path(
            path, self.log_dir, DEFAULT_ERROR_LOG_FILENAME, use_script_dir)

    @staticmethod
    def _read_error_entries(path: Path) -> list[JSONType]:
        """Read existing entries; a missing or corrupt file yields ``[]``."""
        if not path.exists():
            return []
        try:
            with open(path, encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            ErrorLogger._quarantine(path, f"Corrupted error log ({exc})")
            return []
        if not isinstance(entries, list):
            ErrorLogger._quarantine(path, "Error log is not a JSON list")
            return []
        return cast("list[JSONType]", entries)

    @staticmethod
    def _write_error_entries(entries: list[JSONType], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(entries, indent=4, default=str))

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
            raise ValueError(
                f"max_entries must be at least 1, got {max_entries}")

        error_path = self._resolve_path(path, use_script_dir)

        entry: dict[str, JSONType] = {
            "timestamp": DateTime.get_current_time(
                utc_offset_hours, string_format=False).isoformat(),
            "type": type(exception).__name__,
            "message": str(exception),
            "context": context or "unspecified",
            "traceback": self._traceback_string(exception),
        }
        with _LOG_LOCK:
            entries = self._read_error_entries(error_path)
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
        with _LOG_LOCK:
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

        with _LOG_LOCK:
            error_path.unlink(missing_ok=True)
        return True


def _iter_lines_reverse(path: Path, chunk: int = 64 * 1024) -> Iterator[bytes]:
    """Yield the non-blank lines of ``path`` from last to first.

    Reads backwards in ``chunk``-sized blocks, so memory stays bounded however
    large the file is. Splitting on ``b"\n"`` is safe for UTF-8: that byte never
    appears inside a multi-byte character.
    """
    with open(path, "rb") as f:
        pos = f.seek(0, os.SEEK_END)
        buf = b""
        while pos > 0:
            size = min(chunk, pos)
            pos -= size
            f.seek(pos)
            buf = f.read(size) + buf
            parts = buf.split(b"\n")
            # may be the tail of a line that started in an earlier chunk
            buf = parts[0]
            for line in reversed(parts[1:]):
                if line.strip():
                    yield line
        if buf.strip():
            yield buf


class JsonlErrorLogger:
    """Error log that appends one JSON object per line.

    Unlike :class:`ErrorLogger`, which rewrites a whole JSON array on every
    call, this never reads or rewrites the file: each error is a single
    append, so the cost stays flat however large the log gets. Every write
    takes a cross-process file lock, so several processes (for example
    gunicorn workers) can share one log without losing entries.

    Use ``ErrorLogger`` for occasional errors and a human-friendly file; use
    this for backends, error bursts and multi-worker servers. Same method
    names, so ``Logger(error_logger=JsonlErrorLogger(...))`` works unchanged.

    Rotation is by size: when a write would push the file past ``max_bytes``
    it becomes ``<file>.1`` (older ones shift to ``.2``, ``.3``, ...), and the
    oldest beyond ``backups`` is dropped.

    Where the file lives follows the same rules as ``ErrorLogger``: absolute
    ``path`` wins; relative paths resolve under ``log_dir`` if set, else next
    to the running script (``use_script_dir=True``) or the current directory.
    The default file is ``logs/errors_log.jsonl``.

    Limits: advisory locks are unreliable on network filesystems (NFS/SMB),
    so don't share one log across hosts.

    Example:
        >>> errors = JsonlErrorLogger(log_dir="/var/log/myapp",
        ...                           max_bytes=5_000_000, backups=5)
        >>> try:
        ...     1 / 0
        ... except ZeroDivisionError as exc:
        ...     errors.log_error(exc, context="math")
        >>> errors.view_error_entries(limit=5)
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
        """
        Args:
            log_dir: Directory relative log paths resolve under (``~`` expanded).
            max_bytes: Rotate once the file would exceed this size. ``None``
                never rotates (the log grows without bound).
            backups: Rotated files to keep (0 = just discard on rotation).
            fsync: Force every entry to disk. Slow, but survives power loss.
                Off by default: entries still survive a process crash.
            lock_timeout: Seconds to wait for the cross-process lock before
                raising ``LoggingError`` (0 = try once). Enforced on every platform. 

        Raises:
            ValueError: If a number is out of range.
        """
        if max_bytes is not None and max_bytes < 1:
            raise ValueError(f"max_bytes must be at least 1, got {max_bytes}")
        if backups < 0:
            raise ValueError(f"backups must be 0 or more, got {backups}")
        if lock_timeout < 0:
            raise ValueError(
                f"lock_timeout must be 0 or more, got {lock_timeout}")
        self.log_dir: Path | None = (
            Path(log_dir).expanduser() if log_dir is not None else None)
        self.max_bytes = max_bytes
        self.backups = backups
        self.fsync = fsync
        self.lock_timeout = lock_timeout

    # ---- internals ----------------------------------------------------------

    def _resolve_path(self, path: PathLike | None, use_script_dir: bool) -> Path:
        return resolve_log_path(
            path, self.log_dir, DEFAULT_ERROR_LOG_FILENAME_JSONL, use_script_dir)

    @staticmethod
    def _backup(path: Path, n: int) -> Path:
        return path.with_name(f"{path.name}.{n}")

    def _all_files(self, path: Path) -> list[Path]:
        """Rotated backups (oldest first), then the live file."""
        return [self._backup(path, n) for n in range(self.backups, 0, -1)] + [path]

    def _rotate_if_needed(self, path: Path, incoming: int) -> None:
        if self.max_bytes is None:
            return
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return
        if size == 0 or size + incoming <= self.max_bytes:
            return
        if self.backups == 0:
            path.unlink(missing_ok=True)
            return
        for i in range(self.backups - 1, 0, -1):
            older = self._backup(path, i)
            if older.exists():
                replace_file(older, self._backup(path, i + 1))
        replace_file(path, self._backup(path, 1))

    def _append(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:  # "ab" opens with O_APPEND
            f.write(data)
            f.flush()
            if self.fsync:
                os.fsync(f.fileno())

    def _read_entries(self, path: Path, limit: int | None) -> list[JSONType]:
        """The last ``limit`` entries (all if None), oldest first.

        Reads newest-first (live file, then ``.1``, ``.2``, ...) from the end of
        each file and stops as soon as it has enough, so ``limit=10`` on a
        500 MB log touches a few KB. Unparseable lines (e.g. one cut short by a
        hard crash) are skipped with a warning and don't count toward ``limit``.
        """
        newest_first: list[JSONType] = []
        skipped = 0
        done = False
        for file in reversed(self._all_files(path)):
            if done:
                break
            if not file.exists():
                continue
            for raw in _iter_lines_reverse(file):
                try:
                    entry: JSONType = json.loads(
                        raw.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                newest_first.append(entry)
                if limit is not None and len(newest_first) >= limit:
                    done = True
                    break
        if skipped:
            warnings.warn(
                f"Skipped {skipped} unreadable line(s) in error log {path}",
                RuntimeWarning,
                stacklevel=3,
            )
        newest_first.reverse()
        return newest_first

    # ---- public API (same names as ErrorLogger) -----------------------------

    def log_error(
        self,
        exception: BaseException,
        context: str | None = None,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        utc_offset_hours: float = 0,
    ) -> Path:
        """Append an error entry and return the path of the file written.

        Args:
            exception: The exception to record.
            context: Free-form label such as "data_loading".
            path: Log file (default ``logs/errors_log.jsonl``).
            use_script_dir: Resolve a relative ``path`` next to the running
                script instead of the current directory. Ignored when
                ``log_dir`` is set.
            utc_offset_hours: UTC offset used for the timestamp (-12 to +14).

        Raises:
            ValueError: If the offset is out of range.
            LoggingError: If the cross-process lock can't be acquired in time.
        """
        log_path = self._resolve_path(path, use_script_dir)
        entry: dict[str, JSONType] = {
            "timestamp": DateTime.get_current_time(
                utc_offset_hours, string_format=False).isoformat(),
            "type": type(exception).__name__,
            "message": str(exception),
            "context": context or "unspecified",
            "traceback": "".join(traceback.format_exception(exception)),
        }
        # json.dumps escapes newlines inside strings: one entry is always one line.
        data = (json.dumps(entry, default=str, separators=(
            ",", ":")) + "\n").encode("utf-8")

        with _THREAD_LOCK, file_lock(log_path, self.lock_timeout):
            self._rotate_if_needed(log_path, len(data))
            self._append(log_path, data)
        return log_path

    def view_error_entries(
        self,
        path: PathLike | None = None,
        limit: int | None = 10,
        use_script_dir: bool = True,
    ) -> list[JSONType]:
        """Return the most recent ``limit`` entries (``None`` for all).

        Reads rotated backups too, oldest first. A missing log returns ``[]``
        and creates nothing.
        """
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1 or None, got {limit}")
        log_path = self._resolve_path(path, use_script_dir)
        if not any(f.exists() for f in self._all_files(log_path)):
            return []
        with _THREAD_LOCK, file_lock(log_path, self.lock_timeout):
            return self._read_entries(log_path, limit)

    def clear_errors(
        self,
        path: PathLike | None = None,
        use_script_dir: bool = True,
        *,
        confirm: bool = True,
    ) -> bool:
        """Delete the log and its rotated backups. True if anything was deleted.

        Args:
            confirm: Ask on the terminal first. Needs an interactive session;
                pass ``confirm=False`` in scripts, CI, or servers.

        Raises:
            LoggingError: If ``confirm=True`` but stdin is not interactive.
        """
        log_path = self._resolve_path(path, use_script_dir)
        if not any(f.exists() for f in self._all_files(log_path)):
            return False

        if confirm:
            if not sys.stdin.isatty():
                raise LoggingError(
                    "clear_errors(confirm=True) needs an interactive terminal; "
                    "pass confirm=False in non-interactive code."
                )
            answer = input(
                f"Delete all entries in {log_path}? This cannot be undone. [y/N] ")
            if answer.strip().lower() not in {"y", "yes"}:
                return False

        with _THREAD_LOCK, file_lock(log_path, self.lock_timeout):
            for file in self._all_files(log_path):
                file.unlink(missing_ok=True)
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

    def __init__(
        self,
        level: int = logging.WARNING,
        color: bool | None = None,
        error_logger: ErrorWriter | None = None,
    ) -> None:
        """
        Args:
            level: Logging level (logging.INFO, logging.DEBUG, ...).
            color: ``None`` (default) colors output only on a terminal;
                ``True`` / ``False`` force colors on / off.
            error_logger: Default ErrorLogger used whenever ``save_to_json``
                is set, e.g. ``ErrorLogger(log_dir="/var/log/myapp")`` so a
                service doesn't have to pass one on every call. A per-call
                ``error_logger`` still overrides it.
        """
        self.error_logger = error_logger
        # Instantiated directly instead of via logging.getLogger(): getLogger
        # registers the logger in a global dict that is never cleaned up, so
        # creating Loggers repeatedly (e.g. per request) would leak forever.
        self.logger = logging.Logger(f"haashi.{next(_logger_ids)}", level)
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

    def _persist(
        self,
        exception: BaseException,
        error_logger: ErrorWriter | None,
        path: PathLike | None,
        use_script_dir: bool,
        context: str | None,
    ) -> Path:
        writer = error_logger or self.error_logger
        if writer is None:
            writer = self.error_logger = ErrorLogger()
        return writer.log_error(
            exception, context=context, path=path, use_script_dir=use_script_dir)

    def _log_persisted(
        self,
        emit: Callable[[str], None],
        message: Any,
        error_logger: ErrorWriter | None,
        path: PathLike | None,
        exception: BaseException | None,
        save_to_json: bool,
        use_script_dir: bool,
        context: str | None,
    ) -> None:
        """Shared body of ``error`` and ``critical``."""
        text = str(message)
        if save_to_json:
            if exception is None:
                raise LoggingError(
                    "save_to_json=True requires an `exception` argument")
            saved_to = self._persist(
                exception, error_logger, path, use_script_dir, context)
            text = f"{text}\nSee {saved_to} for details"
        emit(text)

    def error(
        self,
        message: Any = "Error occurred!",
        error_logger: ErrorWriter | None = None,
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
        self._log_persisted(
            self.logger.error, message, error_logger, path, exception,
            save_to_json, use_script_dir, context)

    def critical(
        self,
        message: Any = "Critical error!",
        error_logger: ErrorWriter | None = None,
        path: PathLike | None = None,
        exception: BaseException | None = None,
        save_to_json: bool = False,
        use_script_dir: bool = True,
        context: str | None = None,
    ) -> None:
        """Log a critical (fatal-level) message, optionally persisting to JSON.

        Takes the same arguments as :meth:`error`. Use it for failures the
        program cannot recover from (for example right before exiting).
        Output is styled like errors.

        Raises:
            LoggingError: If ``save_to_json=True`` without an ``exception``.

        Example:
            >>> try:
            ...     connect_to_database()
            ... except ConnectionError as exc:
            ...     logger.critical("Database unreachable", exception=exc,
            ...                     save_to_json=True)
            ...     raise SystemExit(1)
        """
        self._log_persisted(
            self.logger.critical, message, error_logger, path, exception,
            save_to_json, use_script_dir, context)

    def exception(
        self,
        message: Any = "Exception occurred!",
        error_logger: ErrorWriter | None = None,
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
            raise LoggingError(
                "logger.exception() must be called inside an `except` block")

        text = str(message)
        if save_to_json:
            saved_to = self._persist(
                exc, error_logger, path, use_script_dir, context)
            text = f"{text}\nSee {saved_to} for details"
        self.logger.error(text, exc_info=True)
