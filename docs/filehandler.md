
# FileHandler

JSON and text I/O with validation, atomic writes and script-relative path helpers.

```python
FileHandler(logger=None)
```

`logger` is an optional [`Logger`](logger.md) used for debug/warning messages (default: a warning-level `Logger`). Paths may be `str`, `pathlib.Path` or any `os.PathLike[str]`.

## JSON

### `save_json(data, path, indent=4)`

Saves JSON-serializable data, overwriting the target. Parent directories are created.

```python
fh.save_json({"status": "ok", "items": [1, 2, 3]}, "data/output.json")
```

- **Validated first.** `data` is serialized *before* anything touches disk. If it can't be serialized, nothing is written and an existing file is left untouched.
- **Strict JSON.** `NaN`/`Infinity` are rejected (`allow_nan=False`), as are sets, custom objects and circular references.
- **Atomic.** See [Architecture → Atomic writes](architecture.md#atomic-writes).
- **ASCII-safe output.** Non-ASCII text is written escaped (`"Ọlá"` → `"\u1ecc\u00e1"`) and round-trips exactly through `read_json`.

Raises `InvalidJsonFormatError` (bad data) or `FileOperationError` (write failed).

### `read_json(path)`

```python
data = fh.read_json("data/output.json")
```

Raises `FileNotFoundError` (missing), `FileOperationError` (not a file, invalid JSON, undecodable UTF-8, I/O error).

## Text

### `save_txt(data, path, mode="w", add_newline_prefix=False)`

```python
fh.save_txt("first line", "notes.txt")
fh.save_txt("\nmore", "notes.txt", mode="a")
fh.save_txt("more", "notes.txt", mode="a", add_newline_prefix=True)
```

| Parameter | Description |
|---|---|
| `mode` | `"w"` overwrite (**atomic**) or `"a"` append (**not atomic**). Anything else raises `ValueError`. |
| `add_newline_prefix` | Write `\n` before the content. Handy when appending to a file that doesn't end with a newline. |

UTF-8. Raises `FileOperationError` on I/O failure.

### `read_txt(path)`

Returns the file as a string. Raises `FileNotFoundError`, `FileOperationError`.

## Filesystem checks

| Method | Does | Raises |
|---|---|---|
| `ensure_writable_path(path) -> Path` | Creates parent directories, returns the path | `FileOperationError` |
| `ensure_readable_file(path) -> Path` | Returns the path if it is an existing file | `FileNotFoundError`; `FileOperationError` if it exists but isn't a file |

## Script-relative helpers

For scripts that must find project files no matter where they're launched from.

### `get_script_dir() -> Path`

Directory of the executed main script, with the cwd fallback described in [Path resolution](architecture.md#path-resolution).

### `get_parent_path(levels_up=1, start_path=None) -> Path`

Climbs `levels_up` directories above the **caller's file** (or above `start_path`).

```python
# script: my-project/src/scripts/process.py
fh.get_parent_path(levels_up=2)   # /home/user/my-project
fh.get_parent_path(levels_up=0)   # /home/user/my-project/src/scripts
```

Raises `ValueError` if `levels_up < 0`. In a REPL/notebook there is no `__file__`, so the cwd is the starting point.

### `get_ancestor_by_name(folder_name, start_path=None, max_levels=10) -> Path | None`

Finds an ancestor directory by exact, **case-sensitive** name. More robust than counting levels. Checks the start directory and up to `max_levels - 1` parents; returns `None` (and logs a warning) if not found.

```python
root = fh.get_ancestor_by_name("my-project")
if root is None:
    raise SystemExit("run this from inside my-project")
config = fh.read_json(root / "config.json")
```

> **Caller detection.** These helpers inspect the call stack to find *your* file. In `haashi.aio`, the wrapper resolves the start directory before delegating, so they still point at your code, not at haashi's.

## Concurrency

- Writes to **different** files: independent and safe.
- Writes to the **same** file: each write is atomic; last write wins. No interleaving or truncation.
- `save_txt(mode="a")`: plain append; concurrent appenders aren't guaranteed to be intact. For concurrent logging use [`JsonlErrorLogger`](error-logging.md#jsonlerrorlogger).
