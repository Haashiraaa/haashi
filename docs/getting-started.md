
# Getting started

## Requirements

- Python **3.10 or newer** (tested on 3.10 to 3.14)
- Linux, macOS or Windows
- Nothing else: haashi has **zero runtime dependencies**

## Install

```bash
pip install haashi
python -c "import haashi; print(haashi.__version__)"
```

Development install:

```bash
git clone https://github.com/Haashiraaa/haashi.git
cd haashi
pip install -e ".[dev]"      # pytest, pytest-cov, ruff, pyright, autopep8, build, twine
```

## Imports

Everything public is reachable from one place:

```python
from haashi.utility import (
    Logger, ErrorLogger, JsonlErrorLogger, FileHandler,
    ScreenUtil, DateTime, Colors, Benchmark,
    UtilityError, FileOperationError, InvalidJsonFormatError, LoggingError,
    BenchmarkError, InvalidFunctionError, BenchmarkTimeoutError,
)
```

The async mirror lives in `haashi.aio` (see [Async API](async.md)).

## First script

```python
import logging
from haashi.utility import Logger, FileHandler, Benchmark, DateTime

logger = Logger(level=logging.INFO)
fh = FileHandler(logger=logger)

logger.info("Starting")

fh.save_json({"run": DateTime.get_current_time(1)}, "out/run.json")   # creates out/
print(fh.read_json("out/run.json"))

per_call = Benchmark(logger=logger).measure_time(lambda: sum(range(100_000)), run_times=10)
logger.info(f"{per_call:.6f}s per call")
```

## Persisting errors

```python
try:
    risky()
except Exception as exc:
    logger.error("risky() failed", exception=exc, save_to_json=True, context="startup")
```

This logs to stderr **and** appends a structured entry (timestamp, type, message, context, traceback) to `logs/errors_log.json` next to your script. The console message ends with `See <path> for details`.

Passing `save_to_json=True` without an `exception` raises `LoggingError`; it never silently does nothing.

## First service (async)

```python
from fastapi import FastAPI
from haashi.aio import FileHandler, JsonlErrorLogger

app = FastAPI()
files = FileHandler()
errors = JsonlErrorLogger(log_dir="/var/log/myapp", max_bytes=5_000_000, backups=5)

@app.post("/orders")
async def create_order(order: dict):
    try:
        await files.save_json(order, "/data/orders/latest.json")
    except Exception as exc:
        await errors.log_error(exc, context="POST /orders")
        raise
    return {"ok": True}
```

Always set `log_dir` on servers. Without it, "the script's directory" is your server's entry point, which is rarely what you want. See [Deployment](deployment.md).

## Choosing between the two APIs

| You're writing | Import from |
|---|---|
| Script, CLI, notebook | `haashi.utility` |
| FastAPI, Starlette, aiohttp, asyncio | `haashi.aio` |
| Sync code on a thread pool | `haashi.utility` (thread-safe; see [Architecture](architecture.md#concurrency-matrix)) |

## Next

- Understand the guarantees: [Architecture](architecture.md)
- Pick an error logger: [Error logging](error-logging.md)
