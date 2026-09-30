# haashi

**A lightweight, dependency-free Python utility toolkit**: structured logging, file I/O, terminal helpers, datetime utilities and performance benchmarking, with a matching async API.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)
[![Typed](https://img.shields.io/badge/typing-py.typed-informational)](src/haashi/py.typed)

**Author:** Haashiraaa
**Python:** 3.10 to 3.14
**Runtime dependencies:** none (standard library only)

> **Full documentation:** [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md): a complete guide and reference with recipes, troubleshooting and an API cheat sheet.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Package Structure](#package-structure)
- [Features](#features)
  - [Logger](#logger) · [ErrorLogger](#errorlogger) · [FileHandler](#filehandler) · [DateTime](#datetime) · [ScreenUtil and Colors](#screenutil-and-colors) · [Benchmark](#benchmark)
- [Backend and async usage](#backend-and-async-usage)
- [Reliability](#reliability)
- [Exception Hierarchy](#exception-hierarchy)
- [Import Cost](#import-cost)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

`haashi` is a focused toolkit for the small things almost every script needs: logging, file I/O, terminal output, datetime handling and benchmarking, with nothing to install besides `haashi` itself.

**Perfect for:**
- CLI tools and scripts where startup time matters
- Backend services (FastAPI, aiohttp, asyncio) that need safe, non-blocking file I/O
- Serverless functions with cold-start sensitivity
- Any project that wants structured logging and file helpers without a heavy dependency tree
- Quick performance profiling of arbitrary functions

**Key principles:**
- **Zero runtime dependencies**: nothing to resolve, nothing to conflict with your own pins
- **Lazy loading**: importing `haashi.utility` loads nothing; each submodule is imported the first time you use a class from it
- **A good citizen**: never configures the root logger or touches your app's logging setup
- **Safe by default**: atomic file writes, validated input, thread-safe error logging
- **Robust error handling**: a small, flat exception hierarchy with clear messages
- **Typed**: full type hints, checked with pyright in strict mode, and a `py.typed` marker

---

## Installation

```bash
pip install haashi
```

Everything is available from one import:

```python
from haashi.utility import (
    Logger, ErrorLogger, FileHandler, ScreenUtil, DateTime, Colors, Benchmark,
)
```

For development: `pip install "haashi[dev]"` (pytest, pytest-cov, ruff, pyright, autopep8, build, twine).

---

## Package Structure

```
haashi/
├── __init__.py             # __version__ (single source of truth)
├── py.typed                # PEP 561 typing marker
├── utility/                # sync API (scripts, CLIs)
│   ├── __init__.py         # lazy loader for the names below
│   ├── logger.py           # Logger, ErrorLogger
│   ├── filehandler.py      # FileHandler
│   ├── benchmark.py        # Benchmark
│   ├── uiux.py             # ScreenUtil, Colors
│   ├── _datetime.py        # DateTime
│   ├── exceptions.py       # UtilityError and subclasses
│   ├── _atomic.py          # crash-safe file writes (internal)
│   ├── _paths.py           # script-directory detection (internal)
│   └── _types.py           # PathLike, JSONType, JSON helpers (internal)
└── aio/                    # async API (FastAPI, aiohttp, asyncio): same names
    ├── __init__.py
    ├── filehandler.py      # FileHandler
    ├── errorlogger.py      # ErrorLogger
    └── benchmark.py        # Benchmark
```

---

## Features

### Logger

Console logging with `debug` / `info` / `warning` / `error` / `critical`, plus `exception()` for logging the exception you're currently handling. Each `Logger` instance is independent, and nothing is configured on the root logger. Output goes to stderr as `[LEVEL] message`.

Output is colored by level using the [`Colors`](#screenutil-and-colors) class (debug cyan, info blue, warning yellow, error and critical red), but only when writing to a terminal. In files, pipes and CI it is plain text, and the [`NO_COLOR`](https://no-color.org) environment variable is respected. Pass `color=True` or `color=False` to force it either way.

```python
import logging
from haashi.utility import Logger

logger = Logger(level=logging.INFO)   # Logger(level, color=None, error_logger=None)
logger.info("Processing started")

try:
    risky_operation()
except Exception as exc:
    # Console + persisted to logs/errors_log.json (next to your script)
    logger.error("Operation failed", exception=exc, save_to_json=True, context="data_load")

try:
    risky_operation()
except Exception:
    logger.exception("risky_operation() failed")   # includes the traceback

logger.critical("Database unreachable")            # same arguments as error()
```

`save_to_json=True` without an `exception` raises `LoggingError` rather than silently doing nothing.

### ErrorLogger

The rotating JSON error log behind `Logger`. `log_error`, `view_error_entries` and `clear_errors` all resolve the file the same way, so what you write is what you read and clear.

```python
from haashi.utility import ErrorLogger

errors = ErrorLogger()                           # or ErrorLogger(log_dir="/var/log/myapp")
try:
    1 / 0
except ZeroDivisionError as exc:
    path = errors.log_error(exc, context="math", utc_offset_hours=1, max_entries=100)
    # `path` is the file that was written

recent = errors.view_error_entries(limit=5)      # limit=None for everything
errors.clear_errors(confirm=False)               # confirm=True prompts (interactive only)
```

**Where the log goes.** With no `log_dir`, relative paths resolve next to the running script (default `logs/errors_log.json`). If the script lives in an installed location (site-packages or a scripts/bin directory, as with console scripts or `python -m pytest`) or there is no script at all (REPL), the current directory is used instead. With `log_dir` set, relative paths resolve under it. An absolute `path` is always used as given. See [Backend and async usage](#backend-and-async-usage).

**Corrupted logs are never overwritten.** If the log can't be parsed, it is moved to `<name>.corrupt` (or `.corrupt.1`, ...), a `RuntimeWarning` is emitted, and a fresh log starts. This also applies when reading with `view_error_entries`.

**Entry format:** `timestamp` (ISO 8601 with UTC offset), `type`, `message`, `context`, `traceback`.

> **Note:** each `log_error` call rewrites the log file and `fsync`s it, under a process-wide lock. That is ideal for occasional errors, but it is not a high-volume logger. For error storms, log to the console (or a proper log shipper) and persist only the ones you need to keep.

### FileHandler

JSON/TXT read-write. Data is validated *before* anything touches disk, and `str`, `Path` and any `os.PathLike` are accepted. Also includes helpers that find paths relative to your script rather than the current directory.

```python
from haashi.utility import FileHandler

fh = FileHandler()
fh.save_json({"status": "ok"}, "data/output.json")   # creates data/ if needed
data = fh.read_json("data/output.json")

fh.save_txt("first line", "notes.txt")
fh.save_txt("\nmore", "notes.txt", mode="a")

fh.ensure_writable_path("out/report.txt")            # creates parents, returns a Path
fh.ensure_readable_file("out/report.txt")            # raises if missing / not a file

project_root = fh.get_ancestor_by_name("my-project")   # Path or None
script_dir = fh.get_script_dir()
```

- `save_json` and `save_txt(mode="w")` are **atomic**: a crash mid-write can't leave a truncated file. `save_txt(mode="a")` is a plain append and is not atomic.
- `save_json` is strict JSON: sets, custom objects and `NaN`/`Infinity` raise `InvalidJsonFormatError` and nothing is written. Non-ASCII text is stored escaped and round-trips exactly.
- `get_script_dir()` follows the same rules as the error log (installed locations and REPLs fall back to the current directory).

### DateTime

Timezone-aware "now" at a fixed UTC offset (-12 to +14, fractions allowed). No time-zone names or daylight-saving handling; use `zoneinfo` for those.

```python
from haashi.utility import DateTime

DateTime.get_current_time(utc_offset_hours=1)                    # '2026-09-19'
DateTime.get_current_time(5.5, only_date=False)                  # '2026-09-19 22:41:07'
DateTime.get_current_time(1, string_format=False)                # aware datetime
```

### ScreenUtil and Colors

```python
from haashi.utility import Colors, ScreenUtil

ScreenUtil.animate("Processing", cycles=3, delay=0.3)
print(ScreenUtil.format_text(long_text, width=60))

print(Colors.success("Build passed!"))
print(Colors.error("3 tests failed"))
print(f"{Colors.CYAN}custom{Colors.RESET}")
```

`Colors` has helpers for `debug`, `info`, `warning`, `error`, `success` and `header`, plus raw codes (`RED`, `BOLD`, `BG_BLUE`, ...). `Colors` always emits ANSI codes; only `Logger` auto-detects terminals and `NO_COLOR`.

### Benchmark

Warms up a function, then times it with `timeit` and reports seconds per call from the fastest batch.

```python
from haashi.utility import Benchmark

bench = Benchmark()

def my_function():
    return sum(range(1_000_000))

seconds = bench.measure_time(my_function, run_times=10, repeat_times=3)
print(f"{seconds:.4f}s per call")
```

Output from the function is suppressed while timing (`suppress_output=False` to keep it), and any logging state you had before is restored afterwards. Suppression is **process-wide** (it redirects stdout/stderr and disables logging), so avoid it in multi-threaded programs. If the function raises, you get a `BenchmarkError` with the original chained.

---

## Backend and async usage

`haashi.aio` has the **same class and method names** as `haashi.utility`. The difference is that anything touching the disk is `await`-able and runs in a worker thread, so it never blocks your event loop. Nothing is added to the dependency list.

```python
# scripts / CLI (sync)
from haashi.utility import FileHandler
FileHandler().save_json(data, "x.json")
```

```python
# FastAPI, aiohttp, asyncio (async): same names, just await
from haashi.aio import FileHandler
await FileHandler().save_json(data, "x.json")
```

```python
from fastapi import FastAPI
from haashi.aio import ErrorLogger, FileHandler, Logger

app = FastAPI()
logger = Logger()
errors = ErrorLogger(log_dir="/var/log/myapp")     # you choose where logs live
files = FileHandler()

@app.post("/orders")
async def create_order(order: dict):
    try:
        await files.save_json(order, "/data/orders/latest.json")
    except Exception as exc:
        await errors.log_error(exc, context="POST /orders")
        raise
```

| Class | In `haashi.aio` | Notes |
|---|---|---|
| `FileHandler` | async `save_json`, `read_json`, `save_txt`, `read_txt`, `ensure_*` | Path helpers (`get_script_dir`, `get_parent_path`, `get_ancestor_by_name`) stay sync: no IO to await. |
| `ErrorLogger` | async `log_error`, `view_error_entries`, `clear_errors` | Thread-safe. Pass `confirm=False` to `clear_errors` on servers. |
| `Benchmark` | async `measure_time` for coroutine functions | `suppress_output` defaults to `False` (silencing output is process-wide). |
| `Logger`, `DateTime`, `Colors`, exceptions | re-exported unchanged | Logging a line is fast; it needs no `await`. |

**Choosing where error logs go.** By default `ErrorLogger` writes next to the running script. That is convenient for scripts but wrong for servers (under uvicorn/gunicorn "the script" is the server's own entry point). Pass `log_dir`:

```python
ErrorLogger(log_dir="/var/log/myapp")     # logs/errors go to /var/log/myapp/errors_log.json
ErrorLogger(log_dir="~/myapp-logs")       # "~" is expanded
Logger(error_logger=ErrorLogger(log_dir="/var/log/myapp"))   # default for save_to_json=True
```

Relative paths resolve under `log_dir`; an absolute `path` is always used as given. Files are written atomically and guarded by a lock, so many concurrent requests can log errors without losing entries. (Several *processes* writing one file, such as multiple gunicorn workers, need one `log_dir` per worker or an external log shipper.)

**Serverless / read-only filesystems.** The default log location is usually read-only on AWS Lambda. Use the temp directory, and send important errors to your platform's own logging too:

```python
ErrorLogger(log_dir="/tmp/logs")
```

---

## Reliability

| Guarantee | Detail |
|---|---|
| Atomic writes | JSON, `save_txt(mode="w")` and the error log are written to a temp file, fsynced, then swapped in. Failures leave the original intact. |
| Thread-safe error log | One process-wide lock guards every read-modify-write. No lost entries under concurrency. |
| No global state leaks | `Logger` instances are not added to Python's global logger registry, so creating one per request is safe. |
| Corruption-safe | A corrupt error log is moved to `<name>.corrupt`, never overwritten. |
| Validate first | Invalid data is rejected before any file is touched. |

**Known limits:** multiple *processes* writing one error log are not coordinated; `save_txt(mode="a")` is not atomic; `Benchmark(suppress_output=True)` is process-wide.

---

## Exception Hierarchy

Everything inherits from `UtilityError`, so you can catch broadly or narrowly:

```
UtilityError
├── FileOperationError        # FileHandler read/write/path failures
├── InvalidJsonFormatError    # data can't be represented as JSON
├── LoggingError              # Logger/ErrorLogger misuse
├── BenchmarkError            # the benchmarked function raised
├── InvalidFunctionError      # a non-callable was passed to Benchmark
└── BenchmarkTimeoutError     # reserved for future timeout support
```

Missing files raise the built-in `FileNotFoundError`, and bad arguments raise `ValueError`, as you'd expect.

---

## Import Cost

`haashi` imports only the standard library, and `haashi.utility` loads its submodules lazily, so you only pay for what you use. Importing `haashi` does not import `asyncio` or `typing`; the async cost is opt-in via `haashi.aio`. To measure it on your own machine:

```bash
python -X importtime -c "import haashi" 2> imports.txt && tail -n 3 imports.txt
```

---

## Contributing

```bash
git clone https://github.com/Haashiraaa/haashi.git
cd haashi
pip install -e ".[dev]"
ruff check . && pyright && pytest
```

Please make sure contributions include:

- **Tests** for new behavior (`pytest`)
- **Type hints**: pyright runs in strict mode on `src/`
- **Docstrings** on public functions, with an example where it helps
- **Appropriate exceptions**: raise a `UtilityError` subclass; don't print-and-swallow
- **No new runtime dependencies**: `haashi` is dependency-free by design; discuss in an issue first
- **Async parity**: if a class in `haashi.utility` has an async twin in `haashi.aio`, keep their methods and signatures in step (a test enforces this)

Releasing is documented in [RELEASING.md](RELEASING.md).

---

## License

MIT, see [LICENSE](LICENSE).

## Support

- **Documentation:** [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Issues:** [GitHub Issues](https://github.com/Haashiraaa/haashi/issues)
- **Repository:** [GitHub](https://github.com/Haashiraaa/haashi)

**Made with ❤️ by Haashiraaa**
