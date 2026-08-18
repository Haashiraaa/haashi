

# src/haashi/utility/exceptions.py


"""Custom exceptions for utility-related operations."""


class UtilityError(Exception):
    """Base exception for all utility-related errors."""


class FileOperationError(UtilityError):
    """Raised when file operations fail."""


class BenchmarkError(UtilityError):
    """
    Raised when benchmarking operations fail unexpectedly.
    """


class InvalidFunctionError(UtilityError):
    """
    Raised when provided function is invalid or not callable.

    Example:
        >>> bench = Benchmark()
        >>> bench.measure_time("not a function")
        InvalidFunctionError: Expected callable function, got str
    """


class BenchmarkTimeoutError(UtilityError):
    """
    Raised when benchmark exceeds maximum allowed time.

    This exception can be used in future implementations to handle
    benchmarks that take too long to execute.
    """
