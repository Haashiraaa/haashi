

# benchmark/exceptions.py


"""Custom exceptions for benchmark module."""


class BenchmarkError(Exception):
    """
    Base exception for benchmark-related errors.

    Raised when benchmarking operations fail unexpectedly.
    """


class InvalidFunctionError(BenchmarkError):
    """
    Raised when provided function is invalid or not callable.

    Example:
        >>> bench = Benchmark()
        >>> bench.measure_time("not a function")
        InvalidFunctionError: Expected callable function, got str
    """


class BenchmarkTimeoutError(BenchmarkError):
    """
    Raised when benchmark exceeds maximum allowed time.

    This exception can be used in future implementations to handle
    benchmarks that take too long to execute.
    """
