# haashi

**A lightweight, dependency-free Python utility toolkit** — structured logging, file I/O, terminal helpers, datetime utilities, and performance benchmarking.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-green)](https://github.com/Haashiraaa/haashi)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)

**Version:** 2.0.0
**Author:** Haashiraaa
**Python:** ≥ 3.10
**Runtime dependencies:** none — standard library only

---

## Overview

`haashi` is the successor to `haashi_pkg`. As of v2.0.0 it's been rewritten as a focused, zero-dependency utility toolkit: everything for logging, file I/O, terminal output, datetime handling, and benchmarking, and nothing else.

**Perfect for:**
- CLI tools and scripts where startup time matters
- Serverless / Lambda functions with cold-start sensitivity
- Any project that wants structured logging and file helpers without dragging in a data-science stack
- Quick performance profiling of arbitrary functions

**Key principles:**
- **Zero runtime dependencies** — nothing to resolve, nothing to conflict with your own pins
- **Fast import** — see [Why it's fast](#why-its-fast) below
- **Robust error handling** — a small, flat custom exception hierarchy with clear messages
- **Type-safe** — full type hints throughout
- **Comprehensive documentation** — every public method has a docstring with examples

> **Looking for `DataAnalyzer`, `DataLoader`, `DataSaver`, `PlotEngine`, `QuickPlot`, or `PowerCanvas`?**
> Those lived in `haashi_pkg`'s `data_engine` and `plot_engine` modules and were **not** carried forward into `haashi`. If you depend on them, stay on `haashi_pkg<2.0` — it still installs and works, it just won't receive further feature updates. See [Migrating from haashi_pkg](#migrating-from-haashi_pkg) below.

---

## Package Structure

```
haashi/
└── utility/
    ├── utils.py        # Logger, ErrorLogger, FileHandler, ScreenUtil, DateTimeUtil, Colors, Benchmark
    └── exceptions.py   # UtilityError, FileOperationError, BenchmarkError,
                         # InvalidFunctionError, BenchmarkTimeoutError
```

Everything is re-exported from `haashi.utility`, so a single import line covers the whole toolkit:

```python
from haashi.utility import Logger, FileHandler, ScreenUtil, DateTimeUtil, Colors, Benchmark
```

---

## Installation

```bash
pip install haashi
```

Optional dev dependencies (for contributing):

```bash
pip install "haashi[dev]"   # pytest, pytest-cov, ruff, pyright, autopep8
```

There are no runtime dependencies to worry about — `haashi` only touches the Python standard library.

---

## Features by Class

### **Logger**
Console logging with multiple levels (`debug`, `info`, `warning`, `error`), backed by an `ErrorLogger` that can persist errors to a rotating JSON file.

```python
from haashi.utility import Logger
import logging

logger = Logger(level=logging.INFO)
logger.info("Processing started")

try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exception=e, save_to_json=True, context="data_load")
```

### **FileHandler**
JSON/TXT read-write with path validation, plus script-relative path helpers that work no matter where the script is invoked from.

```python
from haashi.utility import FileHandler

fh = FileHandler(logger=logger)
fh.save_json({"status": "ok"}, "data/output.json")
data = fh.read_json("data/output.json")

# Find a path relative to wherever *your* script lives, not the cwd
project_root = fh.get_ancestor_by_name("my-project")
```

### **ScreenUtil**
Terminal clearing, loading animations, interactive pauses, and text wrapping.

```python
from haashi.utility import ScreenUtil

ScreenUtil.animate("Processing", cycles=3, delay=0.3)
ScreenUtil.wait_and_enter("Review the output above, then press Enter...")
```

### **DateTimeUtil**
UTC-based current time with configurable timezone offset and string/datetime output.

```python
from haashi.utility import DateTimeUtil

DateTimeUtil.get_current_time(utc_offset_hours=1, only_date=False)
# '2026-08-20 14:03:11'
```

### **Colors**
ANSI terminal colors and styles, with convenience wrappers for common message types.

```python
from haashi.utility import Colors

print(Colors.success("Build passed!"))
print(Colors.error("3 tests failed"))
```

### **Benchmark**
Warms up a function, then times it with `timeit` for a stable average.

```python
from haashi.utility import Benchmark

bench = Benchmark()

def my_function():
    return sum(range(1_000_000))

avg_time = bench.measure_time(my_function, run_times=10)
print(f"Average: {avg_time:.4f}s")
```

---

## Exception Hierarchy

All custom exceptions inherit directly from `UtilityError`, so you can catch broadly or narrowly:

```python
UtilityError                   # Base exception for everything in haashi.utility
├── FileOperationError         # FileHandler read/write/path failures
├── BenchmarkError             # Benchmark execution failures
├── InvalidFunctionError       # A non-callable was passed to Benchmark
└── BenchmarkTimeoutError      # Reserved for future timeout support
```

```python
from haashi.utility import Benchmark, InvalidFunctionError

bench = Benchmark()
try:
    bench.measure_time("not a function")
except InvalidFunctionError as e:
    print(f"Bad input: {e}")
```

---

## Why It's Fast

`haashi` imports only the standard library. Measured on the same machine, launching a fresh Python process and importing each dependency set:

| Import set | Median wall time |
|---|---|
| Bare Python startup | ~11 ms |
| `haashi`-style import (stdlib only) | ~37 ms |
| Old `haashi_pkg`-style import (pandas, numpy, matplotlib, seaborn, openpyxl) | ~1,260 ms |

That's roughly **34x faster**, or about 1.2 seconds saved per process start — real time on every CLI invocation, every cold serverless start, and every test collection run. Numbers are from repeated subprocess launches of each dependency set on one machine, not a formal cross-platform benchmark suite; run your own `python -X importtime` comparison if it matters for your deployment target.

---

## Migrating from haashi_pkg

| Before (`haashi_pkg`) | After (`haashi` v2.0.0) |
|---|---|
| `from haashi_pkg.utility import Logger` | `from haashi.utility import Logger` |
| `from haashi_pkg.benchmark import Benchmark` | `from haashi.utility import Benchmark` |
| `from haashi_pkg.data_engine import DataAnalyzer, DataLoader, DataSaver` | **Removed.** No successor exists in `haashi`. Stay on `haashi_pkg<2.0`. |
| `from haashi_pkg.plot_engine import PlotEngine, QuickPlot, PowerCanvas` | **Removed.** No successor exists in `haashi`. Stay on `haashi_pkg<2.0`. |
| `from haashi_pkg.utility import Utility` (legacy wrapper) | **Removed.** Use `Logger`, `FileHandler`, `ScreenUtil`, `DateTimeUtil` directly. |
| `from haashi_pkg.utility import ClipboardUtil` | **Removed.** No replacement. |

If you only ever used `Logger`, `FileHandler`, `ScreenUtil`, `DateTimeUtil`, `Colors`, or `Benchmark`, migration is a straight import-path swap and a `pip uninstall haashi_pkg && pip install haashi`.

If you rely on `data_engine` or `plot_engine`, **do not upgrade** — pin `haashi_pkg<2.0` and keep using it as-is. It will keep working; it just won't gain new features.

---

## Contributing

Contributions welcome! Please ensure:

- **Documentation**: docstrings for all public functions, with examples
- **Type hints**: full type annotations
- **Error handling**: raise the appropriate custom exception, don't print-and-swallow
- **Tests**: cover new features (`pytest`)
- **Non-mutating**: don't modify inputs unless explicitly documented
- **Zero new dependencies**: `haashi` is dependency-free by design — if a contribution needs a third-party package, discuss it in an issue first

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Haashiraaa/haashi/issues)
- **Documentation**: [README](https://github.com/Haashiraaa/haashi/blob/main/README.md)
- **Repository**: [GitHub](https://github.com/Haashiraaa/haashi)
- **Legacy package** (`data_engine` / `plot_engine`, pandas-based): [haashi_pkg on GitHub](https://github.com/Haashiraaa/haashi-analytics-toolkit)

---

**Made with ❤️ by Haashiraaa**
