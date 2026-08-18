

# src/haashi/__init__.py

"""haashi - a lightweight, dependency-free utility toolkit.

Currently provides a single subpackage:
    utility: logging, file I/O, screen/terminal helpers, datetime helpers,
             and performance benchmarking.
"""

from . import utility

__version__ = "2.0.0"

__all__ = [
    "utility",
]
