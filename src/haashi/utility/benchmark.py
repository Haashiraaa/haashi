# src/haashi/utility/benchmark.py

"""Function timing with warmup."""

from __future__ import annotations

import logging
import os
import timeit
from collections.abc import Callable, Generator
from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from typing import Any

from .exceptions import BenchmarkError, InvalidFunctionError
from .logger import Logger


class Benchmark:
    """Measure how long a zero-argument function takes.

    Example:
        >>> bench = Benchmark()
        >>> bench.measure_time(lambda: sum(range(1_000_000)), run_times=10)
        0.0234
    """

    def __init__(self, logger: Logger | None = None) -> None:
        """
        Args:
            logger: Optional Logger. The default only shows warnings.
        """
        self.logger = logger or Logger()

    @contextmanager
    def _suppress_output(self) -> Generator[None]:
        """Silence stdout, stderr and logging, restoring the previous state."""
        previous_disable = logging.root.manager.disable
        with open(os.devnull, "w") as null, redirect_stdout(null), redirect_stderr(null):
            logging.disable(logging.CRITICAL)
            try:
                yield
            finally:
                logging.disable(previous_disable)

    @staticmethod
    def _validate_run_times(run_times: int) -> int:
        if run_times < 1:
            raise ValueError(f"run_times must be at least 1, got {run_times}")
        return run_times

    @staticmethod
    def _validate_repeat_times(repeat_times: int) -> int:
        if repeat_times < 1:
            raise ValueError(f"repeat_times must be at least 1, got {repeat_times}")
        return repeat_times

    @staticmethod
    def _validate_warmup_times(warmup_times: int) -> int:
        if warmup_times < 0:
            raise ValueError(f"warmup_times must be 0 or more, got {warmup_times}")
        return warmup_times

    @staticmethod
    def _validate_passed_func(func: object) -> Callable[[], Any]:
        if not callable(func):
            raise InvalidFunctionError(
                f"Passed function must be callable, got {type(func).__name__}")
        return func  # type: ignore[return-value]

    def _warmup(
        self,
        func: Callable[[], Any],
        times: int,
        suppress_output: bool,
    ) -> None:
        """Run ``func`` ``times`` times, untimed, so caches/imports are warm."""
        if times == 0:
            return
        self.logger.debug(f"Warming up function {times} times...")
        ctx = self._suppress_output() if suppress_output else nullcontext()
        with ctx:
            for _ in range(times):
                func()
        self.logger.debug("Warmup complete.")

    def measure_time(
        self,
        func: Callable[[], Any],
        warmup_times: int = 3,
        run_times: int = 5,
        repeat_times: int = 1,
        suppress_output: bool = True,
    ) -> float:
        """Measure the per-call execution time of ``func`` in seconds.

        ``func`` is run ``run_times`` times per batch and the batch is repeated
        ``repeat_times`` times; the fastest batch is reported (the standard
        ``timeit`` approach, which minimizes noise from other processes).

        Args:
            func: Callable taking no arguments.
            warmup_times: Untimed warmup calls (0 to skip).
            run_times: Calls per timed batch (>= 1).
            repeat_times: Number of batches (>= 1).
            suppress_output: Silence stdout/stderr/logging while running.

        Returns:
            Seconds per call, from the fastest batch.

        Raises:
            ValueError: If a count argument is out of range.
            InvalidFunctionError: If ``func`` is not callable.
            BenchmarkError: If ``func`` raises while being measured.
        """
        run_times = self._validate_run_times(run_times)
        repeat_times = self._validate_repeat_times(repeat_times)
        warmup_times = self._validate_warmup_times(warmup_times)
        target = self._validate_passed_func(func)

        try:
            self._warmup(target, warmup_times, suppress_output)
            self.logger.debug(f"Running benchmark {run_times} times...")

            ctx = self._suppress_output() if suppress_output else nullcontext()
            with ctx:
                batches = timeit.repeat(target, number=run_times, repeat=repeat_times)

            per_call = min(batches) / run_times
            self.logger.debug(f"Average execution time: {per_call:.4f} seconds")
            return per_call
        except Exception as exc:
            raise BenchmarkError(f"Failed to benchmark function: {exc}") from exc
