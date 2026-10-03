# src/haashi/aio/__init__.py

"""
Async API for haashi
====================

The same class and method names as :mod:`haashi.utility`, but every method that
touches the disk is awaitable and runs in a worker thread, so it never blocks
your event loop (FastAPI, aiohttp, Starlette, plain ``asyncio``...).

Import from here instead of ``haashi.utility``::

    from haashi.aio import FileHandler, ErrorLogger, Logger

    fh = FileHandler()
    await fh.save_json({"status": "ok"}, "data/output.json")

What is async:
    FileHandler, ErrorLogger, Benchmark  (disk IO / timing of coroutines)

What is re-exported unchanged (already fast and safe in async code):
    Logger, DateTime, Colors and all exceptions. ``Logger`` methods are plain
    calls: logging a line does not need ``await``.

Nothing here adds dependencies; it is built on ``asyncio.to_thread``.
"""

from __future__ import annotations

from ..utility._datetime import DateTime
from ..utility.exceptions import (
    BenchmarkError,
    BenchmarkTimeoutError,
    FileOperationError,
    InvalidFunctionError,
    InvalidJsonFormatError,
    LoggingError,
    UtilityError,
)
from ..utility.logger import Logger
from ..utility.uiux import Colors
from .benchmark import Benchmark
from .errorlogger import ErrorLogger
from .jsonl_errorlogger import JsonlErrorLogger
from .filehandler import FileHandler

__all__ = [
    "FileHandler",
    "ErrorLogger",
    "JsonlErrorLogger",
    "Benchmark",
    "Logger",
    "DateTime",
    "Colors",
    "UtilityError",
    "FileOperationError",
    "InvalidJsonFormatError",
    "LoggingError",
    "BenchmarkError",
    "InvalidFunctionError",
    "BenchmarkTimeoutError",
]
