# src/haashi/__init__.py

"""haashi - a lightweight, dependency-free utility toolkit.

Provides a single subpackage:
    utility: logging, file I/O, terminal helpers, datetime helpers,
             and performance benchmarking.
"""

from . import utility

# Single source of truth for the version (read statically by setuptools).
# Keep this a plain string literal.
__version__ = "1.0.0"

__all__ = ["utility"]
