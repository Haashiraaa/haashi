# Changelog

All notable changes to haashi are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


## [1.3.1] - 2026-10-03 - Lock Timeout & Cheaper Reads

### Fixed
- `JsonlErrorLogger(lock_timeout=...)` is now enforced on POSIX as well as Windows. Previously a worker holding the lock indefinitely could stall every other worker; waiters now give up with `LoggingError` after `lock_timeout` seconds.
- `haashi.aio` is now exposed at the top level, so it can be accessed directly as `haashi.aio` in addition to explicit imports such as `from haashi.aio import FileHandler`.
- `import haashi` no longer imports typing. 

### Changed
- `JsonlErrorLogger.view_error_entries(limit=N)` now reads each file backwards and stops after `N` valid entries instead of loading the whole log and its backups. Cost is proportional to `N`, not the log size.
- `lock_timeout` is validated (`ValueError` if negative).
- README rewritten as a high-level overview; documentation split into focused pages under `docs/` and updated for `JsonlErrorLogger`, the cross-process lock and the `ErrorWriter` protocol.

## [1.3.0] - 2026-10-03 - JsonlErrorLogger for Backends

### Added
- `JsonlErrorLogger`: an append-only alternative to `ErrorLogger` that writes
  one JSON object per line. No read or rewrite per call, so cost stays flat
  as the log grows; safe for threads, async tasks and multiple worker
  processes sharing one file (cross-process file lock: `fcntl` on POSIX,
  `msvcrt` on Windows). Size-based rotation via `max_bytes` / `backups`,
  optional `fsync`, same method names as `ErrorLogger`. Available as
  `haashi.utility.JsonlErrorLogger` and, awaitable, `haashi.aio.JsonlErrorLogger`.
- `Logger(error_logger=...)` now accepts any object with a compatible
  `log_error` method, including `JsonlErrorLogger`.


## [1.2.0] - 2026-10-01 - Logger.critical & Documentation

### Added
- `Logger.critical()`: log fatal-level messages. Takes the same arguments as
  `Logger.error()` (including `exception`, `save_to_json`, `context`) and is
  styled like errors. Also available from `haashi.aio`, which re-exports `Logger`.
- `docs/DOCUMENTATION.md`: full user guide and reference covering every class,
  path-resolution rules, atomic writes, thread-safety, the async API, recipes
  (CLI, FastAPI, AWS Lambda, Docker, tests), troubleshooting and an API cheat sheet.

### Changed
- README rewritten to match the code exactly: documents atomic writes,
  thread-safety, `log_dir`, corrupt-log quarantine (`<name>.corrupt`), the
  installed-location fallback for script-relative paths, the full package layout
  and the real `dev` extras. It now warns that `Benchmark(suppress_output=True)`
  is process-wide and shows how to run on read-only filesystems such as AWS Lambda.
- `Logger.error()` and `Logger.critical()` share one implementation.
- Release workflows: `release.yml` and `changelog.yml` now use the same
  changelog-heading check (`[1.2.0]` and `[v1.2.0]` are both accepted), and
  leftover editing notes were removed from `publish.yml`.

### Fixed
- The 1.0.0 changelog entry now says CI covers Python 3.10-3.14, matching the
  CI matrix and package classifiers.
- Removed a redundant `return` in script-directory detection.


## [1.1.0] - 2026-09-30 - Backend & Async Support

### Added
- `haashi.aio`: async twins of `FileHandler`, `ErrorLogger` and `Benchmark` with
  the same class and method names. Disk IO runs in a worker thread
  (`asyncio.to_thread`), so it never blocks the event loop; no new dependencies.
  `Logger`, `DateTime`, `Colors` and all exceptions are re-exported unchanged.
  Importing `haashi` does not import `asyncio`; the cost is opt-in.
- `ErrorLogger(log_dir=...)`: choose the directory error logs are written to
  (relative paths resolve under it; absolute paths still win). Intended for
  servers, where "the script's directory" is the server's entry point.
- `Logger(error_logger=...)`: default `ErrorLogger` used by `save_to_json=True`.


## [1.0.1] - 2026-09-30 - Backend Safety

### Fixed
- `ErrorLogger` is now thread-safe: concurrent `log_error` calls no longer lose entries or corrupt the log.
- `FileHandler.save_json` / `save_txt(mode="w")` and the error log are written atomically, so a crash mid-write can't leave a truncated file.
- `Logger` no longer leaks into the global logging registry, so creating one per request is safe.
- A corrupted error log is moved to `<name>.corrupt` instead of being overwritten.



## [1.0.0] - 2026-09-20 - Initial Release

### Added
- `Logger` - console logging with per-instance levels, output colored by level
  via the `Colors` class (terminal only; respects `NO_COLOR`; override with
  `color=True/False`), `exception()` for logging the active exception with its
  traceback, and optional JSON persistence of errors.
- `ErrorLogger` - rotating JSON error log with `log_error`,
  `view_error_entries` and `clear_errors`. All three resolve the log file the
  same way, so what is written is what is read and cleared.
- `FileHandler` - JSON/TXT read and write, validated before anything touches
  disk, plus script-relative path helpers (`get_script_dir`,
  `get_parent_path`, `get_ancestor_by_name`). Accepts `str`, `Path` or any
  `os.PathLike`.
- `ScreenUtil` (loading animation, text wrapping), `Colors` (ANSI codes and
  level helpers), `DateTime` (timezone-aware current time, UTC-12 to UTC+14,
  fractional offsets allowed) and `Benchmark` (warmup + `timeit`-based timing).
- Exception hierarchy rooted at `UtilityError`.
- Lazy loading in `haashi.utility`: submodules are imported on first use.
- Zero runtime dependencies, full type hints, and a `py.typed` marker
  (PEP 561).
- Test suite, and CI covering ruff, pyright (strict) and pytest on
  Python 3.10-3.14, plus a build-and-install smoke test.
