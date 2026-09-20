"""Guards for the lazy-loading utility/__init__.py."""

import ast
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import haashi.utility as util

INIT = Path(util.__file__ or "")


def _type_checking_imports() -> dict[str, str]:
    """name -> relative module, from the `if TYPE_CHECKING:` block of __init__.py."""
    tree = ast.parse(INIT.read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.If) and getattr(node.test, "id", "") == "TYPE_CHECKING":
            for stmt in node.body:
                if isinstance(stmt, ast.ImportFrom) and stmt.level > 0:  # package-relative only
                    module = "." * stmt.level + (stmt.module or "")
                    for alias in stmt.names:
                        found[alias.name] = module
    return found


def test_all_lazy_and_type_checking_block_agree() -> None:
    lazy = getattr(util, "_LAZY")  # noqa: B009
    assert set(util.__all__) == set(lazy), "__all__ and _LAZY drifted apart"
    assert _type_checking_imports() == lazy, "TYPE_CHECKING block and _LAZY drifted apart"


@pytest.mark.parametrize("name", util.__all__)
def test_every_name_resolves_to_the_real_object(name: str) -> None:
    lazy = getattr(util, "_LAZY")  # noqa: B009
    module = importlib.import_module(lazy[name], "haashi.utility")
    assert getattr(util, name) is getattr(module, name)


def test_module_docstring_is_present() -> None:
    assert util.__doc__ and "Utility package for haashi" in util.__doc__


def test_dir_lists_lazy_names() -> None:
    listed = dir(util)
    for name in util.__all__:
        assert name in listed


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="no attribute 'Nope'"):
        util.Nope  # type: ignore[attr-defined]  # noqa: B018


def test_star_import_works() -> None:
    namespace: dict[str, object] = {}
    exec("from haashi.utility import *", namespace)  # noqa: S102
    for name in util.__all__:
        assert name in namespace


def test_submodules_load_only_on_first_use() -> None:
    code = """
import json, sys
import haashi.utility as u

def loaded():
    return sorted(m.rsplit(".", 1)[1] for m in sys.modules if m.startswith("haashi.utility."))

before = loaded()
u.Colors
after_colors = loaded()
u.Logger
after_logger = loaded()
print(json.dumps([before, after_colors, after_logger]))
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    before, after_colors, after_logger = json.loads(out.stdout)
    assert before == []
    assert after_colors == ["uiux"]
    assert "logger" in after_logger and "uiux" in after_logger
    assert "benchmark" not in after_logger and "filehandler" not in after_logger


def test_importing_the_package_does_not_import_typing() -> None:
    """Keeps `import haashi` at bare-interpreter cost (typing alone is ~10 ms)."""
    probe = "import sys; {imp}; print('typing' in sys.modules)"
    baseline = subprocess.run(
        [sys.executable, "-c", probe.format(imp="pass")],
        capture_output=True, text=True, check=True)
    if baseline.stdout.strip() == "True":
        pytest.skip("this interpreter loads typing at startup, so the check is meaningless")
    fresh = subprocess.run(
        [sys.executable, "-c", probe.format(imp="import haashi")],
        capture_output=True, text=True, check=True)
    assert fresh.stdout.strip() == "False"
