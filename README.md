# haashi documentation

Technical documentation for **haashi** `1.3.x`. For the overview and pitch, see the [project README](../README.md).

These pages explain *how things behave and why*, not just signatures. Every statement here is checked against the source in `src/haashi/`.

## Reading paths

| I want to... | Read |
|---|---|
| Install and run something in 5 minutes | [Getting started](getting-started.md) |
| Understand the guarantees (atomicity, locks, safety) | [Architecture](architecture.md) |
| Log to the console and persist errors | [Logger](logger.md) → [Error logging](error-logging.md) |
| Run a backend with multiple workers | [Error logging](error-logging.md#jsonlerrorlogger) → [Deployment](deployment.md) |
| Read/write JSON and text safely | [FileHandler](filehandler.md) |
| Use it from FastAPI / aiohttp / asyncio | [Async API](async.md) |
| Time a function | [Benchmark](benchmark.md) |
| Look up an exception or signature | [Reference](reference.md) |
| Fix something that isn't working | [Troubleshooting](troubleshooting.md) |
| Contribute or cut a release | [Contributing](contributing.md), [RELEASING](../RELEASING.md) |

## Page index

1. [Getting started](getting-started.md)
2. [Architecture & guarantees](architecture.md)
3. [Logger](logger.md)
4. [Error logging: `ErrorLogger` and `JsonlErrorLogger`](error-logging.md)
5. [FileHandler](filehandler.md)
6. [Benchmark](benchmark.md)
7. [Utilities: `DateTime`, `ScreenUtil`, `Colors`](utilities.md)
8. [Async API (`haashi.aio`)](async.md)
9. [Deployment recipes](deployment.md)
10. [Reference](reference.md)
11. [Troubleshooting](troubleshooting.md)
12. [Contributing](contributing.md)

## Conventions

- `haashi.utility` is the synchronous API; `haashi.aio` mirrors it with awaitable I/O.
- Paths are `str`, `pathlib.Path` or any `os.PathLike[str]`.
- "Process-wide" means shared by every instance in one Python process.
- Examples assume `import logging` where `logging.INFO` etc. are used.
