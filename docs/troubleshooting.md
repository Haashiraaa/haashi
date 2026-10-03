
# Troubleshooting

## Error logs

**My error log didn't appear where I expected.**
By default it goes to `logs/errors_log.json` (or `.jsonl`) next to the *main script*. If that script lives in site-packages or a scripts/bin directory (console script, `python -m ...`), or there is no main script (REPL, notebook), the **current directory** is used instead. Set `log_dir` to be explicit. `log_error` returns the exact path it wrote.

**`clear_errors` raised `LoggingError`.**
`confirm=True` needs an interactive terminal. Pass `confirm=False` in scripts, CI, servers and cron.

**`RuntimeWarning: Corrupted error log`.**
`ErrorLogger` couldn't parse its file. It was moved to `<name>.corrupt` and a fresh log started. Inspect or delete the backup. (Common cause: several *processes* sharing an `ErrorLogger` file. Switch to `JsonlErrorLogger`.)

**`RuntimeWarning: Skipped N unreadable line(s)`.**
`JsonlErrorLogger` found lines that aren't valid JSON, typically one cut short by a hard kill mid-write. They are skipped; the rest is intact.

**Entries are missing with several gunicorn/uvicorn workers.**
You are using `ErrorLogger`, which isn't coordinated across processes. Use `JsonlErrorLogger` with a shared local `log_dir`.

**`LoggingError: Timed out after ...s waiting for lock`.**
Another process held the log's lock longer than `lock_timeout` (default 10 s). Raise `lock_timeout`, or check for a stuck process. Locks are released automatically if the holder crashes, so a persistent timeout means a live process is holding it.

**A `.lock` file appeared next to my log.**
Expected. It is the cross-process lock for `JsonlErrorLogger`. It is never renamed or deleted; keep it, and exclude it from log shipping globs if needed.

**JSONL log is huge.**
`max_bytes=None` (the default) never rotates. Set `max_bytes` and `backups`.

**Locking misbehaves on a shared network drive.**
Advisory file locks are unreliable on NFS/SMB. Use a local directory per host.

**Permission denied writing logs.**
The service user can't write to `log_dir`. Fix permissions, or on read-only systems (Lambda) use `/tmp`.

## FileHandler

**`save_json` raised `InvalidJsonFormatError`.**
Your data contains something JSON can't represent (a `set`, a custom object, `NaN`, a cycle). Convert first (`sorted(my_set)`). Nothing was written and any existing file is untouched.

**Non-ASCII characters look escaped in my JSON file.**
Expected: `save_json` writes ASCII-safe JSON. `read_json` restores the original text exactly.

**`get_parent_path` / `get_ancestor_by_name` start from the wrong place.**
They start from the *caller's* file. In a REPL/notebook there is no file, so the cwd is used. Pass `start_path=` explicitly.

**A stray `.name.<pid>.<id>.tmp` file exists.**
A process was killed between writing the temp file and swapping it in. The target is intact (old content). Delete the temp file.

**Appending from multiple threads produced garbled lines.**
`save_txt(mode="a")` is a plain append. Use `JsonlErrorLogger` for concurrent logging.

## Logger

**Logs contain weird `\033[...` characters.**
You forced `color=True`, or the stream was a TTY when captured. Remove the override or use `color=False`.

**No colors on my terminal.**
`NO_COLOR` is set, or stderr isn't a TTY (piped, IDE console). Force with `color=True`.

**`logger.exception()` raised `LoggingError`.**
It must be called inside an `except` block.

**`save_to_json=True` raised `LoggingError`.**
You didn't pass `exception=`. Use `logger.exception(...)` inside `except`, or pass the exception.

**Debug messages don't show.**
The default level is `WARNING`. Use `Logger(level=logging.DEBUG)`.

## Benchmark

**Output or logs disappeared.**
`suppress_output=True` (the sync default) silences stdout/stderr/logging during timing. Pass `suppress_output=False`.

**Async benchmark blocks my loop.**
You passed a plain function; it runs on the loop. Pass a coroutine function, or benchmark in a script.

**Timings vary a lot.**
Increase `warmup_times`, `run_times` and `repeat_times`. The fastest batch is reported, which already filters most noise.

## Async

**`TypeError: object ... can't be used in 'await' expression`.**
You imported from `haashi.utility` but used `await`. Import from `haashi.aio`.

**`RuntimeWarning: coroutine ... was never awaited`.**
An `haashi.aio` method was called without `await`.

## Installation

**`import haashi` is slow.**
It shouldn't be: measure with `python -X importtime -c "import haashi" 2> imports.txt && tail -n 3 imports.txt`. Importing individual classes loads only their submodules.

**pip installs extra packages.**
It shouldn't: haashi has no runtime dependencies. `pip install "haashi[dev]"` adds development tools only.
