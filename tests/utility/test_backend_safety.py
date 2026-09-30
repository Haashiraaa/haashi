"""Regression tests for behavior a long-running backend depends on."""

import gc
import json
import logging
import threading
from pathlib import Path

import pytest

from haashi.utility import ErrorLogger, FileHandler, Logger


def test_concurrent_log_error_loses_no_entries(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"

    def work(worker: int) -> None:
        for i in range(15):
            el.log_error(
                ValueError(f"{worker}-{i}"), path=log,
                use_script_dir=False, max_entries=10_000)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(json.loads(log.read_text())) == 8 * 15


def test_creating_loggers_does_not_grow_the_logging_registry() -> None:
    registry = logging.root.manager.loggerDict
    before = len(registry)
    for _ in range(200):
        Logger()
        FileHandler()
    gc.collect()
    assert len(registry) == before


def test_save_json_replaces_file_atomically(tmp_path: Path) -> None:
    fh = FileHandler()
    target = tmp_path / "a.json"
    fh.save_json({"v": 1}, target)
    inode = target.stat().st_ino
    fh.save_json({"v": 2}, target)

    assert target.stat().st_ino != inode  # swapped in, not truncated in place
    assert fh.read_json(target) == {"v": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]  # no temp litter


def test_failed_write_keeps_old_content_and_leaves_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fh = FileHandler()
    target = tmp_path / "keep.json"
    fh.save_json({"v": "old"}, target)

    def explode(*_a: object, **_k: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("haashi.utility._atomic.os.replace", explode)
    with pytest.raises(Exception, match="disk full"):
        fh.save_json({"v": "new"}, target)

    assert json.loads(target.read_text()) == {"v": "old"}
    assert [p.name for p in tmp_path.iterdir()] == ["keep.json"]


def test_corrupt_error_log_is_backed_up_not_destroyed(tmp_path: Path) -> None:
    el = ErrorLogger()
    log = tmp_path / "e.json"
    log.write_text("{ not json")

    with pytest.warns(RuntimeWarning, match="Corrupted"):
        el.log_error(ValueError("x"), path=log, use_script_dir=False)

    assert (tmp_path / "e.json.corrupt").read_text() == "{ not json"
    assert len(json.loads(log.read_text())) == 1
