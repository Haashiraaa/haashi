# Changelog

All notable changes to haashi are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


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

### Fixed
- `ErrorLogger` is now thread-safe: concurrent `log_error` calls no longer lose
  entries or corrupt the log.
- JSON/TXT writes and the error log are written atomically, so a crash
  mid-write cannot leave a truncated file.
- `Logger` no longer leaks into the global logging registry, so creating one
  per request is safe.
- A corrupted error log is moved to `<name>.corrupt` instead of being
  overwritten.


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
  Python 3.10-3.13, plus a build-and-install smoke test.
