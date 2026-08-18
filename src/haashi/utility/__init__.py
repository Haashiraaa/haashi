# __init__.py
"""
Utility Module for haashi
==============================

Provides utility classes for common operations including logging, file I/O,
screen manipulation, datetime helpers, and performance benchmarking. As of
v2.0.0, benchmarking lives here too - there is no separate `benchmark`
module; everything is in this single `utility` package.

Main Classes:
    Logger: Console logging with multiple log levels and JSON error persistence
    ErrorLogger: JSON-based error logging with automatic rotation
    FileHandler: File operations (JSON, TXT) with validation
    ScreenUtil: Terminal screen manipulation and animations
    DateTimeUtil: Datetime utilities and formatting
    Colors: ANSI color codes and styles for terminal output
    Benchmark: Performance timing and profiling

Custom Exceptions:
    UtilityError: Base exception for utility errors
    FileOperationError: File operation failures
    ClipboardError: Reserved - no clipboard functionality currently implemented
    BenchmarkError: Base exception for benchmark failures
    InvalidFunctionError: Raised when a non-callable is passed to Benchmark
    BenchmarkTimeoutError: Reserved for future timeout handling

Recommended Usage:
    >>> from haashi.utility import Logger, FileHandler, Benchmark
    >>> import logging
    >>>
    >>> logger = Logger(level=logging.INFO)
    >>> file_handler = FileHandler(logger=logger)
    >>>
    >>> logger.info("Processing started")
    >>> data = file_handler.read_json("config.json")
    >>> file_handler.save_json(results, "output.json")
    >>>
    >>> bench = Benchmark(logger=logger)
    >>> avg_time = bench.measure_time(lambda: sum(range(1_000_000)))
"""

# BenchmarkTimeoutError is defined in exceptions.py but never imported into
# utils.py's namespace (only BenchmarkError and InvalidFunctionError are),
# so it has to be pulled in from exceptions.py directly.
from haashi.utility.exceptions import BenchmarkTimeoutError
from haashi.utility.utils import (
    Benchmark,
    BenchmarkError,
    ClipboardError,
    Colors,
    DateTimeUtil,
    ErrorLogger,
    FileHandler,
    FileOperationError,
    InvalidFunctionError,
    Logger,
    ScreenUtil,
    UtilityError,
)

__all__ = [
    # Core classes
    'Logger',
    'ErrorLogger',
    'FileHandler',
    'ScreenUtil',
    'DateTimeUtil',
    'Colors',
    'Benchmark',

    # Exceptions
    'UtilityError',
    'FileOperationError',
    'ClipboardError',
    'BenchmarkError',
    'InvalidFunctionError',
    'BenchmarkTimeoutError',
]

__version__ = '2.0.0'
