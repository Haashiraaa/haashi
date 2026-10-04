
# test/aio/helpers.py

"""Shared helpers for the tests in the aio package."""

import inspect

from haashi import aio
from haashi.utility import Benchmark as SyncBenchmark
from haashi.utility import ErrorLogger as SyncErrorLogger
from haashi.utility import FileHandler as SyncFileHandler
from haashi.utility import JsonlErrorLogger as SyncJsonlErrorLogger

# name -> parameters whose defaults intentionally differ from the sync class
EXPECTED_DIFFERENCES = {
    # default False in async
    ("Benchmark", "measure_time"): {"suppress_output"},
}

PAIRS = [
    ("FileHandler", SyncFileHandler, aio.FileHandler),
    ("ErrorLogger", SyncErrorLogger, aio.ErrorLogger),
    ("Benchmark", SyncBenchmark, aio.Benchmark),
    ("JsonlErrorLogger", SyncJsonlErrorLogger, aio.JsonlErrorLogger),
]


def _public_methods(cls: type) -> set[str]:
    return {
        n for n, v in vars(cls).items()
        if not n.startswith("_") and (inspect.isfunction(v) or isinstance(v, staticmethod))
    }
