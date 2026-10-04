

import sys
import types
from pathlib import Path

import pytest

# pyright: ignore[reportPrivateUsage]
from haashi.utility._paths import detect_script_dir


class TestDetectScriptDir:
    def test_installed_location_falls_back_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sysconfig

        fake_site = tmp_path / "site-packages"
        fake_site.mkdir()
        (fake_site / "tool.py").write_text("")
        monkeypatch.setattr(sysconfig, "get_path",
                            lambda *_a, **_k: str(fake_site))
        monkeypatch.setitem(sys.modules, "__main__", types.SimpleNamespace(
            __file__=str(fake_site / "tool.py")))
        assert detect_script_dir() == Path.cwd()

    def test_normal_script_dir_is_used(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sysconfig

        (tmp_path / "app.py").write_text("")
        monkeypatch.setattr(sysconfig, "get_path",
                            lambda *_a, **_k: str(tmp_path / "elsewhere"))
        monkeypatch.setitem(sys.modules, "__main__", types.SimpleNamespace(
            __file__=str(tmp_path / "app.py")))
        assert detect_script_dir() == tmp_path.resolve()
