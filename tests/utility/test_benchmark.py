import logging

import pytest

from haashi.utility import Benchmark, BenchmarkError, InvalidFunctionError


def test_returns_positive_float() -> None:
    result = Benchmark().measure_time(lambda: sum(range(1000)), run_times=3)
    assert isinstance(result, float) and result > 0


def test_function_is_called_expected_number_of_times() -> None:
    calls = 0

    def func() -> None:
        nonlocal calls
        calls += 1

    Benchmark().measure_time(func, warmup_times=2, run_times=3, repeat_times=2)
    assert calls == 2 + 3 * 2


def test_zero_warmup_is_allowed() -> None:
    calls = 0

    def func() -> None:
        nonlocal calls
        calls += 1

    Benchmark().measure_time(func, warmup_times=0, run_times=2)
    assert calls == 2


@pytest.mark.parametrize("field", ["run_times", "repeat_times", "warmup_times"])
def test_bad_counts_raise_value_error(field: str) -> None:
    bad = -1 if field == "warmup_times" else 0
    with pytest.raises(ValueError):
        Benchmark().measure_time(lambda: None, **{field: bad})  # type: ignore[arg-type]


def test_non_callable_raises_invalid_function_error() -> None:
    with pytest.raises(InvalidFunctionError):
        Benchmark().measure_time("not a function")  # type: ignore[arg-type]


def test_failing_function_is_wrapped() -> None:
    def bad() -> None:
        raise RuntimeError("nope")

    with pytest.raises(BenchmarkError, match="nope"):
        Benchmark().measure_time(bad)


def test_output_is_suppressed_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    Benchmark().measure_time(lambda: print("noisy"), run_times=1)
    assert "noisy" not in capsys.readouterr().out


def test_output_can_be_left_on(capsys: pytest.CaptureFixture[str]) -> None:
    Benchmark().measure_time(
        lambda: print("visible"), warmup_times=0, run_times=1, suppress_output=False)
    assert "visible" in capsys.readouterr().out


def test_previous_logging_disable_level_is_restored() -> None:
    logging.disable(logging.WARNING)
    try:
        Benchmark().measure_time(lambda: None, run_times=1)
        assert logging.root.manager.disable == logging.WARNING
    finally:
        logging.disable(logging.NOTSET)
