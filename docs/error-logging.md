
# Error logging

haashi ships two persistent error loggers with the same method names (`log_error`, `view_error_entries`, `clear_errors`). Both are accepted by `Logger(error_logger=...)`.

## Choosing

| | [`ErrorLogger`](#errorlogger) | [`JsonlErrorLogger`](#jsonlerrorlogger) |
|---|---|---|
| Format | Single JSON array, pretty-printed | One JSON object per line (JSONL) |
| Write cost | Read + rewrite + `fsync` of the whole file | One append |
| Threads / asyncio | Safe | Safe |
| Multiple processes | **Not coordinated** | **Safe** (cross-process file lock) |
| Retention | Last `max_entries` entries | Size rotation: `max_bytes` + `backups` |
| Default file | `logs/errors_log.json` | `logs/errors_log.jsonl` |
| Human-readable | Yes, open in any editor | Yes, but one line per entry (`jq`, `grep`) |
| Use for | Scripts, CLIs, occasional errors | Backends, error bursts, gunicorn/uvicorn workers |

Rule of thumb: **scripts → `ErrorLogger`; servers → `JsonlErrorLogger`.**

## Entry format

Both write the same fields:

```json
{
    "timestamp": "2026-10-03T14:05:11.123456+01:00",
    "type": "ValueError",
    "message": "boom",
    "context": "math",
    "traceback": "Traceback (most recent call last): ..."
}
```

`context` is `"unspecified"` when omitted. `timestamp` is ISO 8601 with the offset given by `utc_offset_hours` (-12 to +14).

## Where the file goes

Resolution is identical for both and is shared with reads and clears, so what is written is what is read and cleared. Full table: [Architecture → Path resolution](architecture.md#path-resolution). In short:

- absolute `path` → used as given
- relative `path` + `log_dir` → `log_dir / path`
- no `path` + `log_dir` → `log_dir / <default name>`
- otherwise next to the running script (or cwd, see `use_script_dir` and the installed-location fallback)

`log_dir` expands `~`. **Set it on servers.**

---

## ErrorLogger

```python
ErrorLogger(log_dir=None)
```

### `log_error`

```python
errors.log_error(
    exception, context=None, path=None, use_script_dir=True,
    utc_offset_hours=0, max_entries=100,
) -> Path
```

Appends an entry and returns the file path. Only the most recent `max_entries` are kept.

**Raises** `ValueError` if `max_entries < 1` or the offset is out of range.

### `view_error_entries`

```python
errors.view_error_entries(path=None, limit=10, use_script_dir=True) -> list
```

Most recent `limit` entries, oldest first within the slice; `limit=None` returns everything. Raises `ValueError` if `limit < 1`. A missing file returns `[]`.

### `clear_errors`

```python
errors.clear_errors(path=None, use_script_dir=True, *, confirm=True) -> bool
```

Deletes the log; `True` if a file was deleted. `confirm=True` prompts `[y/N]` (only `y`/`yes` proceed) and **requires an interactive terminal**; otherwise it raises `LoggingError` instead of hanging. Pass `confirm=False` in scripts, CI and servers.

### Corrupt logs

If the file can't be parsed, or isn't a JSON list, it is **not overwritten**:

1. Moved to `<name>.corrupt` (or `.corrupt.1`, `.corrupt.2`, ...).
2. A `RuntimeWarning` is emitted.
3. A fresh log starts.

This also happens when a corrupt file is *read* through `view_error_entries`.

### Concurrency and cost

A process-wide `RLock` serializes the read-modify-write, so threads and asyncio tasks lose nothing. Separate **processes** can interleave read-modify-write cycles and lose entries; use `JsonlErrorLogger` for that. Each call rewrites and `fsync`s the whole file, which is fine for occasional errors and wrong for error storms.

---

## JsonlErrorLogger

```python
JsonlErrorLogger(
    log_dir=None, *,
    max_bytes=None,
    backups=3,
    fsync=False,
    lock_timeout=10.0,
)
```

| Parameter | Description |
|---|---|
| `log_dir` | Directory relative paths resolve under (`~` expanded). |
| `max_bytes` | Rotate when a write would push the file past this size. `None` never rotates (unbounded growth). Must be `>= 1`. |
| `backups` | Rotated files to keep (`>= 0`). `0` discards the log on rotation. |
| `fsync` | `fsync` every entry. Survives power loss, but slow. Default off: entries still survive a process crash. |
| `lock_timeout` | Seconds to wait for the cross-process lock before raising `LoggingError` (`>= 0`; `0` tries once). Enforced on every platform. |

**Raises** `ValueError` for `max_bytes < 1`, `backups < 0` or `lock_timeout < 0`.

### `log_error`

```python
errors.log_error(
    exception, context=None, path=None, use_script_dir=True, utc_offset_hours=0,
) -> Path
```

One lock acquisition, one optional rotation, one append. There is no `max_entries`; retention is controlled by rotation.**Raises** `ValueError` (bad offset) or `LoggingError` (lock not acquired within `lock_timeout`). 

### `view_error_entries`

```python
errors.view_error_entries(path=None, limit=10, use_script_dir=True) -> list
```

Reads rotated backups too, oldest first, then returns the last `limit` (`None` for all). A missing log returns `[]` and **creates nothing**. Garbled lines (for example a line cut short by a hard crash) are skipped, with one `RuntimeWarning` reporting how many.

Reads newest-first from the end of each file and stops as soon as it has `limit` valid entries, so `limit=10` stays cheap on a very large log. Only `limit=None` reads everything. Skipped lines don't count toward `limit`, and the warning only counts garbled lines it actually reached.

### `clear_errors`

```python
errors.clear_errors(path=None, use_script_dir=True, *, confirm=True) -> bool
```

Deletes the live file **and all rotated backups** under the lock. Same `confirm` rules as `ErrorLogger`. The `.lock` file is left in place.

### Rotation walk-through

With `max_bytes=1_000_000, backups=2`:

```
errors_log.jsonl      (live, newest)
errors_log.jsonl.1    (previous)
errors_log.jsonl.2    (oldest kept)
```

When the live file would exceed 1 MB: `.1 → .2` (old `.2` dropped), live → `.1`, a new live file starts. Total disk use is bounded by about `(backups + 1) × max_bytes`.

### Multiple processes

```python
# every worker process runs this; all share one directory and one log
errors = JsonlErrorLogger("/var/log/myapp", max_bytes=5_000_000, backups=5)
```

Each append takes `_THREAD_LOCK` then the OS file lock on `errors_log.jsonl.lock`. Tests spawn 4 processes × 40 entries and 8 threads × 25 entries and assert nothing is lost. Limits: local filesystems only (see [Architecture](architecture.md#locking-model)).

### Reading the log outside Python

```bash
tail -n 20 /var/log/myapp/errors_log.jsonl | jq -r '[.timestamp,.type,.message] | @tsv'
grep '"context":"POST /orders"' /var/log/myapp/errors_log.jsonl | wc -l
```

---

## Using with `Logger`

```python
from haashi.utility import Logger, JsonlErrorLogger

logger = Logger(error_logger=JsonlErrorLogger("/var/log/myapp"))
logger.error("failed", exception=exc, save_to_json=True, context="job-42")
logger.critical("fatal", exception=exc, save_to_json=True)
```

## Async

`haashi.aio.ErrorLogger` and `haashi.aio.JsonlErrorLogger` wrap the sync classes with `asyncio.to_thread`, sharing the same locks, so mixing sync and async callers in one process is safe. See [Async API](async.md).
