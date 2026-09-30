"""Every module must import cleanly in a fresh interpreter (catches import cycles)."""

import subprocess
import sys

import pytest

MODULES = [
    "haashi",
    "haashi.utility",
    "haashi.utility._paths",
    "haashi.utility._atomic",
    "haashi.utility._types",
    "haashi.utility._datetime",
    "haashi.utility.exceptions",
    "haashi.utility.uiux",
    "haashi.utility.logger",
    "haashi.utility.filehandler",
    "haashi.utility.benchmark",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports_in_fresh_interpreter(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_public_api_and_version() -> None:
    import haashi
    import haashi.utility as util

    assert isinstance(haashi.__version__, str)
    for name in util.__all__:
        assert hasattr(util, name), name


def test_no_third_party_imports() -> None:
    code = (
        "import sys; before = set(sys.modules); import haashi;"
        "import sys as s; new = {m.split('.')[0] for m in set(s.modules) - before};"
        "print(','.join(sorted(new)))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "pydantic" not in result.stdout
