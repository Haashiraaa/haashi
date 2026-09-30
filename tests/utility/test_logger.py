import io
import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from haashi.utility import Colors, ErrorLogger, FileHandler, Logger, LoggingError


def boom() -> Exception:
    try:
        raise ValueError("boom")
    except ValueError as exc:
        return exc


def test_instances_have_independent_levels() -> None:
    quiet = Logger(level=logging.ERROR)
    loud = Logger(level=logging.DEBUG)
    assert quiet.logger.level == logging.ERROR
    assert loud.logger.level == logging.DEBUG


def test_library_does_not_touch_root_logging() -> None:
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    from haashi.utility import Benchmark

    Logger()
    ErrorLogger()
    FileHandler()
    Benchmark()
    assert root.handlers == handlers
    assert root.level == level


def test_log_error_appends_across_calls(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    el.log_error(boom(), context="one", path=log, use_script_dir=False)
    el.log_error(boom(), context="two", path=log, use_script_dir=False)

    entries = json.loads(log.read_text())
    assert isinstance(entries, list)
    assert [e["context"] for e in entries] == ["one", "two"]
    assert entries[0]["type"] == "ValueError"
    assert "boom" in entries[0]["traceback"]


def test_log_error_prunes_to_max_entries(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    for i in range(5):
        el.log_error(boom(), context=str(i), path=log, use_script_dir=False, max_entries=3)
    entries = el.view_error_entries(path=log, use_script_dir=False, limit=None)
    assert [e["context"] for e in entries] == ["2", "3", "4"]  # type: ignore[index]


def test_timestamp_respects_utc_offset(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    el.log_error(boom(), path=log, use_script_dir=False, utc_offset_hours=1)
    stamp = json.loads(log.read_text())[0]["timestamp"]
    assert stamp.endswith("+01:00")


def test_log_error_rejects_bad_arguments(tmp_path: Path) -> None:
    el = ErrorLogger()
    with pytest.raises(ValueError):
        el.log_error(boom(), path=tmp_path / "e.json", use_script_dir=False, max_entries=0)
    with pytest.raises(ValueError):
        el.log_error(boom(), path=tmp_path / "e.json", use_script_dir=False, utc_offset_hours=99)


def test_corrupt_log_warns_and_recovers(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    log.write_text("{ this is not json")
    with pytest.warns(RuntimeWarning, match="Corrupted"):
        el.log_error(boom(), path=log, use_script_dir=False)
    assert len(json.loads(log.read_text())) == 1


def test_non_list_log_warns_and_recovers(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    log.write_text('{"a": 1}')
    with pytest.warns(RuntimeWarning, match="not a JSON list"):
        el.log_error(boom(), path=log, use_script_dir=False)
    assert len(json.loads(log.read_text())) == 1


def test_view_and_clear_use_the_same_file_as_log_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Default use_script_dir=True everywhere: what is written must be readable/clearable.
    import haashi.utility.logger as logger_mod

    monkeypatch.setattr(logger_mod, "detect_script_dir", lambda *_a, **_k: tmp_path)
    el = ErrorLogger()
    saved = el.log_error(boom())
    assert saved == tmp_path / "logs" / "errors_log.json"
    assert len(el.view_error_entries()) == 1
    assert el.clear_errors(confirm=False) is True
    assert not saved.exists()


def test_view_error_entries_limit_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ErrorLogger().view_error_entries(path=tmp_path / "x.json", use_script_dir=False, limit=0)


def test_clear_errors_missing_file_returns_false(tmp_path: Path) -> None:
    assert ErrorLogger().clear_errors(tmp_path / "nope.json", False, confirm=False) is False


def test_clear_errors_refuses_to_prompt_when_not_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    el.log_error(boom(), path=log, use_script_dir=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(LoggingError):
        el.clear_errors(log, False)
    assert log.exists()


@pytest.mark.parametrize(
    ("answer", "deleted"), [("y", True), ("YES", True), ("n", False), ("", False)]
)
def test_clear_errors_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str, deleted: bool
) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    el.log_error(boom(), path=log, use_script_dir=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt="": answer)
    assert el.clear_errors(log, False) is deleted
    assert log.exists() is (not deleted)


def test_logger_error_persists_when_asked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "l.json"
    exc = boom()
    Logger(logging.INFO).error(
        "failed", exception=exc, save_to_json=True, path=log,
        use_script_dir=False, context="ctx",
    )
    entries = json.loads(log.read_text())
    assert entries[0]["context"] == "ctx"
    err = capsys.readouterr().err
    assert "failed" in err and str(log) in err


def test_logger_error_uses_supplied_error_logger(tmp_path: Path) -> None:
    class Spy(ErrorLogger):
        called = 0

        def log_error(self, *args, **kwargs) -> Path:  # type: ignore[no-untyped-def]
            Spy.called += 1
            return super().log_error(*args, **kwargs)

    Logger().error("x", exception=boom(), save_to_json=True, error_logger=Spy(),
                   path=tmp_path / "s.json", use_script_dir=False)
    assert Spy.called == 1


def test_logger_error_save_requires_exception() -> None:
    with pytest.raises(LoggingError):
        Logger().error("oops", save_to_json=True)


def test_logger_error_without_saving_writes_nothing(tmp_path: Path) -> None:
    Logger().error("just console", path=tmp_path / "n.json", use_script_dir=False)
    assert not (tmp_path / "n.json").exists()


def test_logger_exception_outside_except_raises() -> None:
    with pytest.raises(LoggingError):
        Logger().exception("nothing to log")


def test_logger_exception_inside_except_persists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "x.json"
    try:
        raise KeyError("missing")
    except KeyError:
        Logger(logging.INFO).exception(
            "lookup failed", save_to_json=True, path=log, use_script_dir=False)
    assert json.loads(log.read_text())[0]["type"] == "KeyError"
    err = capsys.readouterr().err
    assert "lookup failed" in err and "KeyError" in err  # traceback is shown


def test_warning_has_no_ansi_codes_when_not_a_tty(capsys: pytest.CaptureFixture[str]) -> None:
    Logger().warning("careful")
    err = capsys.readouterr().err
    assert "careful" in err
    assert "\033[" not in err


# ---- colors -------------------------------------------------------------

class _FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def _handler(lg: Logger) -> logging.StreamHandler:  # type: ignore[type-arg]
    return lg.logger.handlers[0]  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("method", "painter"),
    [
        ("debug", Colors.debug),
        ("info", Colors.info),
        ("warning", Colors.warning),
        ("error", Colors.error),
    ],
)
def test_forced_color_uses_the_colors_class(
    method: str, painter: Callable[[str], str], capsys: pytest.CaptureFixture[str]
) -> None:
    lg = Logger(logging.DEBUG, color=True)
    getattr(lg, method)("msg")
    assert capsys.readouterr().err == painter(f"[{method.upper()}] msg") + "\n"


@pytest.mark.parametrize("method", ["debug", "info", "warning", "error"])
def test_color_false_never_emits_ansi(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    lg = Logger(logging.DEBUG, color=False)
    _handler(lg).setStream(_FakeTTY())  # a real terminal, but color is forced off
    getattr(lg, method)("msg")
    assert "\033[" not in _handler(lg).stream.getvalue()  # type: ignore[attr-defined]


def test_auto_color_is_off_when_not_a_terminal(capsys: pytest.CaptureFixture[str]) -> None:
    Logger(logging.DEBUG).error("plain")
    assert capsys.readouterr().err == "[ERROR] plain\n"


def test_auto_color_is_on_for_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    lg = Logger(logging.DEBUG)
    stream = _FakeTTY()
    _handler(lg).setStream(stream)
    lg.error("boom")
    assert stream.getvalue() == Colors.error("[ERROR] boom") + "\n"


def test_no_color_env_overrides_terminal_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    lg = Logger(logging.DEBUG)
    stream = _FakeTTY()
    _handler(lg).setStream(stream)
    lg.error("boom")
    assert stream.getvalue() == "[ERROR] boom\n"


def test_explicit_color_true_beats_no_color_env(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    Logger(logging.DEBUG, color=True).info("hi")
    assert "\033[" in capsys.readouterr().err


def test_closed_stream_does_not_crash_color_detection() -> None:
    lg = Logger(logging.DEBUG)
    stream = io.StringIO()
    _handler(lg).setStream(stream)
    stream.close()
    # isatty() on a closed stream raises ValueError; detection must swallow it.
    from haashi.utility.logger import _color_enabled  # pyright: ignore[reportPrivateUsage]

    assert _color_enabled(stream, None) is False


def test_exception_traceback_is_colored_as_error(capsys: pytest.CaptureFixture[str]) -> None:
    lg = Logger(logging.INFO, color=True)
    try:
        raise KeyError("k")
    except KeyError:
        lg.exception("lookup failed")
    err = capsys.readouterr().err
    assert err.startswith(Colors.BOLD + Colors.RED)
    assert "KeyError" in err and err.rstrip("\n").endswith(Colors.RESET)


def test_each_logger_gets_a_distinct_underlying_logger() -> None:
    names = {Logger().logger.name for _ in range(5)}
    assert len(names) == 5


# ---- log_dir / default error_logger (backend use) -----------------------------

def test_log_dir_receives_the_default_file(tmp_path: Path) -> None:
    el = ErrorLogger(log_dir=tmp_path / "svc")
    saved = el.log_error(boom())
    assert saved == tmp_path / "svc" / "errors_log.json"
    assert len(el.view_error_entries()) == 1
    assert el.clear_errors(confirm=False) is True


def test_log_dir_wins_over_use_script_dir(tmp_path: Path) -> None:
    el = ErrorLogger(log_dir=tmp_path)
    saved = el.log_error(boom(), path="sub/e.json", use_script_dir=True)
    assert saved == tmp_path / "sub" / "e.json"


def test_absolute_path_beats_log_dir(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere" / "e.json"
    saved = ErrorLogger(log_dir=tmp_path / "svc").log_error(boom(), path=target)
    assert saved == target and target.exists()
    assert not (tmp_path / "svc").exists()


def test_log_dir_expands_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert ErrorLogger(log_dir="~/logs").log_dir == tmp_path / "logs"


def test_logger_uses_default_error_logger_and_call_can_override(tmp_path: Path) -> None:
    default = ErrorLogger(log_dir=tmp_path / "default")
    other = ErrorLogger(log_dir=tmp_path / "other")
    lg = Logger(error_logger=default)

    lg.error("a", exception=boom(), save_to_json=True)
    lg.error("b", exception=boom(), save_to_json=True, error_logger=other)

    assert (tmp_path / "default" / "errors_log.json").exists()
    assert (tmp_path / "other" / "errors_log.json").exists()
