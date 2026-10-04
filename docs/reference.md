
# Reference

## Exceptions

```
UtilityError
├── FileOperationError        FileHandler read/write/path failures
├── InvalidJsonFormatError    data can't be represented as (strict) JSON
├── LoggingError              Logger / error-logger misuse or lock timeout
├── BenchmarkError            the benchmarked function raised
├── InvalidFunctionError      a non-callable was passed to Benchmark
└── BenchmarkTimeoutError     reserved for future timeout support
```

| Exception | Raised by | Typical cause |
|---|---|---|
| `FileOperationError` | `FileHandler.*` | permission denied, path is a directory, invalid JSON on read, undecodable text |
| `InvalidJsonFormatError` | `save_json` | sets, custom objects, `NaN`/`Infinity`, circular references |
| `LoggingError` | `Logger.error/critical`, `clear_errors`, JSONL lock | `save_to_json=True` without `exception`; `exception()` outside `except`; `confirm=True` without a terminal; cross-process lock timeout |
| `BenchmarkError` | `Benchmark.measure_time` | your function raised |
| `InvalidFunctionError` | `Benchmark.measure_time` | argument isn't callable |
| `BenchmarkTimeoutError` | (nothing yet) | reserved |

Built-ins also raised: `FileNotFoundError` (missing files), `ValueError` (bad numeric/mode arguments), and `RuntimeWarning` (corrupt `ErrorLogger` file quarantined; unreadable JSONL lines skipped).

`Logger.exception()` raises `LoggingError` outside an `except` block. All exceptions are importable from both `haashi.utility` and `haashi.aio`.

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

## Type aliases

Defined in `haashi.utility._types` (internal, but useful for annotations):

```python
PathLike = str | Path | os.PathLike[str]
JSONType = str | int | float | bool | None | list[JSONType] | dict[str, JSONType]

class ErrorWriter(Protocol):
    def log_error(
        self, exception: BaseException, context: str | None = None,
        path: PathLike | None = None, use_script_dir: bool = True,
    ) -> Path: ...
```

## Files and defaults

| Item | Default |
|---|---|
| `ErrorLogger` file | `logs/errors_log.json` |
| `JsonlErrorLogger` file | `logs/errors_log.jsonl` |
| JSONL cross-process lock | `<log file>.lock` |
| JSONL backups | `<log file>.1`, `.2`, ... |
| Quarantined corrupt JSON log | `<name>.corrupt`, `.corrupt.1`, ... |
| Atomic-write temp file | `.<name>.<pid>.<thread-id>.tmp` (removed on completion or failure) |

## Full signatures

```python
# Logger
Logger(level=WARNING, color=None, error_logger=None)
  .debug(msg) .info(msg) .warning(msg)
  .error(message="Error occurred!", error_logger=None, path=None, exception=None,
         save_to_json=False, use_script_dir=True, context=None)
  .critical(message="Critical error!", error_logger=None, path=None, exception=None,
            save_to_json=False, use_script_dir=True, context=None)
  .exception(message="Exception occurred!", error_logger=None, save_to_json=False,
             path=None, use_script_dir=True, context=None)

# ErrorLogger
ErrorLogger(log_dir=None)
  .log_error(exception, context=None, path=None, use_script_dir=True,
             utc_offset_hours=0, max_entries=100) -> Path
  .view_error_entries(path=None, limit=10, use_script_dir=True) -> list
  .clear_errors(path=None, use_script_dir=True, *, confirm=True) -> bool

# JsonlErrorLogger
JsonlErrorLogger(log_dir=None, *, max_bytes=None, backups=3, fsync=False, lock_timeout=10.0)
  .log_error(exception, context=None, path=None, use_script_dir=True,
             utc_offset_hours=0) -> Path
  .view_error_entries(path=None, limit=10, use_script_dir=True) -> list
  .clear_errors(path=None, use_script_dir=True, *, confirm=True) -> bool

# FileHandler
FileHandler(logger=None)
  .save_json(data, path, indent=4)
  .read_json(path)
  .save_txt(data, path, mode="w", add_newline_prefix=False)
  .read_txt(path)
  .ensure_writable_path(path)        .ensure_readable_file(path)
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
Colors.debug / info / warning / error / success / header (text)

# Benchmark
Benchmark(logger=None)
  .measure_time(func, warmup_times=3, run_times=5, repeat_times=1, suppress_output=True) -> float

# haashi.aio: await everything except Logger, DateTime, Colors and FileHandler path helpers
FileHandler / ErrorLogger / JsonlErrorLogger / Benchmark   # same signatures
Benchmark.measure_time(..., suppress_output=False)          # default differs
```

## Validation rules at a glance

| Argument | Rule | Error |
|---|---|---|
| `utc_offset_hours` | -12 ≤ x ≤ 14 | `ValueError` |
| `max_entries` | ≥ 1 | `ValueError` |
| `limit` (view) | ≥ 1 or `None` | `ValueError` |
| `max_bytes` | ≥ 1 or `None` | `ValueError` |
| `backups` | ≥ 0 | `ValueError` |
| `lock_timeout` | ≥ 0 | `ValueError` |
| `run_times`, `repeat_times` | ≥ 1 | `ValueError` |
| `warmup_times` | ≥ 0 | `ValueError` |
| `save_txt` `mode` | `"w"` or `"a"` | `ValueError` |
| `levels_up` | ≥ 0 | `ValueError` |

## Compatibility

- Python 3.10, 3.11, 3.12, 3.13, 3.14
- Linux, macOS, Windows (CI matrix)
- Semantic Versioning; see the [changelog](../CHANGELOG.md)
