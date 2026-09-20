# src/haashi/utility/exceptions.py

"""Custom exceptions for the utility package."""


class UtilityError(Exception):
    """Base exception for all utility-related errors."""


class FileOperationError(UtilityError):
    """Raised when a file operation (read, write, path creation) fails."""


class InvalidJsonFormatError(UtilityError):
    """Raised when data cannot be represented as valid JSON."""


class LoggingError(UtilityError):
    """Raised when logging is misconfigured or a logging operation is misused.

    Example:
        >>> logger.error("failed", save_to_json=True)  # no exception passed
        LoggingError: save_to_json=True requires an `exception` argument
    """


class BenchmarkError(UtilityError):
    """Raised when a benchmark run fails unexpectedly."""


class InvalidFunctionError(UtilityError):
    """Raised when the object passed to Benchmark is not callable.

    Example:
        >>> Benchmark().measure_time("not a function")
        InvalidFunctionError: Passed function must be callable, got str
    """


class BenchmarkTimeoutError(UtilityError):
    """Reserved for future timeout support in Benchmark."""
