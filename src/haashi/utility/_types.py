# src/haashi/utility/_types.py

"""Shared type aliases and small JSON helpers (standard library only)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol, TypeAlias

from .exceptions import InvalidJsonFormatError

PathLike: TypeAlias = str | Path | os.PathLike[str]
JSONType: TypeAlias = "str | int | float | bool | None | list[JSONType] | dict[str, JSONType]"


def dump_json(data: object, indent: int | None = 4) -> str:
    """Serialize ``data`` to a JSON string.

    Raises:
        InvalidJsonFormatError: If ``data`` contains something JSON can't
            represent (custom objects, sets, NaN/Infinity, circular refs).
    """
    try:
        return json.dumps(data, indent=indent, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise InvalidJsonFormatError(
            f"Data is not JSON-serializable: {exc}") from exc


class ErrorWriter(Protocol):
    """Anything ``Logger`` can persist errors with (``ErrorLogger``, ``JsonlErrorLogger``)."""

    def log_error(
        self,
        exception: BaseException,
        context: str | None = None,
        path: PathLike | None = None,
        use_script_dir: bool = True,
    ) -> Path: ...
