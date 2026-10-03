
# Architecture & guarantees

This page documents the design decisions behind haashi and the exact guarantees you can rely on.

## Package layout

```
src/haashi/
├── __init__.py              # __version__ (single source of truth)
├── py.typed                 # PEP 561 marker
├── utility/                 # sync API
│   ├── __init__.py          # lazy loader (_LAZY + TYPE_CHECKING block)
│   ├── logger.py            # Logger, ErrorLogger, JsonlErrorLogger
│   ├── filehandler.py       # FileHandler
│   ├── benchmark.py         # Benchmark
│   ├── uiux.py              # ScreenUtil, Colors
│   ├── _datetime.py         # DateTime
│   ├── exceptions.py        # UtilityError and subclasses
│   ├── _atomic.py           # atomic_write_text, replace_file (internal)
│   ├── _filelock.py         # cross-process file lock (internal)
│   ├── _paths.py            # script-dir detection, log path resolution (internal)
│   └── _types.py            # PathLike, JSONType, dump_json, ErrorWriter (internal)
└── aio/                     # async API, same names
    ├── __init__.py
    ├── filehandler.py
    ├── errorlogger.py
    ├── jsonl_errorlogger.py
    └── benchmark.py
```

Modules starting with `_` are internal and may change without notice. Everything in `haashi.utility.__all__` and `haashi.aio.__all__` is public API.

## Zero dependencies

haashi imports only the standard library. CI enforces this twice: a test imports every public name in a fresh interpreter and fails on any non-stdlib module, and the build job asserts the wheel declares **no** runtime requirements.

## Lazy loading

`haashi.utility/__init__.py` defines `_LAZY`, a map of public name → submodule, plus a module-level `__getattr__`. A submodule is imported the first time one of its names is accessed, then cached in the package namespace.

```python
import haashi.utility as u      # nothing else loaded
u.Colors                        # loads haashi.utility.uiux only
u.Logger                        # loads haashi.utility.logger (and what it imports)
```

Details:

- `dir()` and `from haashi.utility import *` include the lazy names (`__dir__` and `__all__` are defined).
- `TYPE_CHECKING` is **defined by hand** (`TYPE_CHECKING = False`) rather than imported from `typing`, because importing `typing` alone costs more than the rest of the file. Type checkers treat it identically.
- Importing `haashi` imports neither `asyncio` nor `typing`. The async cost is opt-in via `haashi.aio`.
- Tests fail if `__all__`, `_LAZY` and the `TYPE_CHECKING` import block drift apart.

## Atomic writes

Used by `FileHandler.save_json`, `FileHandler.save_txt(mode="w")` and `ErrorLogger`.

1. Resolve the real target (`os.path.realpath`), so symlinks are **written through**: the link survives, the target is replaced.
2. Write to a sibling temp file named `.<name>.<pid>.<thread-id>.tmp`.
3. `flush()` and `os.fsync()` the temp file.
4. Copy the existing file's permission bits onto the temp file (if the target existed).
5. `os.replace(tmp, target)`, atomic on POSIX and Windows. On Windows it is retried up to 5 times with a short back-off when antivirus or an indexer briefly holds the file.
6. Best-effort `fsync` of the parent directory (POSIX only) so the rename itself is durable.

If anything fails, the temp file is removed and the original is untouched. Readers see either the old complete file or the new complete file.

**Not atomic:** `FileHandler.save_txt(mode="a")` and `JsonlErrorLogger` appends. Those are single appends by design (see below).

## Append-only logging and crash behavior

`JsonlErrorLogger` writes each entry as **one** `write()` of a single `\n`-terminated line on a file opened in append mode (`"ab"`, i.e. `O_APPEND`). Because `json.dumps` escapes newlines inside strings, one entry is always exactly one line.

- Process crash: the entry is either written or not. A torn final line is possible only on a hard kill mid-write; readers skip it with a `RuntimeWarning`.
- Power loss: entries not yet flushed by the OS can be lost unless you opt in with `fsync=True`.

## Reading large logs

`JsonlErrorLogger.view_error_entries(limit=N)` reads each file **backwards in 64 KB blocks**, newest file first, and stops once it has `N` valid entries. Memory and I/O are proportional to `N`, not to the log size. `limit=None` reads everything.

## Locking model

`JsonlErrorLogger` uses two layers on every append, view and clear:

| Layer | Scope | Mechanism |
|---|---|---|
| `_THREAD_LOCK` | Threads in one process | `threading.RLock`, shared by all `JsonlErrorLogger` instances |
| `file_lock(path)` | Processes on one machine | Advisory OS lock on a sibling `<name>.lock` file |

Cross-process lock details (`_filelock.py`):

- **Both platforms** try a non-blocking lock (`fcntl.flock(LOCK_EX | LOCK_NB)` on POSIX, `msvcrt.locking(LK_NBLCK)` on Windows) and retry with a short back-off (1 ms growing to 20 ms) until `lock_timeout` seconds elapse, then raise `LoggingError`. The OS drops the lock if the holder dies, so a crashed worker cannot wedge the others.
- The lock lives on a separate `.lock` file that is never renamed or deleted, so it stays valid while the log is rotated. One small file per log is expected. It is deliberately not cleaned up: removing a lock file while another process has it open lets two processes lock different inodes and silently defeats the lock.
- Advisory locks are unreliable on **network filesystems** (NFS/SMB). Do not share one log across hosts.

`ErrorLogger` (JSON array) uses only a process-wide `RLock` (`_LOG_LOCK`). It is correct across threads and asyncio tasks, but its read-modify-write is **not** coordinated between processes. Use `JsonlErrorLogger` when several processes share a log.

## Rotation (JsonlErrorLogger)

Rotation happens under the lock, before the append, when `max_bytes` is set:

- Skipped if the live file is empty, or if `size + incoming <= max_bytes`. (A single entry larger than `max_bytes` is therefore still written, into an empty file.)
- With `backups=0`, the live file is deleted.
- Otherwise backups shift `.N-1 → .N, ..., .1 → .2`, then the live file becomes `.1`. The oldest beyond `backups` is overwritten/dropped.
- Reading returns backups oldest-first (`.N … .1`), then the live file.

## Path resolution

Both error loggers and `FileHandler.get_script_dir()` share the same rules.

**Script directory** (`detect_script_dir`): the directory of `__main__.__file__`. Falls back to the current working directory when:

- there is no main script (REPL, Jupyter, `python -c`), or
- the main script lives in an *installed location*: any of `purelib`, `platlib`, `scripts` from `sysconfig` (pip-installed console scripts, `python -m pytest`).

**Log path** (`resolve_log_path`):

| `path` | `log_dir` | Result |
|---|---|---|
| absolute | any | `path` as given |
| relative | set | `log_dir / path` |
| relative | not set | (script dir if `use_script_dir` else cwd) `/ path` |
| none | set | `log_dir / <default name>` |
| none | not set | (script dir or cwd) `/ logs / <default name>` |

Default names: `errors_log.json` (`ErrorLogger`), `errors_log.jsonl` (`JsonlErrorLogger`). With `log_dir` set, `use_script_dir` is ignored.

## Logger isolation

`Logger` constructs `logging.Logger(f"haashi.{n}", level)` **directly** instead of calling `logging.getLogger()`. `getLogger` registers loggers in a global dict that is never cleaned up; creating one `Logger` per request would leak forever. A counter (`itertools.count`) gives unique names (unlike `id()`, never reused). `propagate` is off, and the root logger is never touched. A test asserts the registry does not grow across 200 `Logger()` / `FileHandler()` constructions.

## Concurrency matrix

| Component | Threads | asyncio tasks | Multiple processes |
|---|---|---|---|
| `Logger` | Safe (stdlib handler locks) | Safe | Independent per process |
| `ErrorLogger` | Safe | Safe (`haashi.aio`) | **Not coordinated** |
| `JsonlErrorLogger` | Safe | Safe (`haashi.aio`) | **Safe** (local filesystems) |
| `FileHandler`, different files | Safe | Safe | Safe |
| `FileHandler`, same file, atomic writes | Each write atomic, last wins | same | same |
| `FileHandler.save_txt(mode="a")` | Not guaranteed | Not guaranteed | Not guaranteed |
| `Benchmark(suppress_output=True)` | **No** (process-wide redirect) | **No** | n/a |

## The `ErrorWriter` protocol

`Logger(error_logger=...)` accepts any object with:

```python
def log_error(
    self,
    exception: BaseException,
    context: str | None = None,
    path: PathLike | None = None,
    use_script_dir: bool = True,
) -> Path: ...
```

`ErrorLogger` and `JsonlErrorLogger` both satisfy it. You can pass your own implementation (for example one that ships to a service) as long as it returns the `Path` it wrote to; `Logger` uses that path in its `See <path> for details` message.

## Typing

- `py.typed` ships in the wheel (checked by the build job).
- `src/` is checked with pyright in **strict** mode; tests are checked in standard mode.
- Overloads on `DateTime.get_current_time` give `str` or `datetime` return types depending on `string_format`.

## Async design

`haashi.aio` wraps the sync classes and runs disk I/O with `asyncio.to_thread`. It deliberately reuses the sync implementations, so locks, atomicity and validation are identical. A parity test enforces that every public sync method exists in the async twin with the same parameter order and defaults (the one allowed difference is `Benchmark.measure_time(suppress_output=False)`). See [Async API](async.md).

## Guarantees and limits

**You can rely on**

- No runtime dependencies; cheap import.
- Root logging is never reconfigured; no global registry growth.
- JSON and `save_txt("w")` writes never leave a truncated file; failures leave the original intact.
- Invalid JSON data is rejected before anything touches disk.
- A corrupt `ErrorLogger` file is quarantined, never overwritten.
- `JsonlErrorLogger` loses no entries across threads, tasks or local processes.

**Known limits**

- `ErrorLogger` is not safe across processes; use `JsonlErrorLogger`.
- File locks are advisory and unreliable on NFS/SMB.
- `save_txt(mode="a")` is a plain append.
- `Benchmark(suppress_output=True)` is process-wide.
- `DateTime` uses fixed UTC offsets only (no zone names, no DST).
- `ErrorLogger` rewrites its whole file per call (by design; not for high volume).
