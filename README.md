
# haashi

**The small utility toolkit that doesn't break in production.**
Logging, file I/O, error persistence, terminal helpers and benchmarking, with zero dependencies and a matching async API.

[![PyPI](https://img.shields.io/pypi/v/haashi)](https://pypi.org/project/haashi/)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.14-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)
[![Typed](https://img.shields.io/badge/typing-strict%20%2B%20py.typed-informational)](src/haashi/py.typed)

```bash
pip install haashi
```

---

## Why haashi?

Every project rewrites the same helpers: a logger that doesn't hijack your app, JSON writes that don't corrupt on a crash, an error log that survives load. haashi ships those helpers once, and ships them **correct**.

| You need | haashi gives you |
|---|---|
| Files that never end up half-written | **Atomic writes.** A crash mid-save leaves the old file intact. |
| An error log that doesn't lose entries | **Thread-safe** `ErrorLogger`, and **multi-process-safe** `JsonlErrorLogger` for gunicorn/uvicorn workers. |
| Logs that stay readable at scale | Append-only JSONL with **size-based rotation**; cost stays flat as the log grows. |
| A logger that plays nice | Independent instances, never touches the root logger, no registry leaks. Safe to create per request. |
| Async without a rewrite | `haashi.aio`: **same names**, awaitable, never blocks the event loop. |
| Fast startup (CLIs, Lambda) | **Lazy loading**, standard library only. `import haashi` costs about a bare interpreter. |
| Types you can trust | Full hints, **pyright strict**, `py.typed` shipped. |
| Nothing to conflict with | **Zero runtime dependencies.** |

---

## 30-second tour

```python
import logging
from haashi.utility import Logger, FileHandler, Benchmark

logger = Logger(level=logging.INFO)
fh = FileHandler(logger=logger)

# Atomic, validated JSON: bad data is rejected before touching disk
fh.save_json({"status": "ok", "items": [1, 2, 3]}, "out/result.json")

# Colored on a terminal, plain in files and CI, honors NO_COLOR
logger.info("saved")

# Know what's slow
seconds = Benchmark(logger=logger).measure_time(lambda: sum(range(1_000_000)), run_times=10)
```

**Errors that survive anything:**

```python
try:
    process_order()
except Exception as exc:
    # Console + persisted JSON entry with full traceback
    logger.error("Order failed", exception=exc, save_to_json=True, context="orders")
```

**Backend with several workers sharing one log:**

```python
from haashi.utility import Logger, JsonlErrorLogger

errors = JsonlErrorLogger("/var/log/myapp", max_bytes=5_000_000, backups=5)
logger = Logger(error_logger=errors)   # every worker process can write safely
```

**Same API, async:**

```python
from haashi.aio import FileHandler, JsonlErrorLogger

await FileHandler().save_json(payload, "/data/latest.json")
await JsonlErrorLogger("/var/log/myapp").log_error(exc, context="POST /orders")
```

---

## What's inside

| Class | Does | Docs |
|---|---|---|
| `Logger` | Console logging (`debug`/`info`/`warning`/`error`/`critical`/`exception`) with optional error persistence | [Logger](docs/logger.md) |
| `ErrorLogger` | Rotating JSON array error log; human-friendly, single process | [Error logging](docs/error-logging.md) |
| `JsonlErrorLogger` | Append-only JSONL error log; high volume, many threads and processes | [Error logging](docs/error-logging.md) |
| `FileHandler` | Atomic JSON/TXT I/O, script-relative path helpers | [FileHandler](docs/filehandler.md) |
| `Benchmark` | Warmup + `timeit` timing, fastest-batch reporting | [Benchmark](docs/benchmark.md) |
| `DateTime`, `ScreenUtil`, `Colors` | Fixed-offset "now", loading animation, text wrapping, ANSI colors | [Utilities](docs/utilities.md) |
| `haashi.aio` | Awaitable twins of the I/O classes | [Async API](docs/async.md) |

### Which error logger?

| | `ErrorLogger` | `JsonlErrorLogger` |
|---|---|---|
| Best for | Scripts, CLIs, occasional errors | Servers, bursts, multiple workers |
| File format | One JSON array (pretty-printed) | One JSON object per line |
| Cost per error | Rewrites the whole file | One append |
| Threads | Safe | Safe |
| Multiple processes | Not coordinated | **Safe** (OS file lock) |
| Rotation | Keep the last N entries | By size, with numbered backups |

---

## Documentation

The README is the pitch. The details live in [`docs/`](docs/README.md):

- [Getting started](docs/getting-started.md): install, first script, first service
- [Architecture & guarantees](docs/architecture.md): atomic writes, locking, path resolution, thread/process safety
- [Logger](docs/logger.md) · [Error logging](docs/error-logging.md) · [FileHandler](docs/filehandler.md) · [Benchmark](docs/benchmark.md) · [Utilities](docs/utilities.md)
- [Async API](docs/async.md)
- [Deployment recipes](docs/deployment.md): CLI, FastAPI, multi-worker, Lambda, Docker, tests
- [Reference](docs/reference.md): exceptions, types, full signatures
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md) · [Releasing](RELEASING.md) · [Changelog](CHANGELOG.md)

---

## Trust, by the numbers

- **0** runtime dependencies
- **3.10 → 3.14** on **Linux, macOS and Windows** in CI
- **ruff + pyright (strict) + pytest** gate every merge and every release
- Releases published to PyPI via **Trusted Publishing**; no long-lived tokens

---

## Contributing

```bash
git clone https://github.com/Haashiraaa/haashi.git && cd haashi
pip install -e ".[dev]"
ruff check . && pyright && pytest
```

Read the [contributing guide](docs/contributing.md) first; the short version: tests, strict types, no new runtime dependencies, and async parity.

## License

MIT, see [LICENSE](LICENSE). Made with ❤️ by [Haashiraaa](https://github.com/Haashiraaa).
