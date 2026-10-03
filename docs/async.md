
# Async API (`haashi.aio`)

The same class and method names as `haashi.utility`. Disk I/O is awaitable and runs in a worker thread via `asyncio.to_thread`, so it never blocks your event loop (FastAPI, Starlette, aiohttp, plain asyncio). No new dependencies.

```python
from haashi.aio import FileHandler, ErrorLogger, JsonlErrorLogger, Benchmark, Logger
```

Importing `haashi` does not import `asyncio`; the cost is opt-in via `haashi.aio`.

## What is async

| Name | In `haashi.aio` |
|---|---|
| `FileHandler` | `save_json`, `read_json`, `save_txt`, `read_txt`, `ensure_writable_path`, `ensure_readable_file` are `async`. `get_script_dir`, `get_parent_path`, `get_ancestor_by_name` stay **sync** (no real I/O). |
| `ErrorLogger` | `log_error`, `view_error_entries`, `clear_errors` are `async` |
| `JsonlErrorLogger` | `log_error`, `view_error_entries`, `clear_errors` are `async` |
| `Benchmark` | `measure_time` is `async` |
| `Logger`, `DateTime`, `Colors`, all exceptions | Re-exported **unchanged** (same objects as in `haashi.utility`). Logging a line is fast and needs no `await`. |

Signatures match the sync classes parameter-for-parameter, in the same order. A test enforces this. The single intentional difference: `Benchmark.measure_time(suppress_output=False)` (see below).

## FileHandler

```python
fh = FileHandler()
await fh.save_json({"a": 1}, "data/a.json")
data = await fh.read_json("data/a.json")
await fh.save_txt("hello", "notes.txt")
text = await fh.read_txt("notes.txt")
```

Errors propagate as the same exception types as the sync API. Concurrency:

```python
await asyncio.gather(*(fh.save_json({"i": i}, f"out/{i}.json") for i in range(100)))
```

Writes to different files are independent; concurrent writes to the same file are each atomic, last write wins.

## ErrorLogger and JsonlErrorLogger

```python
errors = JsonlErrorLogger(log_dir="/var/log/myapp", max_bytes=5_000_000)

try:
    await handle_request()
except Exception as exc:
    await errors.log_error(exc, context="POST /orders")
    raise
```

Both reuse the **same locks** as the sync classes (process-wide `RLock`; plus the OS file lock for JSONL), so:

- `asyncio.gather` over many `log_error` calls loses nothing.
- Mixing sync and async callers in one process is safe.
- Several worker processes can share one JSONL log.

On servers pass `confirm=False` to `clear_errors`; `confirm=True` needs a terminal.

## Benchmark

```python
bench = Benchmark()

async def fetch():
    await asyncio.sleep(0.01)

per_call = await bench.measure_time(fetch, run_times=10, repeat_times=3)
```

- Each run `await`s the function's result if it is awaitable.
- Plain functions work but run **on the event loop** and block it while timed.
- `suppress_output` defaults to **`False`**, unlike the sync version, because silencing stdout/stderr/logging is process-wide and would mute every other request in a running server. Enable it only in scripts.
- Timing uses `time.perf_counter()` per batch; the fastest batch wins, as in the sync version.
- Errors are wrapped in `BenchmarkError`; validation errors match the sync class.

## Under the hood

Each async class holds a sync instance (`self._sync`) and delegates with `asyncio.to_thread`, so atomicity, locking and validation are identical. Path helpers on `FileHandler` resolve the start directory *before* delegating so that caller detection still points at your file. Cancellation: if a task is cancelled while a worker thread is mid-write, the thread finishes its (atomic) operation; the file is never left half-written.

## When to use which

| You're writing | Import from |
|---|---|
| Script, CLI, notebook | `haashi.utility` |
| FastAPI / Starlette / aiohttp / asyncio code | `haashi.aio` |
| Sync code inside a thread pool | `haashi.utility` |
