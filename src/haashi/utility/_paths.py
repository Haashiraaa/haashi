# src/haashi/utility/_paths.py

"""Internal path helpers shared by ErrorLogger and FileHandler."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoids a runtime import cycle with logger.py
    from .logger import Logger


def detect_script_dir(logger: Logger | None = None) -> Path:
    """Return the directory of the executed main script, falling back to cwd.

    Args:
        logger: Optional Logger used to report what was detected. When None
            the detection is silent.
    """
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file:
        script_dir = Path(main_file).resolve().parent
        if logger is not None:
            logger.debug(f"Script directory detected: {script_dir}")
        return script_dir

    if logger is not None:
        logger.warning(
            "Could not detect main script location, using current directory")
    return Path.cwd()
