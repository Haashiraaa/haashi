# haashi

**A lightweight, dependency-free Python utility toolkit** — structured logging, file I/O, terminal helpers, datetime utilities, and performance benchmarking.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)
[![Typed](https://img.shields.io/badge/typing-py.typed-informational)](src/haashi/py.typed)

**Author:** Haashiraaa
**Python:** ≥ 3.10
**Runtime dependencies:** none — standard library only

---

## Overview

`haashi` is a focused toolkit for the small things almost every script needs: logging, file I/O, terminal output, datetime handling, and benchmarking — with nothing to install besides `haashi` itself.

**Perfect for:**
- CLI tools and scripts where startup time matters
- Serverless / Lambda functions with cold-start sensitivity
- Any project that wants structured logging and file helpers without a heavy dependency tree
- Quick performance profiling of arbitrary functions

**Key principles:**
- **Zero runtime dependencies** — nothing to resolve, nothing to conflict with your own pins
- **Lazy loading** — importing `haashi.utility` loads nothing; each submodule is imported the first time you use a class from it
- **A good citizen** — never configures the root logger or touches your app's logging setup
- **Robust error handling** — a small, flat exception hierarchy with clear messages
- **Typed** — full type hints, checked with pyright in strict mode, and a `py.typed` marker

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

For development: `pip install "haashi[dev]"` (pytest, ruff, pyright, build).

---

## Package Structure

```
haashi/
└── utility/
    ├── logger.py       # Logger, ErrorLogger
    ├── filehandler.py  # FileHandler
    ├── benchmark.py    # Benchmark
    ├── uiux.py         # ScreenUtil, Colors
    ├── _datetime.py    # DateTime
    └── exceptions.py   # UtilityError and subclasses
```

---

## Features

### Logger

Console logging with `debug` / `info` / `warning` / `error`, plus `exception()` for logging the exception you're currently handling. Each `Logger` instance is independent, and nothing is configured on the root logger.

Output is colored by level using the [`Colors`](#screenutil-and-colors) class — debug cyan, info blue, warning yellow, error red — but only when writing to a terminal. In files, pipes and CI it is plain text, and the [`NO_COLOR`](https://no-color.org) environment variable is respected. Pass `color=True` or `color=False` to force it either way.

```python
import logging
from haashi.utility import Logger

logger = Logger(level=logging.INFO)          # Logger(level, color=None)
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
```

`save_to_json=True` without an `exception` raises `LoggingError` rather than silently doing nothing.

### ErrorLogger

The rotating JSON error log behind `Logger`. `log_error`, `view_error_entries` and `clear_errors` all resolve the file the same way, so what you write is what you read and clear.

```python
from haashi.utility import ErrorLogger

errors = ErrorLogger()
try:
    1 / 0
except ZeroDivisionError as exc:
    errors.log_error(exc, context="math", utc_offset_hours=1, max_entries=100)

recent = errors.view_error_entries(limit=5)      # limit=None for everything
errors.clear_errors(confirm=False)               # confirm=True prompts (interactive only)
```

A corrupted log file emits a `RuntimeWarning` and starts fresh instead of crashing your app.

### FileHandler

JSON/TXT read-write. Data is validated *before* anything touches disk, and `str`, `Path` and any `os.PathLike` are accepted. Also includes helpers that find paths relative to your script rather than the current directory.

```python
from haashi.utility import FileHandler

fh = FileHandler()
fh.save_json({"status": "ok"}, "data/output.json")   # creates data/ if needed
data = fh.read_json("data/output.json")

fh.save_txt("first line", "notes.txt")
fh.save_txt("more", "notes.txt", mode="a")

project_root = fh.get_ancestor_by_name("my-project")   # Path or None
script_dir = fh.get_script_dir()
```

### DateTime

Timezone-aware "now" at a fixed UTC offset (−12 to +14, fractions allowed).

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

`Colors` has helpers for `debug`, `info`, `warning`, `error`, `success` and `header`, plus raw codes (`RED`, `BOLD`, `BG_BLUE`, ...).

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

Output from the function is suppressed while timing (`suppress_output=False` to keep it), and any logging state you had before is restored afterwards.

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

`haashi` imports only the standard library, and `haashi.utility` loads its submodules lazily, so you only pay for what you use. To measure it on your own machine:

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
- **Type hints** — pyright runs in strict mode on `src/`
- **Docstrings** on public functions, with an example where it helps
- **Appropriate exceptions** — raise a `UtilityError` subclass; don't print-and-swallow
- **No new runtime dependencies** — `haashi` is dependency-free by design; discuss in an issue first

Releasing is documented in [RELEASING.md](RELEASING.md).

---

## License

MIT — see [LICENSE](LICENSE).

## Support

- **Issues:** [GitHub Issues](https://github.com/Haashiraaa/haashi/issues)
- **Repository:** [GitHub](https://github.com/Haashiraaa/haashi)

**Made with ❤️ by Haashiraaa**
