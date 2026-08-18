

# benchmark/benchmark.py


"""Benchmarking and performance profiling utilities."""

import logging
import os
import timeit
from collections.abc import Callable
from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from typing import Any

from haashi_pkg.utility import Logger

from .exceptions import BenchmarkError, InvalidFunctionError


class Benchmark:
    """
    Performance benchmarking and timing utilities.

    Provides methods to measure execution time and profile functions.

    Example:
        >>> from haashi_pkg.benchmark import Benchmark
        >>> 
        >>> bench = Benchmark()
        >>> 
        >>> def my_function():
        ...     return sum(range(1000000))
        >>> 
        >>> avg_time = bench.measure_time(my_function, run_times=10)
        [INFO] Average execution time: 0.0234 seconds
        >>> print(f"Function took {avg_time:.4f}s on average")
        Function took 0.0234s on average
    """

    def __init__(self, logger: Logger | None = None) -> None:
        """
        Initialize Benchmark with optional logger.

        Args:
            logger: Optional Logger instance (default: creates INFO logger)
        """
        self.logger = logger or Logger(level=logging.INFO)

    @contextmanager
    def _suppress_output(self):
        with open(os.devnull, "w") as null:
            with redirect_stdout(null), redirect_stderr(null):
                logging.disable(logging.CRITICAL)
                try:
                    yield
                finally:
                    logging.disable(logging.NOTSET)

    def _warmup(
        self,
        func: Callable[[], Any] | None,
        times: int = 3,
        suppress_output: bool = True,
    ) -> None:
        """
        Warm up a function by running it multiple times.

        This is useful for ensuring the function is optimized and ready for benchmarking.

        Args:
            func: Callable function to warm up (must take no arguments)
            times: Number of times to run the function (default: 3)

        """
        # Validate inputs
        if times < 1:
            raise ValueError(f"times must be at least 1, got {times}")

        if not callable(func):
            raise InvalidFunctionError(
                f"Expected callable function, got {type(func).__name__}"
            )

        self.logger.debug(f"Warming up function {times} times...")

        ctx = self._suppress_output() if suppress_output else nullcontext()
        with ctx:
            for _ in range(times):
                func()

        self.logger.debug("Warmup complete.")

    def measure_time(
        self,
        func: Callable[[], Any] | None,
        warmup_times: int = 3,
        run_times: int = 5,
        repeat_times: int = 1,
        suppress_output: bool = True,
    ) -> float:
        """
        Measure average execution time of a function.

        Runs the function multiple times and returns the average execution time.
        Useful for performance testing and optimization.

        Args:
            func: Callable function to measure (must take no arguments)
            run_times: Number of times to run for averaging (default: 5)

        Returns:
            Average execution time in seconds (float)

        Raises:
            ValueError: If run_times is less than 1
            InvalidFunctionError: If func is not callable
            BenchmarkError: If function execution fails

        Example:
            >>> bench = Benchmark()
            >>> def expensive_operation():
            ...     result = 0
            ...     for i in range(1000000):
            ...         result += i
            ...     return result
            >>> 
            >>> # Measure with default 5 runs
            >>> time_taken = bench.measure_time(expensive_operation)
            [INFO] Average execution time: 0.0456 seconds
            >>> 
            >>> # Measure with 10 runs for better accuracy
            >>> time_taken = bench.measure_time(expensive_operation, run_times=10)
            [INFO] Average execution time: 0.0449 seconds
        """
        # Validate inputs
        if run_times < 1:
            raise ValueError(f"run_times must be at least 1, got {run_times}")
        if repeat_times < 1:
            raise ValueError(
                f"repeat_times must be at least 1, got {repeat_times}")

        if not callable(func):
            raise InvalidFunctionError(
                f"Expected callable function, got {type(func).__name__}"
            )

        try:

            # Warm up the function
            self._warmup(
                func, times=warmup_times, suppress_output=suppress_output)

            self.logger.debug(f"Running benchmark {run_times} times...")

            # Use timeit for accurate timing

            ctx = self._suppress_output() if suppress_output else nullcontext()
            with ctx:
                times = timeit.repeat(
                    func, number=run_times, repeat=repeat_times)

            average_time = min(times) / run_times

            self.logger.debug(
                f"Average execution time: {average_time:.4f} seconds")

            return average_time

        except InvalidFunctionError:
            # Re-raise our custom exception
            raise

        except Exception as e:
            error_msg = f"Failed to benchmark function: {e!s}"
            self.logger.error(error_msg)
            raise BenchmarkError(error_msg) from e
