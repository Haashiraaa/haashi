
# Contributing

## Setup

```bash
git clone https://github.com/Haashiraaa/haashi.git
cd haashi
pip install -e ".[dev]"
ruff check . && pyright && pytest
```

All three must pass. CI runs them on Linux, macOS and Windows across Python 3.10 to 3.14 (ruff and pyright on Ubuntu only), and the **publish workflow re-runs them before anything is uploaded**.

## Project principles

1. **Zero runtime dependencies.** Discuss in an issue before proposing one.
2. **Lazy and cheap to import.** Don't add module-level imports to `haashi/__init__.py` or `utility/__init__.py`; use the lazy table.
3. **Correct under concurrency.** If a feature touches shared files, define its thread and process story and test it.
4. **Strict types.** `src/` is checked by pyright in strict mode.
5. **Errors are `UtilityError` subclasses** (or the obvious built-in); never print-and-swallow.
6. **Async parity.** Anything with an async twin stays in step.

## Checklists

**Adding a method to a sync class that has an async twin**

- [ ] Implement it in `haashi.utility`.
- [ ] Add the async method to the twin in `haashi.aio` with identical parameter names, order and defaults.
- [ ] `tests/aio/test_aio.py` parity tests pass (add an allowed difference only if justified).

**Adding a public name**

- [ ] Add it to `__all__`, `_LAZY` and the `TYPE_CHECKING` import block in `utility/__init__.py` (a test fails if they drift).
- [ ] Re-export from `haashi.aio` if it is safe to use in async code.
- [ ] Document it in `docs/` and add it to [Reference](reference.md).

**Adding an error persister**

- [ ] Satisfy the `ErrorWriter` protocol in `_types.py`.
- [ ] Reuse `resolve_log_path`, so `log_dir`, `use_script_dir` and absolute paths behave the same.
- [ ] Test threads, and processes if it claims multi-process safety (use the `spawn` start method).

## Testing notes

- Use `tmp_path`; never write into the repo.
- Subprocess tests (import cost, lazy loading) run in fresh interpreters so they see real import behavior.
- Multi-process tests use `multiprocessing.get_context("spawn")` for cross-platform parity. Worker functions must be module-level.
- Patch `haashi.utility._paths.detect_script_dir` to avoid depending on where pytest was launched.
- Windows: file locking and `os.replace` retries behave differently; run the suite there before touching `_atomic.py` or `_filelock.py`.

## Style

- Docstrings on public functions with an example when it helps (Google-style `Args:` / `Raises:`).
- Line length 100 (ruff); ruff rules `E, F, I, UP, B, SIM`.
- Comments explain *why*, not what.

## Documentation

- `README.md` is the pitch: benefits, a short tour, links. No deep detail.
- `docs/` is the technical reference. Keep claims verifiable against the source, and update the relevant page in the same PR as the code.
- User-visible changes go in `CHANGELOG.md` under `## [Unreleased]`.

## Releasing

Releases are tag-driven; see [RELEASING.md](../RELEASING.md). A PyPI version can never be re-uploaded, so fix forward with the next patch.
