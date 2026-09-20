# Changelog

All notable changes to haashi are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
