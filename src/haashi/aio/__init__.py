"""
Async API for haashi.

This package mirrors the synchronous ``haashi.utility`` API while making
filesystem-heavy operations awaitable. Methods that touch the disk are
executed in worker threads via ``asyncio.to_thread``, which keeps the event
loop responsive during I/O-bound work.

Public exports include:
- ``FileHandler``, ``ErrorLogger``, ``JsonlErrorLogger``, ``Benchmark``
- ``Logger``, ``DateTime``, ``Colors``
- exception types re-exported from the sync package
"""

from __future__ import annotations

TYPE_CHECKING = False

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

_LAZY: dict[str, str] = {
    "FileHandler": ".filehandler",
    "ErrorLogger": ".errorlogger",
    "JsonlErrorLogger": ".jsonl_errorlogger",
    "Benchmark": ".benchmark",
    "Logger": "..utility.logger",
    "DateTime": "..utility._datetime",
    "Colors": "..utility.uiux",
    "UtilityError": "..utility.exceptions",
    "FileOperationError": "..utility.exceptions",
    "InvalidJsonFormatError": "..utility.exceptions",
    "LoggingError": "..utility.exceptions",
    "BenchmarkError": "..utility.exceptions",
    "InvalidFunctionError": "..utility.exceptions",
    "BenchmarkTimeoutError": "..utility.exceptions",
}


def __getattr__(name: str) -> object:
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    value = getattr(importlib.import_module(module_name, __name__), name)
    globals()[name] = value  # cache: the next access skips __getattr__
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY})


if TYPE_CHECKING:
    from typing import Any  # noqa: F401 # type: ignore

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
    from .filehandler import FileHandler
    from .jsonl_errorlogger import JsonlErrorLogger
