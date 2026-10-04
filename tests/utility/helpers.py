
"""Shared plain helpers for the tests in the utility package.

Fixtures live in conftest.py.
"""

from __future__ import annotations

import ast
import io
import logging
from pathlib import Path
from typing import cast

import haashi.utility as util
from haashi.utility import JsonlErrorLogger, Logger

INIT = Path(util.__file__ or "")


def boom() -> Exception:
    """Return a real, raised-and-caught ValueError (so it has a traceback)."""
    try:
        raise ValueError("boom")
    except ValueError as exc:
        return exc


class FakeTTY(io.StringIO):
    """A StringIO that claims to be a terminal."""

    def isatty(self) -> bool:
        return True


def get_handler(lg: Logger) -> logging.StreamHandler:  # type: ignore[type-arg]
    return lg.logger.handlers[0]  # type: ignore[return-value]


def messages(entries: list[object]) -> list[str]:
    return [cast("dict[str, str]", e)["message"] for e in entries]


def worker(log_dir: str, worker_id: int, n: int) -> None:
    """Process target for multi-process tests (must be importable by 'spawn')."""
    el = JsonlErrorLogger(log_dir=log_dir)
    for i in range(n):
        el.log_error(ValueError(f"{worker_id}-{i}"))


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
