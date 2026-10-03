
# Deployment recipes

## CLI script

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

Errors land in `logs/errors_log.json` next to your script. If the CLI is installed with pip (a console script), the script lives in an installed location and haashi falls back to the **current directory**; set `log_dir` explicitly for predictable behavior.

## FastAPI, single process

```python
from fastapi import FastAPI
from haashi.aio import FileHandler, JsonlErrorLogger, Logger

app = FastAPI()
logger = Logger()
errors = JsonlErrorLogger(log_dir="/var/log/myapp", max_bytes=5_000_000, backups=5)
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

## Multiple workers (gunicorn / uvicorn `--workers`)

Each worker is a separate process, so the log must be multi-process safe. Use `JsonlErrorLogger` and point every worker at the **same** `log_dir`:

```python
# app.py, imported by every worker
from haashi.utility import Logger, JsonlErrorLogger

errors = JsonlErrorLogger("/var/log/myapp", max_bytes=10_000_000, backups=5)
logger = Logger(error_logger=errors)
```

```bash
uvicorn app:app --workers 4
gunicorn app:app -k uvicorn.workers.UvicornWorker -w 4
```

Requirements and caveats:

- All workers must be on the **same host** and a **local filesystem**. Advisory locks don't work reliably on NFS/SMB.
- A lock file `errors_log.jsonl.lock` appears next to the log. Leave it alone.
- Rotation happens under the lock, so workers never fight over `.1`/`.2`.
- `lock_timeout` (default 10 s) bounds how long a worker waits for the log. If it expires, `log_error` raises `LoggingError`, so in a request handler wrap the call so a logging hiccup can't mask the original error.

Don't use `ErrorLogger` here: it isn't coordinated across processes and can lose entries.

## Choosing the log directory

| Environment | `log_dir` |
|---|---|
| Linux service | `/var/log/<app>` (create it and grant write access to the service user) |
| systemd | `LogsDirectory=<app>` → `/var/log/<app>` |
| User-level app | `~/.local/state/<app>` (`~` is expanded) |
| Container | A mounted volume, e.g. `/var/log/myapp` |
| Tests | `tmp_path` |

## AWS Lambda / read-only filesystems

The code directory is read-only. Write to `/tmp`:

```python
from haashi.utility import JsonlErrorLogger, Logger

errors = JsonlErrorLogger(log_dir="/tmp/logs", max_bytes=1_000_000, backups=1)
logger = Logger(error_logger=errors)
```

`/tmp` is not durable across cold starts. Also send important errors to CloudWatch (stderr already goes there).

## Docker / containers

Containers want logs on stderr, which `Logger` already does. For persisted error entries, mount a volume and point `log_dir` at it. Set `NO_COLOR=1`, or rely on TTY detection, to keep container logs free of ANSI codes. Make sure the container user can write to the volume.

## systemd / cron jobs

No TTY means no color and `clear_errors(confirm=True)` raises `LoggingError`. Use `confirm=False`.

## Tests

```python
def test_logs_errors(tmp_path):
    errors = JsonlErrorLogger(log_dir=tmp_path)
    errors.log_error(ValueError("x"))
    assert len(errors.view_error_entries()) == 1
```

- Point everything at pytest's `tmp_path`, or pass `log_dir`/`use_script_dir=False` so tests don't write into your repo.
- Capture console output with `capsys` (`Logger` writes to stderr).
- Use `-W error::RuntimeWarning` in specific tests if you want corrupt-log quarantines to fail loudly.

## Production checklist

- [ ] `log_dir` set explicitly and writable by the service user
- [ ] `JsonlErrorLogger` if more than one process writes the log
- [ ] `max_bytes` and `backups` set so the log can't fill the disk
- [ ] `clear_errors(confirm=False)` anywhere non-interactive
- [ ] `haashi.aio` classes used inside async handlers
- [ ] Log directory on a local filesystem (not NFS/SMB)
