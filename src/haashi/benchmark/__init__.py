

# src/haashi/benchmark/__init__.py


"""Benchmarking and performance profiling utilities."""

from .benchmark import Benchmark
from .exceptions import BenchmarkError, BenchmarkTimeoutError, InvalidFunctionError

__all__ = [
    'Benchmark',
    'BenchmarkError',
    'BenchmarkTimeoutError',
    'InvalidFunctionError'
]


__version__ = '1.5.0'
