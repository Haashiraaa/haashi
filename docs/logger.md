
# Logger

Console logging with optional persistence of errors.

```python
Logger(level=logging.WARNING, color=None, error_logger=None)
```

| Parameter | Description |
|---|---|
| `level` | Minimum level shown (`logging.DEBUG`, `INFO`, ...). Default `WARNING`. |
| `color` | `None`: color only on a terminal. `True` / `False` force it. |
| `error_logger` | Default persister used when `save_to_json=True`. Any [`ErrorWriter`](architecture.md#the-errorwriter-protocol): `ErrorLogger`, `JsonlErrorLogger`, or your own. |

Attributes: `logger.logger` (the underlying `logging.Logger`), `logger.error_logger` (default persister or `None`).

## Behavior

- **Independent.** Each instance owns a private `logging.Logger` named `haashi.<n>`; levels never affect other instances.
- **Nothing global.** The root logger is never touched, `propagate` is off, and instances aren't registered in Python's logger registry, so creating one per request is safe.
- **stderr.** Output goes to stderr as `[LEVEL] message`.

## Color rules

| Level | Style (via `Colors`) |
|---|---|
| DEBUG | dim cyan |
| INFO | bold blue |
| WARNING | bold yellow |
| ERROR, CRITICAL | bold red |

With `color=None`, color is used only when the stream is a terminal **and** [`NO_COLOR`](https://no-color.org) is unset. Files, pipes and CI stay plain. `color=True` forces color even if `NO_COLOR` is set; `color=False` never emits ANSI. The decision is made per record against the handler's *current* stream, and a missing or closed stream counts as "not a terminal".

## Methods

### `debug(message)`, `info(message)`, `warning(message)`

`message` may be any object (converted with `str`).

### `error(...)`

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

With `save_to_json=True` the exception is persisted and the console message gains a second line, `See <path> for details`, using the path the persister actually wrote.

**Persister selection**, in order: the per-call `error_logger`, then the one given to `Logger(...)`, then a default `ErrorLogger()` created on demand and cached on `logger.error_logger`.

`path` and `use_script_dir` are forwarded to the persister; see [path resolution](architecture.md#path-resolution).

**Raises** `LoggingError` if `save_to_json=True` but no `exception` was given.

### `critical(...)`

Same arguments and persistence behavior as `error()`, logged at `CRITICAL` (styled like errors, shown at every level). Default message: `"Critical error!"`. Use it for unrecoverable failures, typically right before exiting.

```python
try:
    connect_to_database()
except ConnectionError as exc:
    logger.critical("Database unreachable", exception=exc, save_to_json=True)
    raise SystemExit(1)
```

### `exception(...)`

Logs the exception currently being handled, **with traceback**, taken from `sys.exc_info()`.

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

> The parameter order differs from `error()` (`save_to_json` precedes `path`). Use keyword arguments.

```python
try:
    risky()
except Exception:
    logger.exception("risky() failed", save_to_json=True, context="job-42")
```

**Raises** `LoggingError` if called outside an `except` block.

## Using a custom persister

```python
from haashi.utility import Logger, JsonlErrorLogger

logger = Logger(error_logger=JsonlErrorLogger("/var/log/myapp"))
logger.error("failed", exception=exc, save_to_json=True)   # -> /var/log/myapp/errors_log.jsonl
```

Custom class: implement `log_error(exception, context=None, path=None, use_script_dir=True) -> Path`.

## Testing

`Logger` writes to stderr, so use `capsys` (`capsys.readouterr().err`). Output is uncolored under pytest because stderr isn't a TTY. Force with `color=True` to assert on ANSI output.
