import asyncio
import inspect
import json
import threading
from pathlib import Path

import pytest

from haashi import aio
from haashi.utility import Benchmark as SyncBenchmark
from haashi.utility import ErrorLogger as SyncErrorLogger
from haashi.utility import FileHandler as SyncFileHandler
from haashi.utility import JsonlErrorLogger as SyncJsonlErrorLogger

# ---- API parity: the whole point of "same names" ------------------------------

# name -> reason its signature intentionally differs from the sync class
EXPECTED_DIFFERENCES = {
    # default False in async
    ("Benchmark", "measure_time"): {"suppress_output"},
}

PAIRS = [
    ("FileHandler", SyncFileHandler, aio.FileHandler),
    ("ErrorLogger", SyncErrorLogger, aio.ErrorLogger),
    ("Benchmark", SyncBenchmark, aio.Benchmark),
    ("JsonlErrorLogger", SyncJsonlErrorLogger, aio.JsonlErrorLogger),
]


def _public_methods(cls: type) -> set[str]:
    return {
        n for n, v in vars(cls).items()
        if not n.startswith("_") and (inspect.isfunction(v) or isinstance(v, staticmethod))
    }


@pytest.mark.parametrize(("label", "sync_cls", "async_cls"), PAIRS)
def test_async_classes_expose_every_sync_method(
    label: str, sync_cls: type, async_cls: type
) -> None:
    assert _public_methods(async_cls) >= _public_methods(sync_cls), (
        f"{label}: aio is missing {_public_methods(sync_cls) - _public_methods(async_cls)}")


@pytest.mark.parametrize(("label", "sync_cls", "async_cls"), PAIRS)
def test_method_signatures_match_sync(label: str, sync_cls: type, async_cls: type) -> None:
    for name in _public_methods(sync_cls):
        sync_sig = inspect.signature(getattr(sync_cls, name))
        async_sig = inspect.signature(getattr(async_cls, name))
        differing = EXPECTED_DIFFERENCES.get((label, name), set())
        sync_order = list(sync_sig.parameters)
        async_order = list(async_sig.parameters)
        assert async_order[: len(sync_order)] == sync_order, (
            f"{label}.{name} parameter order differs: {sync_order} vs {async_order}")
        for pname, sp in sync_sig.parameters.items():
            ap = async_sig.parameters.get(pname)
            assert ap is not None, f"{label}.{name} lost parameter {pname!r}"
            assert ap.kind == sp.kind, f"{label}.{name}({pname}) kind changed"
            if pname not in differing:
                assert ap.default == sp.default, f"{label}.{name}({pname}) default changed"


def test_io_methods_are_coroutines_and_path_helpers_are_not() -> None:
    for name in ("save_json", "read_json", "save_txt", "read_txt",
                 "ensure_writable_path", "ensure_readable_file"):
        assert inspect.iscoroutinefunction(
            getattr(aio.FileHandler, name)), name
    for name in ("get_script_dir", "get_parent_path", "get_ancestor_by_name"):
        assert not inspect.iscoroutinefunction(
            getattr(aio.FileHandler, name)), name
    for name in ("log_error", "view_error_entries", "clear_errors"):
        assert inspect.iscoroutinefunction(
            getattr(aio.ErrorLogger, name)), name
    for name in ("log_error", "view_error_entries", "clear_errors"):
        assert inspect.iscoroutinefunction(
            getattr(aio.JsonlErrorLogger, name)), name
    assert inspect.iscoroutinefunction(aio.Benchmark.measure_time)


def test_reexports_are_the_same_objects_as_sync() -> None:
    from haashi.utility import Colors, DateTime, FileOperationError, Logger

    assert aio.Logger is Logger
    assert aio.DateTime is DateTime
    assert aio.Colors is Colors
    assert aio.FileOperationError is FileOperationError
    for name in aio.__all__:
        assert hasattr(aio, name), name


# ---- FileHandler ---------------------------------------------------------------

def test_file_roundtrip(tmp_path: Path) -> None:
    async def main() -> None:
        fh = aio.FileHandler()
        await fh.save_json({"a": [1, 2]}, tmp_path / "x" / "a.json")
        assert await fh.read_json(tmp_path / "x" / "a.json") == {"a": [1, 2]}
        await fh.save_txt("one", tmp_path / "t.txt", add_newline_prefix=False)
        await fh.save_txt("two", tmp_path / "t.txt", mode="a", add_newline_prefix=False)
        assert await fh.read_txt(tmp_path / "t.txt") == "onetwo"

    asyncio.run(main())


def test_errors_propagate_as_the_same_exception_types(tmp_path: Path) -> None:
    async def main() -> None:
        fh = aio.FileHandler()
        with pytest.raises(FileNotFoundError):
            await fh.read_json(tmp_path / "missing.json")
        with pytest.raises(aio.InvalidJsonFormatError):
            # fmt: off
            await fh.save_json({"s": {1}}, tmp_path / "bad.json") # type: ignore[reportArgumentType]
            # fmt: on
        assert not (tmp_path / "bad.json").exists()
        (tmp_path / "broken.json").write_text("{nope")
        with pytest.raises(aio.FileOperationError):
            await fh.read_json(tmp_path / "broken.json")

    asyncio.run(main())


def test_io_runs_off_the_event_loop_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[int] = []
    real = SyncFileHandler.save_json

    def spy(self: SyncFileHandler, *a: object, **k: object) -> None:
        seen.append(threading.get_ident())
        real(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(SyncFileHandler, "save_json", spy)

    async def main() -> int:
        await aio.FileHandler().save_json({"k": 1}, tmp_path / "t.json")
        return threading.get_ident()

    loop_thread = asyncio.run(main())
    assert seen and seen[0] != loop_thread


def test_event_loop_stays_responsive_during_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    real = SyncFileHandler.save_json

    def slow(self: SyncFileHandler, *a: object, **k: object) -> None:
        time.sleep(0.3)  # simulate a slow disk
        real(self, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(SyncFileHandler, "save_json", slow)

    async def main() -> int:
        ticks = 0

        async def heartbeat() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.02)
                ticks += 1

        beat = asyncio.create_task(heartbeat())
        await aio.FileHandler().save_json({"k": 1}, tmp_path / "s.json")
        beat.cancel()
        return ticks

    assert asyncio.run(main()) >= 3  # a blocked loop would tick ~0 times


def test_concurrent_writes_to_different_files(tmp_path: Path) -> None:
    async def main() -> None:
        fh = aio.FileHandler()
        await asyncio.gather(*(fh.save_json({"i": i}, tmp_path / f"{i}.json") for i in range(40)))
        results = await asyncio.gather(*(fh.read_json(tmp_path / f"{i}.json") for i in range(40)))
        assert results == [{"i": i} for i in range(40)]

    asyncio.run(main())


def test_path_helpers_still_see_the_users_file_not_the_wrapper() -> None:
    fh = aio.FileHandler()
    assert fh.get_parent_path(levels_up=0) == Path(__file__).resolve().parent
    assert fh.get_ancestor_by_name("tests") == Path(
        __file__).resolve().parents[1]


# ---- ErrorLogger ---------------------------------------------------------------

def test_gathered_log_error_calls_lose_nothing(tmp_path: Path) -> None:
    async def main() -> None:
        errors = aio.ErrorLogger(log_dir=tmp_path)
        await asyncio.gather(*(
            errors.log_error(ValueError(str(i)), max_entries=1000) for i in range(60)))
        assert len(await errors.view_error_entries(limit=None)) == 60

    asyncio.run(main())
    assert len(json.loads((tmp_path / "errors_log.json").read_text())) == 60


def test_sync_and_async_error_loggers_share_one_lock(tmp_path: Path) -> None:
    sync = SyncErrorLogger(log_dir=tmp_path)

    async def main() -> None:
        errors = aio.ErrorLogger(log_dir=tmp_path)

        def sync_worker() -> None:
            for i in range(20):
                sync.log_error(KeyError(f"s{i}"), max_entries=1000)

        thread = threading.Thread(target=sync_worker)
        thread.start()
        await asyncio.gather(*(errors.log_error(KeyError(f"a{i}"), max_entries=1000)
                               for i in range(20)))
        await asyncio.to_thread(thread.join)

    asyncio.run(main())
    assert len(json.loads((tmp_path / "errors_log.json").read_text())) == 40


def test_clear_errors_confirm_false(tmp_path: Path) -> None:
    async def main() -> None:
        errors = aio.ErrorLogger(log_dir=tmp_path)
        await errors.log_error(ValueError("x"))
        assert await errors.clear_errors(confirm=False) is True
        assert await errors.clear_errors(confirm=False) is False

    asyncio.run(main())


# ---- Benchmark -----------------------------------------------------------------

def test_benchmark_times_a_coroutine_function() -> None:
    calls = 0

    async def work() -> None:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)

    async def main() -> float:
        return await aio.Benchmark().measure_time(
            work, warmup_times=2, run_times=3, repeat_times=2)

    per_call = asyncio.run(main())
    assert calls == 2 + 3 * 2
    assert per_call >= 0.009 and per_call < 0.5   # was < 0.05


def test_benchmark_accepts_plain_functions() -> None:
    assert asyncio.run(aio.Benchmark().measure_time(
        lambda: sum(range(100)), run_times=2)) > 0


def test_benchmark_validation_and_error_wrapping() -> None:
    bench = aio.Benchmark()

    async def boom() -> None:
        raise RuntimeError("nope")

    async def main() -> None:
        with pytest.raises(ValueError):
            await bench.measure_time(boom, run_times=0)
        with pytest.raises(aio.InvalidFunctionError):
            await bench.measure_time("nope")  # type: ignore[arg-type]
        with pytest.raises(aio.BenchmarkError, match="nope"):
            await bench.measure_time(boom)

    asyncio.run(main())


def test_benchmark_does_not_silence_output_by_default(
    capsys: pytest.CaptureFixture[str]
) -> None:
    async def noisy() -> None:
        print("visible")

    asyncio.run(aio.Benchmark().measure_time(
        noisy, warmup_times=0, run_times=1))
    assert "visible" in capsys.readouterr().out


def test_importing_haashi_does_not_import_asyncio() -> None:
    import subprocess
    import sys

    code = "import sys, haashi; print('asyncio' in sys.modules)"
    base = subprocess.run([sys.executable, "-c", "import sys; print('asyncio' in sys.modules)"],
                          capture_output=True, text=True, check=True)
    if base.stdout.strip() == "True":
        pytest.skip("interpreter loads asyncio at startup")
    out = subprocess.run([sys.executable, "-c", code],
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"  # async cost is opt-in via haashi.aio
