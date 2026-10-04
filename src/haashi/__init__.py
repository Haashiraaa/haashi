
# src/haashi/__init__.py

"""haashi - a lightweight, dependency-free utility toolkit.
...
"""

from __future__ import annotations

# Defined by hand instead of imported from `typing`: importing `typing`
# costs ~10 ms on its own. Type checkers treat this name exactly like
# typing.TYPE_CHECKING.
TYPE_CHECKING = False

if TYPE_CHECKING:
    from . import aio, utility

# Single source of truth for the version (read statically by setuptools).
# Keep this a plain string literal.
__version__ = "1.3.1"

__all__ = ["utility", "aio"]


def __getattr__(name: str) -> object:
    if name in __all__:
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
