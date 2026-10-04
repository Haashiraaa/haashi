"""
Utility helpers for haashi.

This package provides lightweight, standard-library-only utilities for:
- structured logging and error persistence
- file I/O and script-relative path helpers
- datetime handling
- terminal styling and UI utilities
- benchmarking and function timing

Public exports include:
- ``Logger``, ``ErrorLogger``, ``JsonlErrorLogger``
- ``FileHandler``
- ``DateTime``, ``Colors``, ``ScreenUtil``
- ``Benchmark``
- exception types for file operations, logging, and benchmark failures
"""

from __future__ import annotations

# Defined by hand instead of imported from `typing`: importing `typing` costs
# ~10 ms on its own, more than everything else in this file. Type checkers
# (pyright, mypy) recognise this name exactly like typing.TYPE_CHECKING.
TYPE_CHECKING = False

__all__ = [
    "Logger",
    "ErrorLogger",
    "JsonlErrorLogger",
    "FileHandler",
    "ScreenUtil",
    "DateTime",
    "Colors",
    "Benchmark",
    "UtilityError",
    "FileOperationError",
    "BenchmarkError",
    "InvalidFunctionError",
    "BenchmarkTimeoutError",
    "InvalidJsonFormatError",
    "LoggingError",
]

# public name -> submodule that defines it. Submodules are imported on first
# access, so `import haashi.utility` itself stays as cheap as possible.
# tests/test_lazy_init.py fails if this drifts from __all__ or from the
# TYPE_CHECKING block below.
_LAZY: dict[str, str] = {
    "Logger": ".logger",
    "ErrorLogger": ".logger",
    "JsonlErrorLogger": ".logger",
    "FileHandler": ".filehandler",
    "ScreenUtil": ".uiux",
    "Colors": ".uiux",
    "DateTime": "._datetime",
    "Benchmark": ".benchmark",
    "UtilityError": ".exceptions",
    "FileOperationError": ".exceptions",
    "BenchmarkError": ".exceptions",
    "InvalidFunctionError": ".exceptions",
    "BenchmarkTimeoutError": ".exceptions",
    "InvalidJsonFormatError": ".exceptions",
    "LoggingError": ".exceptions",
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    value = getattr(importlib.import_module(module_name, __name__), name)
    globals()[name] = value  # cache: the next access skips __getattr__
    return value


def __dir__() -> list[str]:
    # Without this, tab-completion and dir() wouldn't show the lazy names.
    return sorted({*globals(), *_LAZY})


if TYPE_CHECKING:
    # Static-analysis-only imports: pyright and IDEs see the real types,
    # but this block never runs.
    from typing import Any

    from ._datetime import DateTime
    from .benchmark import Benchmark
    from .exceptions import (
        BenchmarkError,
        BenchmarkTimeoutError,
        FileOperationError,
        InvalidFunctionError,
        InvalidJsonFormatError,
        LoggingError,
        UtilityError,
    )
    from .filehandler import FileHandler
    from .logger import ErrorLogger, JsonlErrorLogger, Logger
    from .uiux import Colors, ScreenUtil
