# src/haashi/aio/benchmark.py

"""Async Benchmark: same names as ``haashi.utility.Benchmark``."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any

from ..utility.benchmark import Benchmark as _SyncBenchmark
from ..utility.exceptions import BenchmarkError
from ..utility.logger import Logger


class Benchmark:
    """Async twin of :class:`haashi.utility.Benchmark`.

    Times coroutine functions (``await func()`` each run). Plain functions are
    accepted too, but they run on the event loop and block it while timed.

    Example:
        >>> bench = Benchmark()
        >>> async def fetch():
        ...     await asyncio.sleep(0.01)
        >>> await bench.measure_time(fetch, run_times=10)
        0.0101
    """

    def __init__(self, logger: Logger | None = None) -> None:
        self._sync = _SyncBenchmark(logger)
        self.logger = self._sync.logger

    @staticmethod
    async def _call(func: Callable[[], Any]) -> None:
        result = func()
        if inspect.isawaitable(result):
            await result

    async def measure_time(
        self,
        func: Callable[[], Any],
        warmup_times: int = 3,
        run_times: int = 5,
        repeat_times: int = 1,
        suppress_output: bool = False,
    ) -> float:
        """Measure the per-call execution time of ``func`` in seconds.

        Same semantics as the sync version: ``run_times`` calls per batch,
        ``repeat_times`` batches, fastest batch reported.

        ``suppress_output`` defaults to **False** here, unlike the sync
        version. Silencing stdout/stderr/logging is process-wide, so in a
        running server it would also mute every other request while the
        benchmark awaits. Turn it on only in scripts.

        Raises:
            ValueError: If a count argument is out of range.
            InvalidFunctionError: If ``func`` is not callable.
            BenchmarkError: If ``func`` raises while being measured.
        """
        run_times = self._sync._validate_run_times(run_times)
        repeat_times = self._sync._validate_repeat_times(repeat_times)
        warmup_times = self._sync._validate_warmup_times(warmup_times)
        target = self._sync._validate_passed_func(func)

        try:
            ctx = self._sync._suppress_output() if suppress_output else nullcontext()
            with ctx:
                if warmup_times:
                    self.logger.debug(
                        f"Warming up function {warmup_times} times...")
                    for _ in range(warmup_times):
                        await self._call(target)
                    self.logger.debug("Warmup complete.")

                self.logger.debug(f"Running benchmark {run_times} times...")
                batches: list[float] = []
                for _ in range(repeat_times):
                    start = time.perf_counter()
                    for _ in range(run_times):
                        await self._call(target)
                    batches.append(time.perf_counter() - start)

            per_call = min(batches) / run_times
            self.logger.debug(
                f"Average execution time: {per_call:.4f} seconds")
            return per_call
        except Exception as exc:
            raise BenchmarkError(
                f"Failed to benchmark function: {exc}") from exc
