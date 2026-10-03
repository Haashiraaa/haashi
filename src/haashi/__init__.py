
# src/haashi/__init__.py

"""haashi - a lightweight, dependency-free utility toolkit.

Subpackages:
    utility: logging, file I/O, terminal helpers, datetime helpers and
             performance benchmarking (sync API).
    aio:     the same API with awaitable IO for FastAPI, aiohttp and asyncio
             (import it explicitly: ``from haashi.aio import FileHandler``).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import aio, utility

# Single source of truth for the version (read statically by setuptools).
# Keep this a plain string literal.
__version__ = "1.3.1"

__all__ = ["utility", "aio"]


def __getattr__(name: str):
    if name in __all__:
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
