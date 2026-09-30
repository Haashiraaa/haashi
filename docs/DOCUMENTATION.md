# haashi Documentation

> Complete user guide and reference for **haashi** `1.2.x`: a lightweight, dependency-free Python utility toolkit for logging, file I/O, terminal helpers, datetime handling and benchmarking, with a matching async API.

This document explains *how things behave and why*, not just what the signatures are. If you only need a quick overview, see the [README](../README.md).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Core Concepts](#4-core-concepts)
   - [4.1 Zero dependencies and lazy loading](#41-zero-dependencies-and-lazy-loading)
   - [4.2 The error model](#42-the-error-model)
   - [4.3 Where files go: path resolution](#43-where-files-go-path-resolution)
   - [4.4 Atomic writes](#44-atomic-writes)
   - [4.5 Thread-safety](#45-thread-safety)
   - [4.6 Typing](#46-typing)
5. [Logger](#5-logger)
6. [ErrorLogger](#6-errorlogger)
7. [FileHandler](#7-filehandler)
8. [DateTime](#8-datetime)
9. [ScreenUtil](#9-screenutil)
10. [Colors](#10-colors)
11. [Benchmark](#11-benchmark)
12. [Async API (`haashi.aio`)](#12-async-api-haashiaio)
13. [Recipes](#13-recipes)
    - [13.1 CLI script](#131-cli-script)
    - [13.2 FastAPI service](#132-fastapi-service)
    - [13.3 AWS Lambda / read-only filesystems](#133-aws-lambda--read-only-filesystems)
    - [13.4 Docker / containers](#134-docker--containers)
    - [13.5 Using haashi in tests](#135-using-haashi-in-tests)
14. [Exceptions Reference](#14-exceptions-reference)
15. [Type Aliases](#15-type-aliases)
16. [Guarantees and Limits](#16-guarantees-and-limits)
17. [Troubleshooting / FAQ](#17-troubleshooting--faq)
18. [Development and Releasing](#18-development-and-releasing)
19. [API Cheat Sheet](#19-api-cheat-sheet)

---

## 1. Introduction

haashi is a small toolkit for the things nearly every script or service needs:

| Need | Class | Module |
|---|---|---|
| Console logging with optional JSON persistence | [`Logger`](#5-logger) | `haashi.utility` |
| Rotating JSON error log | [`ErrorLogger`](#6-errorlogger) | `haashi.utility` |
| JSON/TXT file I/O and script-relative paths | [`FileHandler`](#7-filehandler) | `haashi.utility` |
| Timezone-aware "now" | [`DateTime`](#8-datetime) | `haashi.utility` |
| Loading animation, text wrapping | [`ScreenUtil`](#9-screenutil) | `haashi.utility` |
| ANSI colors | [`Colors`](#10-colors) | `haashi.utility` |
| Timing functions | [`Benchmark`](#11-benchmark) | `haashi.utility` |
| Awaitable versions of the I/O classes | `FileHandler`, `ErrorLogger`, `Benchmark` | `haashi.aio` |

**Design goals**

- **Zero runtime dependencies.** Standard library only.
- **Cheap to import.** Submodules load on first use.
- **A good citizen.** Never configures the root logger, never registers global state you can't clean up.
- **Safe by default.** Atomic writes, validated input, thread-safe error logging.
- **Typed.** Full type hints, checked with pyright in strict mode, `py.typed` shipped.

**Requirements:** Python 3.10 or newer. Tested on Python 3.10 to 3.14 across Linux, macOS and Windows.

---

## 2. Installation

```bash
pip install haashi
```

Development install:

```bash
git clone https://github.com/Haashiraaa/haashi.git
cd haashi
pip install -e ".[dev]"
```

The `dev` extra installs pytest, pytest-cov, ruff, pyright, autopep8, build and twine.

Verify:

```bash
python -c "import haashi; print(haashi.__version__)"
```

---

## 3. Quick Start

```python
import logging
from haashi.utility import Logger, FileHandler, Benchmark, DateTime

logger = Logger(level=logging.INFO)
fh = FileHandler(logger=logger)

logger.info("Starting")

fh.save_json({"run": DateTime.get_current_time(1)}, "out/run.json")
print(fh.read_json("out/run.json"))

seconds = Benchmark(logger=logger).measure_time(lambda: sum(range(100_000)), run_times=10)
logger.info(f"{seconds:.6f}s per call")
```

The same code, async:

```python
from haashi.aio import FileHandler, Logger

fh = FileHandler()
await fh.save_json({"hello": "world"}, "out/hello.json")
```

---

## 4. Core Concepts

### 4.1 Zero dependencies and lazy loading

`import haashi` only imports `haashi.utility`'s `__init__`, which defines a lazy lookup table. Each class's module is imported the first time you access the class:

```python
import haashi.utility as u      # nothing else loaded yet
u.Colors                        # now haashi.utility.uiux is loaded
u.Logger                        # now haashi.utility.logger is loaded
```

`dir(haashi.utility)` and `from haashi.utility import *` both work and include the lazy names. Importing `haashi` does **not** import `asyncio` or `typing`. The async cost is opt-in via `haashi.aio`.

### 4.2 The error model

Everything haashi raises on purpose inherits from `UtilityError`, so you can catch broadly or narrowly. Standard built-ins are used where they are the obvious fit:

| Situation | Exception |
|---|---|
| File doesn't exist | `FileNotFoundError` (built-in) |
| Bad argument (range, mode) | `ValueError` (built-in) |
| Read/write/path failure | `FileOperationError` |
| Data can't be JSON | `InvalidJsonFormatError` |
| Logging misuse | `LoggingError` |
| Benchmarked function raised | `BenchmarkError` |
| Non-callable passed to Benchmark | `InvalidFunctionError` |

Full details in [Exceptions Reference](#14-exceptions-reference).

### 4.3 Where files go: path resolution

Both `ErrorLogger` and `FileHandler` have to decide where relative paths live. There are three modes.

**Script-relative (default for `ErrorLogger`).** "The script" is the directory of the running main script (`__main__.__file__`). Logs stay with your project no matter which directory you launch from.

**Fallbacks to the current working directory.** The cwd is used when:
- there is no main script (REPL, Jupyter, `python -c`), or
- the main script lives in an *installed location* (site-packages or the Python scripts/bin directory). That covers pip-installed console scripts and `python -m pytest`, where writing logs next to the tool would be surprising.

**Explicit directory (`log_dir`).** Recommended for servers and services. Under uvicorn/gunicorn, "the script" is the server's own entry point, not your app.

Resolution order for `ErrorLogger`:

| `path` given? | `log_dir` set? | Result |
|---|---|---|
| absolute | any | the `path`, as given |
| relative | yes | `log_dir / path` |
| relative | no | script dir (or cwd if `use_script_dir=False`) `/ path` |
| no | yes | `log_dir / errors_log.json` |
| no | no | script dir (or cwd) `/ logs / errors_log.json` |

### 4.4 Atomic writes

`FileHandler.save_json`, `FileHandler.save_txt(mode="w")` and the error log are written like this:

1. Write the new content to a temporary sibling file (`.name.<pid>.<thread>.tmp`).
2. `flush` and `fsync` it.
3. Swap it into place with `os.replace`.
4. Best-effort `fsync` of the directory (POSIX) so the rename itself is durable.

Readers see either the old file or the new one, never a half-written mix. If anything fails, the temp file is removed and the original is untouched. Also:

- **Symlinks** are written *through*: the link survives, the target is replaced.
- **Permissions** of an existing file are preserved.
- **Windows** retries `os.replace` briefly if antivirus or an indexer holds the file open.

`save_txt(mode="a")` appends directly and is **not** atomic.

### 4.5 Thread-safety

| Component | Thread-safe? |
|---|---|
| `ErrorLogger` (sync and async) | Yes. One process-wide lock guards every read-modify-write, shared by all instances. |
| `FileHandler` writes to *different* files | Yes |
| `FileHandler` writes to the *same* file | Each write is atomic; last write wins |
| `FileHandler.save_txt(mode="a")` to one file from many threads | Not guaranteed (plain append) |
| `Logger` | As thread-safe as Python's `logging` (handlers are locked) |
| `Benchmark(suppress_output=True)` | **No.** Redirecting stdout/stderr and `logging.disable` are process-wide. |
| Multiple **processes** writing one error log | Not coordinated. Use one `log_dir` per worker or a log shipper. |

### 4.6 Typing

- `py.typed` is shipped (PEP 561), so your type checker sees haashi's annotations.
- `src/` is checked with pyright in strict mode.
- Lazy names are declared in a `TYPE_CHECKING` block, so IDE completion and go-to-definition work even though imports are deferred.

---

## 5. Logger

Console logging with `debug`, `info`, `warning`, `error`, `critical`, plus `exception()` for the exception currently being handled. Optionally persists errors to the JSON log.

```python
Logger(level=logging.WARNING, color=None, error_logger=None)
```

| Parameter | Description |
|---|---|
| `level` | Minimum level shown (`logging.DEBUG`, `INFO`, ...). Default `WARNING`. |
| `color` | `None` = color only on a terminal. `True` / `False` force it. |
| `error_logger` | Default [`ErrorLogger`](#6-errorlogger) used when `save_to_json=True`. |

### 5.1 Behavior

- **Independent instances.** Each `Logger` owns a private `logging.Logger` (named `haashi.<n>`), so one instance's level never affects another's.
- **Nothing global.** The root logger is never touched, `propagate` is off, and loggers are not placed in Python's global logger registry, so creating one per request does not leak memory.
- **Output goes to stderr** as `[LEVEL] message`.
- **Attributes.** `logger.logger` is the underlying `logging.Logger`. `logger.error_logger` is the default persistence target (may be `None`).

### 5.2 Color rules

| Level | Color |
|---|---|
| DEBUG | dim cyan |
| INFO | bold blue |
| WARNING | bold yellow |
| ERROR / CRITICAL | bold red |

With `color=None` (default), colors are used only if the stream is a terminal **and** the [`NO_COLOR`](https://no-color.org) environment variable is unset. Log files, pipes and CI stay plain text. `color=True` forces colors even when `NO_COLOR` is set. `color=False` never emits ANSI codes.

### 5.3 Methods

#### `debug(message)`, `info(message)`, `warning(message)`

`message` can be any object (converted with `str`).

```python
logger = Logger(level=logging.DEBUG)
logger.debug("cache miss")
logger.info("started")
logger.warning("disk at 91%")
```

#### `error(...)`

```python
logger.error(
    message="Error occurred!",
    error_logger=None,
    path=None,
    exception=None,
    save_to_json=False,
    use_script_dir=True,
    context=None,
)
```

```python
try:
    load_config()
except Exception as exc:
    logger.error("Config load failed", exception=exc, save_to_json=True, context="startup")
```

With `save_to_json=True` the entry is written to the JSON log and the console message gains a second line: `See <path> for details`.

**Raises** `LoggingError` if `save_to_json=True` but no `exception` was passed. It fails loudly instead of silently doing nothing.

Which `ErrorLogger` is used: the per-call `error_logger`, else the one given to `Logger(...)`, else a default `ErrorLogger()` created on demand and cached on `logger.error_logger`.

#### `critical(...)`

For failures the program cannot recover from (for example right before exiting). It takes exactly the same arguments as `error()`, is styled like errors, and is shown at every level, including `logging.CRITICAL`.

```python
logger.critical(
    message="Critical error!",
    error_logger=None,
    path=None,
    exception=None,
    save_to_json=False,
    use_script_dir=True,
    context=None,
)
```

```python
try:
    connect_to_database()
except ConnectionError as exc:
    logger.critical("Database unreachable", exception=exc, save_to_json=True, context="startup")
    raise SystemExit(1)
```

**Raises** `LoggingError` if `save_to_json=True` but no `exception` was passed.

#### `exception(...)`

Like `error`, but takes the exception from the active `except` block and includes the traceback in the console output.

```python
logger.exception(
    message="Exception occurred!",
    error_logger=None,
    save_to_json=False,
    path=None,
    use_script_dir=True,
    context=None,
)
```

> Note the parameter order differs from `error()` (`save_to_json` comes before `path`). Use keyword arguments.

```python
try:
    risky()
except Exception:
    logger.exception("risky() failed", save_to_json=True, context="job-42")
```

**Raises** `LoggingError` if called outside an `except` block.

---

## 6. ErrorLogger

A rotating JSON error log. `log_error`, `view_error_entries` and `clear_errors` resolve the file identically (see [4.3](#43-where-files-go-path-resolution)), so what you write is what you read and clear.

```python
ErrorLogger(log_dir=None)
```

| Parameter | Description |
|---|---|
| `log_dir` | Directory relative log paths resolve under. `~` is expanded. `None` keeps script-relative behavior. |

The attribute `errors.log_dir` holds the expanded `Path` (or `None`).

### 6.1 `log_error`

```python
errors.log_error(
    exception,
    context=None,
    path=None,
    use_script_dir=True,
    utc_offset_hours=0,
    max_entries=100,
) -> Path
```

Appends an entry and returns the path of the file it wrote.

| Parameter | Description |
|---|---|
| `exception` | Any `BaseException`. |
| `context` | Free-form label such as `"data_loading"`. Stored as `"unspecified"` if omitted. |
| `path` | Log file. Default `logs/errors_log.json`. |
| `use_script_dir` | Resolve a relative path against the script dir instead of cwd. Ignored when `log_dir` is set. |
| `utc_offset_hours` | Offset for the timestamp, -12 to +14. |
| `max_entries` | Keep only the most recent N entries (>= 1). Older ones are dropped. |

**Raises** `ValueError` if `max_entries < 1` or the offset is out of range.

**Entry format**

```json
{
    "timestamp": "2026-09-30T14:05:11.123456+01:00",
    "type": "ValueError",
    "message": "boom",
    "context": "math",
    "traceback": "Traceback (most recent call last): ..."
}
```

The file is a JSON list, oldest first.

### 6.2 `view_error_entries`

```python
errors.view_error_entries(path=None, limit=10, use_script_dir=True) -> list
```

Returns the most recent `limit` entries. `limit=None` returns everything. Raises `ValueError` if `limit < 1`. A missing file returns `[]`.

### 6.3 `clear_errors`

```python
errors.clear_errors(path=None, use_script_dir=True, *, confirm=True) -> bool
```

Deletes the log. Returns `True` if a file was deleted, `False` if there was none (or the user declined).

- `confirm=True` asks `Delete all entries in <path>? ... [y/N]`. Only `y`/`yes` (any case) proceeds.
- **Requires an interactive terminal.** In scripts, CI and servers, pass `confirm=False`. Otherwise it raises `LoggingError` rather than hanging on `input()`.

### 6.4 Corrupt logs

If the log can't be parsed, or isn't a JSON list, haashi **does not overwrite it**:

1. The file is moved to `<name>.corrupt` (or `.corrupt.1`, `.corrupt.2`, ... if a backup already exists).
2. A `RuntimeWarning` is emitted.
3. A fresh log starts.

This also happens when a corrupt file is *read* via `view_error_entries`.

### 6.5 Performance note

Each `log_error` call re-reads, rewrites and `fsync`s the whole file under a lock. That is ideal for occasional errors but not a high-volume logger. For error storms, log to the console or a log shipper and persist only what you need to keep.

---

## 7. FileHandler

JSON and text I/O with validation, atomic writes, and script-relative path helpers.

```python
FileHandler(logger=None)
```

`logger` is an optional [`Logger`](#5-logger) used for debug/warning messages (default: a warning-level `Logger`). Paths may be `str`, `pathlib.Path` or any `os.PathLike`.

### 7.1 JSON

#### `save_json(data, path, indent=4)`

Saves JSON-serializable data. Overwrites. Parent directories are created.

```python
fh.save_json({"status": "ok", "items": [1, 2, 3]}, "data/output.json")
```

- **Validated before touching disk.** If `data` can't be serialized, nothing is written (and an existing file is left untouched).
- **Strict JSON:** `NaN` and `Infinity` are rejected, as are sets, custom objects and circular references.
- **Atomic** (see [4.4](#44-atomic-writes)).
- Non-ASCII text is written escaped (`"Ọlá"` becomes `"\u1ecc\u00e1"`). It round-trips exactly through `read_json`.

**Raises** `InvalidJsonFormatError` (bad data), `FileOperationError` (write failed).

#### `read_json(path)`

```python
data = fh.read_json("data/output.json")
```

**Raises** `FileNotFoundError` (missing), `FileOperationError` (not a file, invalid JSON, undecodable, I/O error).

### 7.2 Text

#### `save_txt(data, path, mode="w", add_newline_prefix=False)`

```python
fh.save_txt("first line", "notes.txt")
fh.save_txt("\nmore", "notes.txt", mode="a")
fh.save_txt("more", "notes.txt", mode="a", add_newline_prefix=True)
```

| Parameter | Description |
|---|---|
| `mode` | `"w"` overwrite (atomic) or `"a"` append (not atomic). Anything else raises `ValueError`. |
| `add_newline_prefix` | Write `\n` before the content. Handy when appending to a file not ending in a newline. |

UTF-8.

#### `read_txt(path)`

Returns the file as a string. **Raises** `FileNotFoundError`, `FileOperationError`.

### 7.3 Filesystem checks

| Method | Does | Raises |
|---|---|---|
| `ensure_writable_path(path) -> Path` | Creates parent directories, returns the path. | `FileOperationError` |
| `ensure_readable_file(path) -> Path` | Returns the path if it's an existing file. | `FileNotFoundError`, `FileOperationError` (exists but isn't a file) |

### 7.4 Script-relative path helpers

Useful when a script must find project files regardless of where it's launched from.

#### `get_script_dir() -> Path`

Directory of the executed main script. Falls back to the cwd (see [4.3](#43-where-files-go-path-resolution)).

#### `get_parent_path(levels_up=1, start_path=None) -> Path`

Climbs `levels_up` directories above the *caller's* file (or above `start_path`).

```python
# script: my-project/src/scripts/process.py
fh.get_parent_path(levels_up=2)   # -> /home/user/my-project
fh.get_parent_path(levels_up=0)   # -> /home/user/my-project/src/scripts
```

**Raises** `ValueError` if `levels_up < 0`. In a REPL/notebook (no `__file__`), it starts from the cwd.

#### `get_ancestor_by_name(folder_name, start_path=None, max_levels=10) -> Path | None`

Finds an ancestor directory by exact, case-sensitive name. More robust than counting levels because it survives refactors of your folder layout.

```python
root = fh.get_ancestor_by_name("my-project")
if root is None:
    raise SystemExit("run this from inside my-project")
config = fh.read_json(root / "config.json")
```

It checks the start directory and up to `max_levels - 1` of its parents. Returns `None` (with a warning) if not found.

---

## 8. DateTime

Timezone-aware "now" at a **fixed UTC offset**.

```python
DateTime.get_current_time(utc_offset_hours=0, string_format=True, only_date=True)
```

| Parameter | Description |
|---|---|
| `utc_offset_hours` | -12 to +14. Fractions allowed (`5.5` = India, `5.75` = Nepal). |
| `string_format` | `True` returns a string; `False` returns a timezone-aware `datetime`. |
| `only_date` | For strings: `YYYY-MM-DD` if `True`, else `YYYY-MM-DD HH:MM:SS`. Ignored for datetimes. |

```python
DateTime.get_current_time(1)                          # '2026-09-30'
DateTime.get_current_time(1, only_date=False)         # '2026-09-30 14:05:11'
DateTime.get_current_time(5.5, string_format=False)   # datetime(..., tzinfo=UTC+05:30)
```

**Raises** `ValueError` if the offset is outside -12..+14.

> It uses a fixed offset: no time-zone names and no daylight-saving handling. For those, use `zoneinfo`.

---

## 9. ScreenUtil

Small terminal output helpers (static methods).

#### `ScreenUtil.animate(text="Loading", cycles=2, delay=0.5)`

Prints a dot animation on one line (`Loading.`, `Loading..`, `Loading...`), one dot per `delay` seconds; one cycle is three dots. The cursor is left at the end of the line, so call `print()` afterwards.

```python
ScreenUtil.animate("Processing", cycles=3, delay=0.3)
print()
```

#### `ScreenUtil.format_text(text, width=70) -> str`

Wraps each line to `width` characters. Blank lines are preserved, so paragraphs stay separated.

```python
print(ScreenUtil.format_text(long_text, width=60))
```

---

## 10. Colors

ANSI escape codes as class attributes, plus helpers.

**Attributes**

| Group | Names |
|---|---|
| Reset | `RESET` |
| Foreground | `BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE` |
| Bright foreground | `BRIGHT_BLACK` ... `BRIGHT_WHITE` |
| Background | `BG_BLACK` ... `BG_WHITE` |
| Styles | `BOLD DIM ITALIC UNDERLINE BLINK REVERSE HIDDEN STRIKETHROUGH` |

**Helpers** (each returns a string)

| Helper | Style |
|---|---|
| `Colors.colored(text, color, style=None)` | any color, optional style |
| `Colors.debug(text)` | dim cyan |
| `Colors.info(text)` | bold blue |
| `Colors.warning(text)` | bold yellow |
| `Colors.error(text)` | bold red |
| `Colors.success(text)` | bold green |
| `Colors.header(text)` | bold underlined cyan |

```python
print(Colors.success("Build passed"))
print(Colors.colored("custom", Colors.MAGENTA, Colors.BOLD))
print(f"{Colors.CYAN}raw codes{Colors.RESET}")
```

> `Colors` **always** emits ANSI codes. Only [`Logger`](#5-logger) auto-detects terminals and `NO_COLOR`. If you print colors to files or pipes yourself, check `sys.stdout.isatty()` first.

---

## 11. Benchmark

Times a zero-argument function with warmup and `timeit`.

```python
Benchmark(logger=None)
```

#### `measure_time(func, warmup_times=3, run_times=5, repeat_times=1, suppress_output=True) -> float`

| Parameter | Description |
|---|---|
| `func` | Callable taking no arguments. Use `lambda` or `functools.partial` to bind arguments. |
| `warmup_times` | Untimed warmup calls. `0` skips warmup. |
| `run_times` | Calls per timed batch (>= 1). |
| `repeat_times` | Number of batches (>= 1). |
| `suppress_output` | Silence stdout, stderr and logging while running. |

**Returns** seconds **per call**, taken from the *fastest* batch (`min(batches) / run_times`). This is the standard `timeit` approach: slower batches mostly reflect noise from other processes.

```python
bench = Benchmark()

def parse():
    return sum(range(1_000_000))

print(f"{bench.measure_time(parse, run_times=10, repeat_times=3):.4f}s per call")
```

**Raises**

| Exception | When |
|---|---|
| `ValueError` | `run_times < 1`, `repeat_times < 1`, or `warmup_times < 0` |
| `InvalidFunctionError` | `func` isn't callable |
| `BenchmarkError` | `func` raised while being measured (original is chained as `__cause__`) |

**Output suppression** restores the previous `logging.disable` level afterwards (even if you had set your own). It is process-wide, so don't use it in multi-threaded programs while other threads log or print.

---

## 12. Async API (`haashi.aio`)

Same class and method names as `haashi.utility`. Disk I/O is awaitable and runs in a worker thread (`asyncio.to_thread`), so it never blocks the event loop. No new dependencies.

```python
from haashi.aio import FileHandler, ErrorLogger, Benchmark, Logger
```

### 12.1 What's async and what isn't

| Name | In `haashi.aio` |
|---|---|
| `FileHandler` | `save_json`, `read_json`, `save_txt`, `read_txt`, `ensure_writable_path`, `ensure_readable_file` are `async`. `get_script_dir`, `get_parent_path`, `get_ancestor_by_name` stay **sync** (no real I/O). |
| `ErrorLogger` | `log_error`, `view_error_entries`, `clear_errors` are `async` |
| `Benchmark` | `measure_time` is `async` |
| `Logger`, `DateTime`, `Colors`, all exceptions | Re-exported **unchanged** (same objects as in `haashi.utility`), so `Logger.critical()` and friends work the same. They are plain calls: no `await`. |

Signatures match the sync classes parameter-for-parameter, in the same order. The test suite enforces this. The one intentional difference is `Benchmark.measure_time(suppress_output=...)`, which defaults to `False` (below).

### 12.2 FileHandler

```python
fh = FileHandler()
await fh.save_json({"a": 1}, "data/a.json")
data = await fh.read_json("data/a.json")
await fh.save_txt("hello", "notes.txt")
text = await fh.read_txt("notes.txt")
```

Errors propagate as the same exception types as the sync API. Path helpers still resolve relative to *your* file, not haashi's wrapper.

Concurrency:

```python
await asyncio.gather(*(fh.save_json({"i": i}, f"out/{i}.json") for i in range(100)))
```

Writes to different files are independent. Concurrent writes to the same file are each atomic; last write wins.

### 12.3 ErrorLogger

```python
errors = ErrorLogger(log_dir="/var/log/myapp")

try:
    await handle_request()
except Exception as exc:
    await errors.log_error(exc, context="POST /orders")
    raise
```

It shares the same process-wide lock as the sync `ErrorLogger`, so `asyncio.gather` over many `log_error` calls loses no entries, and mixing sync and async callers in one process is safe. On servers, pass `confirm=False` to `clear_errors`.

### 12.4 Benchmark

```python
bench = Benchmark()

async def fetch():
    await asyncio.sleep(0.01)

per_call = await bench.measure_time(fetch, run_times=10, repeat_times=3)
```

- Each run `await`s the function's result if it is awaitable.
- Plain (sync) functions work too, but they run **on the event loop** and block it while timed.
- `suppress_output` defaults to **`False`**, unlike the sync version. Silencing stdout/stderr/logging is process-wide, so in a running server it would also mute every other request. Enable it only in scripts.
- Timing uses `time.perf_counter()` over the batch; the fastest batch wins, as in the sync version.
- Errors are wrapped in `BenchmarkError`; validation errors behave as in the sync class.

### 12.5 When to use which

| You're writing... | Import from |
|---|---|
| A script, CLI, notebook | `haashi.utility` |
| FastAPI / Starlette / aiohttp / asyncio code | `haashi.aio` |
| Sync code inside a thread pool | `haashi.utility` (it's thread-safe where noted in [4.5](#45-thread-safety)) |

---

## 13. Recipes

### 13.1 CLI script

```python
import logging
from haashi.utility import Logger, FileHandler, ErrorLogger

logger = Logger(level=logging.INFO, error_logger=ErrorLogger())
fh = FileHandler(logger=logger)

def main() -> None:
    root = fh.get_ancestor_by_name("my-tool")
    if root is None:
        raise SystemExit("run inside my-tool/")
    config = fh.read_json(root / "config.json")
    logger.info(f"Loaded {len(config)} settings")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal error", save_to_json=True, context="main")
        raise SystemExit(1)
```

Errors land in `logs/errors_log.json` next to your script.

### 13.2 FastAPI service

```python
from fastapi import FastAPI
from haashi.aio import ErrorLogger, FileHandler, Logger

app = FastAPI()
logger = Logger()
errors = ErrorLogger(log_dir="/var/log/myapp")
files = FileHandler()

@app.post("/orders")
async def create_order(order: dict):
    try:
        await files.save_json(order, "/data/orders/latest.json")
    except Exception as exc:
        await errors.log_error(exc, context="POST /orders")
        raise
    return {"ok": True}
```

Tips:
- Always set `log_dir` on servers. Default script-relative logging points at the server's own entry point.
- With several gunicorn/uvicorn **workers**, give each its own `log_dir` (for example include the PID) or ship logs externally. Threads are coordinated; processes are not.

### 13.3 AWS Lambda / read-only filesystems

Lambda's code directory is read-only, so the default error-log location will fail. Write to `/tmp`:

```python
from haashi.utility import ErrorLogger, Logger

errors = ErrorLogger(log_dir="/tmp/logs")
logger = Logger(error_logger=errors)
```

Remember `/tmp` is not durable across cold starts. Also send important errors to your platform's logging (CloudWatch).

### 13.4 Docker / containers

Containers usually want logs on stderr, which is what `Logger` does. For persisted JSON errors, mount a volume and point `log_dir` at it:

```python
ErrorLogger(log_dir="/var/log/myapp")   # mounted volume
```

Set `NO_COLOR=1` (or rely on TTY detection) to keep container logs free of ANSI codes.

### 13.5 Using haashi in tests

- Point everything at pytest's `tmp_path`:

```python
def test_logs_errors(tmp_path):
    errors = ErrorLogger(log_dir=tmp_path)
    errors.log_error(ValueError("x"))
    assert len(errors.view_error_entries()) == 1
```

- Use `use_script_dir=False` or `log_dir` so tests don't write into your repo (the default location is next to the script that started pytest, or the cwd).
- Capture output with `capsys`. `Logger` writes to stderr, without colors when not a TTY.

---

## 14. Exceptions Reference

```
UtilityError
├── FileOperationError        FileHandler read/write/path failures
├── InvalidJsonFormatError    data can't be represented as (strict) JSON
├── LoggingError              Logger/ErrorLogger misuse
├── BenchmarkError            the benchmarked function raised
├── InvalidFunctionError      a non-callable was passed to Benchmark
└── BenchmarkTimeoutError     reserved for future timeout support
```

| Exception | Raised by | Typical cause |
|---|---|---|
| `FileOperationError` | `FileHandler.*` | Permission denied, path is a directory, invalid JSON on read, undecodable text |
| `InvalidJsonFormatError` | `save_json` | sets, custom objects, `NaN`/`Infinity`, circular references |
| `LoggingError` | `Logger.error/exception`, `ErrorLogger.clear_errors` | `save_to_json=True` without `exception`; `exception()` outside `except`; `confirm=True` without a terminal |
| `BenchmarkError` | `Benchmark.measure_time` | your function raised |
| `InvalidFunctionError` | `Benchmark.measure_time` | argument isn't callable |
| `BenchmarkTimeoutError` | (nothing yet) | reserved |

Built-ins also raised: `FileNotFoundError` (missing files), `ValueError` (bad numeric/mode arguments), `RuntimeWarning` (corrupt log quarantined).

Catching:

```python
from haashi.utility import UtilityError, FileOperationError

try:
    data = fh.read_json("x.json")
except FileNotFoundError:
    data = {}
except FileOperationError as exc:
    logger.error(f"bad file: {exc}")
except UtilityError:
    raise
```

All exceptions are importable from `haashi.utility` and `haashi.aio`.

---

## 15. Type Aliases

Defined in `haashi.utility._types` (internal, but useful to know for annotations):

```python
PathLike = str | Path | os.PathLike[str]
JSONType = str | int | float | bool | None | list[JSONType] | dict[str, JSONType]
```

Public method signatures use these, so passing a `Path` or `str` both type-check.

---

## 16. Guarantees and Limits

**You can rely on**

- No runtime dependencies; `import haashi` stays cheap.
- Root logging is never reconfigured.
- Creating many `Logger`/`FileHandler` instances doesn't grow global state.
- JSON/TXT(`"w"`) writes never leave a truncated file, and failures leave the original intact.
- A corrupt error log is preserved (quarantined), never overwritten.
- `ErrorLogger` is thread-safe and loses no entries under concurrency within one process.
- Sync and async APIs have matching names and signatures (enforced by tests).

**Known limits**

- Multi-process writers to one error log are not coordinated.
- `save_txt(mode="a")` is a plain append (not atomic).
- `Benchmark(suppress_output=True)` is process-wide.
- `DateTime` uses fixed UTC offsets, not time-zone names or DST.
- Error logging rewrites the full file each time (by design; not for high volume).

---

## 17. Troubleshooting / FAQ

**My error log didn't appear where I expected.**
By default it goes to `logs/errors_log.json` next to the *main script*. If that script is in site-packages/bin (console script, `python -m ...`) or there is no main script (REPL), it goes to the **cwd**. Set `ErrorLogger(log_dir=...)` to be explicit. `log_error` returns the exact path it wrote.

**`clear_errors` raised `LoggingError`.**
`confirm=True` needs an interactive terminal. Pass `confirm=False` in scripts, CI and servers.

**I got a `RuntimeWarning: Corrupted error log`.**
The log couldn't be parsed. haashi moved it to `<name>.corrupt` and started a fresh one. Inspect or delete the backup.

**`save_json` raised `InvalidJsonFormatError`.**
Your data contains something JSON can't represent (a `set`, a custom object, `NaN`). Convert it first (for example `sorted(my_set)`). Nothing was written.

**Logs have weird `\033[...` characters in a file.**
Colors are only emitted on TTYs by default. If you forced `color=True`, remove it, or set `color=False`.

**Benchmark output or logs disappeared.**
`suppress_output=True` (the sync default) silences stdout/stderr/logging during timing. Pass `suppress_output=False` to see output.

**My async benchmark blocks the loop.**
You passed a plain function; it runs on the loop. Pass a coroutine function, or benchmark in a script.

**Non-ASCII characters look escaped in my JSON file.**
Expected: `save_json` escapes non-ASCII. `read_json` restores the original text exactly.

**`get_parent_path`/`get_ancestor_by_name` start from the wrong place.**
They start from the *caller's* file. In a REPL or notebook there is no file, so the cwd is used. Pass `start_path=` explicitly.

---

## 18. Development and Releasing

```bash
git clone https://github.com/Haashiraaa/haashi.git
cd haashi
pip install -e ".[dev]"
ruff check . && pyright && pytest
```

**Project layout**

```
haashi/
├── __init__.py            # __version__ (single source of truth)
├── py.typed
├── utility/
│   ├── __init__.py        # lazy loader
│   ├── logger.py          # Logger, ErrorLogger
│   ├── filehandler.py     # FileHandler
│   ├── benchmark.py       # Benchmark
│   ├── uiux.py            # ScreenUtil, Colors
│   ├── _datetime.py       # DateTime
│   ├── exceptions.py      # UtilityError and subclasses
│   ├── _atomic.py         # crash-safe writes (internal)
│   ├── _paths.py          # script-dir detection (internal)
│   └── _types.py          # PathLike, JSONType, dump_json (internal)
└── aio/
    ├── __init__.py
    ├── filehandler.py
    ├── errorlogger.py
    └── benchmark.py
```

**Contribution checklist**

- Tests for new behavior (`pytest`).
- Type hints (pyright strict on `src/`).
- Docstrings on public functions, with an example where it helps.
- Raise a `UtilityError` subclass; don't print-and-swallow.
- No new runtime dependencies.
- If you add a public name to `haashi.utility`, update `__all__`, `_LAZY` and the `TYPE_CHECKING` block (a test fails if they drift).
- If you add a method to a sync class that has an async twin, add the twin (a test checks parity).

**Releasing** is tag-driven and documented in [RELEASING.md](../RELEASING.md). User-visible changes are recorded in the [CHANGELOG](../CHANGELOG.md). Summary: bump `__version__`, add a `## [X.Y.Z]` changelog section, push to `main`, tag `vX.Y.Z`. CI validates the changelog, creates the GitHub Release, and publishes to PyPI via Trusted Publishing. A PyPI version can never be re-uploaded, so fix forward with the next patch.

---

## 19. API Cheat Sheet

```python
# Logger
Logger(level=WARNING, color=None, error_logger=None)
  .debug(msg) .info(msg) .warning(msg)
  .error(message, error_logger, path, exception, save_to_json, use_script_dir, context)
  .critical(message, error_logger, path, exception, save_to_json, use_script_dir, context)
  .exception(message, error_logger, save_to_json, path, use_script_dir, context)

# ErrorLogger
ErrorLogger(log_dir=None)
  .log_error(exception, context=None, path=None, use_script_dir=True,
             utc_offset_hours=0, max_entries=100) -> Path
  .view_error_entries(path=None, limit=10, use_script_dir=True) -> list
  .clear_errors(path=None, use_script_dir=True, *, confirm=True) -> bool

# FileHandler
FileHandler(logger=None)
  .save_json(data, path, indent=4)         .read_json(path)
  .save_txt(data, path, mode="w", add_newline_prefix=False)   .read_txt(path)
  .ensure_writable_path(path)              .ensure_readable_file(path)
  .get_script_dir()
  .get_parent_path(levels_up=1, start_path=None)
  .get_ancestor_by_name(folder_name, start_path=None, max_levels=10)

# DateTime
DateTime.get_current_time(utc_offset_hours=0, string_format=True, only_date=True)

# ScreenUtil
ScreenUtil.animate(text="Loading", cycles=2, delay=0.5)
ScreenUtil.format_text(text, width=70)

# Colors
Colors.colored(text, color, style=None)
Colors.debug/info/warning/error/success/header(text)

# Benchmark
Benchmark(logger=None)
  .measure_time(func, warmup_times=3, run_times=5, repeat_times=1, suppress_output=True) -> float

# haashi.aio  (await everything except Logger, DateTime, Colors, path helpers)
FileHandler / ErrorLogger / Benchmark   # same signatures
Benchmark.measure_time(..., suppress_output=False)   # default differs
```
