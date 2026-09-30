
# src/haashi/utility/_paths.py

"""Internal path helpers shared by ErrorLogger and FileHandler."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoids a runtime import cycle with logger.py
    from .logger import Logger


def _looks_installed(path: Path) -> bool:
    """True if ``path`` is inside site-packages or the scripts (bin) directory.

    Those are where pip-installed console scripts and ``python -m pytest``
    live; writing logs there would be surprising.
    """
    import sysconfig

    for key in ("purelib", "platlib", "scripts"):
        root = sysconfig.get_path(key)
        if root and path.is_relative_to(Path(root).resolve()):
            return True
    return False


def detect_script_dir(logger: Logger | None = None) -> Path:
    """Return the directory of the executed main script, falling back to cwd.

    Falls back to the current directory when the main script lives in an
    installed location (site-packages or a scripts/bin directory).

    Args:
        logger: Optional Logger used to report what was detected. When None
            the detection is silent.
    """
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file:
        script_dir = Path(main_file).resolve().parent
        if not _looks_installed(script_dir):
            if logger is not None:
                logger.debug(f"Script directory detected: {script_dir}")
            return script_dir
        if logger is not None:
            logger.debug(
                f"Main script is in an installed location ({script_dir}); "
                "using current directory")
            return Path.cwd()
        return Path.cwd()

    if logger is not None:
        logger.warning(
            "Could not detect main script location, using current directory")
    return Path.cwd()
