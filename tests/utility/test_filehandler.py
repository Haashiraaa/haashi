
import json
from pathlib import Path

import pytest

from haashi.utility import FileHandler, FileOperationError, InvalidJsonFormatError


class TestJson:
    def test_roundtrip_is_not_double_encoded(self, fh: FileHandler, tmp_path: Path) -> None:
        target = tmp_path / "a.json"
        fh.save_json({"key": "value", "n": [1, 2, 3]}, target)

        assert json.loads(target.read_text()) == {
            "key": "value", "n": [1, 2, 3]}
        assert fh.read_json(target) == {"key": "value", "n": [1, 2, 3]}

    def test_str_paths_are_accepted(self, fh: FileHandler, tmp_path: Path) -> None:
        target = str(tmp_path / "nested" / "b.json")
        fh.save_json({"ok": True}, target)
        assert fh.read_json(target) == {"ok": True}

    def test_non_serializable_data_raises_and_writes_nothing(
        self, fh: FileHandler, tmp_path: Path
    ) -> None:
        target = tmp_path / "bad.json"
        with pytest.raises(InvalidJsonFormatError):
            fh.save_json({"s": {1, 2}}, target)  # type: ignore[arg-type]
        assert not target.exists()

    def test_nan_is_rejected(self, fh: FileHandler, tmp_path: Path) -> None:
        with pytest.raises(InvalidJsonFormatError):
            fh.save_json({"x": float("nan")}, tmp_path / "nan.json")

    def test_read_missing_file_raises_filenotfound(
        self, fh: FileHandler, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            fh.read_json(tmp_path / "nope.json")

    def test_read_invalid_content(self, fh: FileHandler, tmp_path: Path) -> None:
        target = tmp_path / "broken.json"
        target.write_text("{not json")
        with pytest.raises(FileOperationError):
            fh.read_json(target)

    def test_utf8_roundtrip(self, fh: FileHandler, tmp_path: Path) -> None:
        fh.save_json({"name": "Ọlá — ñ"}, tmp_path / "u.json")
        assert fh.read_json(tmp_path / "u.json") == {"name": "Ọlá — ñ"}


class TestText:
    def test_write_append_read(self, fh: FileHandler, tmp_path: Path) -> None:
        target = tmp_path / "t.txt"
        fh.save_txt("one", target, add_newline_prefix=False)
        fh.save_txt("two", target, mode="a", add_newline_prefix=False)
        assert fh.read_txt(target) == "onetwo"

    def test_rejects_bad_mode(self, fh: FileHandler, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            fh.save_txt("x", tmp_path / "t.txt", mode="r")

    def test_reading_a_directory_is_not_a_file(
        self, fh: FileHandler, tmp_path: Path
    ) -> None:
        with pytest.raises(FileOperationError):
            fh.read_txt(tmp_path)


class TestPathHelpers:
    def test_get_parent_path(self, fh: FileHandler, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert fh.get_parent_path(
            levels_up=2, start_path=deep) == tmp_path / "a"
        assert fh.get_parent_path(
            levels_up=0, start_path=deep) == deep.resolve()

    def test_get_parent_path_negative(self, fh: FileHandler, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            fh.get_parent_path(levels_up=-1, start_path=tmp_path)

    def test_get_parent_path_defaults_to_callers_file_dir(self, fh: FileHandler) -> None:
        assert fh.get_parent_path(levels_up=0) == Path(
            __file__).resolve().parent

    def test_get_ancestor_by_name(self, fh: FileHandler, tmp_path: Path) -> None:
        deep = tmp_path / "my-project" / "src" / "mod"
        deep.mkdir(parents=True)
        assert fh.get_ancestor_by_name("my-project", start_path=deep) == (
            tmp_path / "my-project").resolve()
        assert fh.get_ancestor_by_name(
            "does-not-exist", start_path=deep) is None
        assert fh.get_ancestor_by_name(
            "my-project", start_path=deep, max_levels=1) is None

    def test_get_script_dir_returns_existing_dir(self, fh: FileHandler) -> None:
        assert fh.get_script_dir().is_dir()
