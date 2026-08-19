
"""
Utility Module for haashi
==============================

Provides utility classes for:
- Logging (console + JSON error persistence)
- File operations (JSON, TXT)
- Screen manipulation (clear, animations)
- Datetime helpers


Author: Haashiraaa
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import sys
import textwrap
import time
import timeit
from collections.abc import Callable
from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .exceptions import (
    BenchmarkError,
    FileOperationError,
    InvalidFunctionError,
)

# Type aliases
PathLike = str | Path
JsonFormat = dict[Any, Any] | list[Any]


# ============================================================================
# ERROR LOGGER (JSON Persistence)
# ============================================================================

class ErrorLogger:
    """
    Handles logging errors to both console and JSON file for persistence.

    This logger automatically saves errors to a JSON file with timestamps,
    error types, and full tracebacks for debugging.

    Attributes:
        error_log_path (Path): Path to the JSON error log file.
        max_entries (int): Maximum number of error entries to keep in JSON.

    Example:
        >>> error_logger = ErrorLogger("logs/errors.json")
        >>> error_logger.log_error(ValueError("Invalid input"), context="data_processing")
    """

    def __init__(
        self,
        default_path: PathLike = "logs/errors.json",
        max_entries: int = 100,
    ) -> None:
        """
        Initialize the error logger.

        Args:
            default: Path where error JSON will be saved.
            max_entries: Maximum number of errors to keep (auto-rotates old entries).
        """
        self.default_path = Path(default_path)
        self.max_entries = max_entries

    def _ensure_path(self, path: Path) -> Path:
        """
        Ensure parent directories exist for file path.

        Simple independent version - no FileHandler needed.

        Args:
            path: File path to validate

        Returns:
            Same path with guaranteed parent directories
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _get_script_dir(self) -> Path:
        """
        Get the directory where the executed script is located.

        Returns the directory of the main Python script that was run,
        NOT the current working directory. This ensures files are saved
        with the script regardless of where the command is executed from.

        Returns:
            Path: Directory containing the executed script

        Example:
            >>> # Script location: /home/user/project/process.py
            >>> handler = FileHandler()
            >>> script_dir = handler.get_script_dir()
            >>> print(script_dir)
            /home/user/project
            >>> 
            >>> # Save file in script's directory
            >>> log_path = script_dir / "logs/output.json"
            >>> handler.save_json(data, log_path)
            >>> # Saves to: /home/user/project/logs/output.json
            >>> 
            >>> # Works the same regardless of where you run from:
            >>> # Run from /home/user/project → saves to /home/user/project/logs/
            >>> # Run from /home/user → saves to /home/user/project/logs/
            >>> # Run from anywhere → saves to /home/user/project/logs/

        Note:
            Falls back to current working directory if main script
            cannot be detected (e.g., in interactive Python sessions).
        """

        # Get the main script file that was executed
        if hasattr(sys.modules['__main__'], '__file__'):
            main_file = sys.modules['__main__'].__file__
            if main_file:
                script_dir = Path(main_file).resolve().parent

                return script_dir

        # Fallback to current working directory
        fallback = Path.cwd()

        return fallback

    def _read_errors(self, path: Path) -> list[JsonFormat]:
        """
        Read existing errors from JSON file.

        Args:
            path: Path to error log file

        Returns:
            List of existing error entries, 
            or empty list if file doesn't exist
        """
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

        return []

    def _write_errors(self, errors: list[JsonFormat], path: Path) -> None:
        """
        Write errors to JSON file.

        Args:
            errors: List of error entries to write
            path: Path where to save the JSON file
        """
        # Ensure directory exists
        validated_path = self._ensure_path(path)

        # Write JSON with pretty formatting
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(errors, f, indent=4, default=str)

    def log_error(
        self,
        exception: Exception,
        context: str | None = None,
        path: PathLike | None = None,
        use_script_dir: bool = True
    ) -> None:
        """
        Save error to JSON file, automatically in script's directory.

        Args:
            exception: The exception to log
            context: Optional context string (e.g., "data_loading", "api_call")
            path: Optional custom path (default: uses default_path from __init__)
            use_script_dir: If True, saves to caller's script directory (default: True)

        Example:
            >>> # In your script: my-project/src/process.py
            >>> error_logger = ErrorLogger()
            >>> 
            >>> try:
            ...     process_data()
            ... except Exception as e:
            ...     error_logger.log_error(e, context="processing")
            >>> 
            >>> # Saves to: my-project/src/logs/errors.json
            >>> # (script's directory, not current working directory!)
        """
        # Determine save path
        error_path = Path(path) if path else self.default_path

        # Save to script's directory if requested
        if use_script_dir:
            script_dir = self._get_script_dir()
            error_path = script_dir / error_path

        # Read existing errors
        existing_errors = self._read_errors(error_path)

        # Create new error entry
        error_entry: JsonFormat = {
            "timestamp": datetime.now().isoformat(),
            "type": type(exception).__name__,
            "message": str(exception),
            "context": context or "unspecified",
            "traceback": self._get_traceback_string(exception),
        }

        # Add to list
        existing_errors.append(error_entry)

        # Rotate if exceeds max entries (keep most recent)
        if len(existing_errors) > self.max_entries:
            existing_errors = existing_errors[-self.max_entries:]

        # Write back to file
        self._write_errors(existing_errors, error_path)

    def clear_errors(self, path: PathLike | None = None) -> None:
        """
        Clear all errors from the log file.

        Args:
            path: Optional custom path (default: uses default_path)
        """
        error_path = Path(path) if path else self.default_path

        if error_path.exists():
            error_path.unlink()

    def get_errors(
        self,
        path: PathLike | None = None,
        limit: int | None = None
    ) -> list[JsonFormat]:
        """
        Retrieve errors from log file.

        Args:
            path: Optional custom path (default: uses default_path)
            limit: Optional limit on number of errors to return (most recent first)

        Returns:
            List of error entries
        """
        error_path = Path(path) if path else self.default_path
        errors = self._read_errors(error_path)

        if limit:
            return errors[-limit:]

        return errors

    def _get_traceback_string(self, exception: Exception) -> str:
        """Extract traceback as string from exception."""
        import traceback
        return ''.join(traceback.format_exception(
            type(exception), exception, exception.__traceback__
        ))


# ============================================================================
# LOGGER UTILITY
# ============================================================================

class Logger:
    """
    Console logging utility with multiple log levels.

    Provides clean, formatted console output for info, debug, warning, and error messages.
    Integrates with ErrorLogger for persistent error tracking.

    Attributes:
        logger (logging.Logger): Internal Python logger instance.
        error_logger (ErrorLogger): JSON error logger for persistence.

    Example:
        >>> logger = Logger(level=logging.INFO)
        >>> logger.info("Processing started")
        >>> logger.error("Failed to load file", save_to_json=True)
    """

    def __init__(
        self,
        level: int = logging.WARNING,
        error_log_path: PathLike | None = None,
    ) -> None:
        """
        Initialize the logger.

        Args:
            level: Logging level (logging.INFO, logging.DEBUG, etc.).
            error_log_path: Optional path for JSON error logging. 
            If None, uses default.
        """
        self.logger = logging.getLogger("haashi")
        self.logger.setLevel(level)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # Initialize error logger for JSON persistence
        self.log_path = error_log_path or "logs/errors.json"
        self.error_logger = ErrorLogger(default_path=self.log_path)

    def info(self, message: Any) -> None:
        """
        Log informational message to console.

        Args:
            message: The message to log (will be converted to string).
        """
        self.logger.info(str(message))

    def debug(self, message: Any) -> None:
        """
        Log debug message to console (only visible if level=DEBUG).

        Args:
            message: The message to log (will be converted to string).
        """
        self.logger.debug(str(message))

    def warning(self, message: Any) -> None:
        """
        Log warning message to console.

        Args:
            message: The message to log (will be converted to string).
        """
        self.logger.warning(str(message))

    def error(
        self,
        message: Any | None = "Error occurred!",
        path: PathLike | None = None,
        exception: Exception | None = None,
        save_to_json: bool = False,
        use_script_dir: bool = True,
        context: str | None = None
    ) -> None:
        """
        Log error message to console and optionally to JSON.

        Args:
            message: The error message to log.
            exception: Optional exception object to log to JSON.
            save_to_json: If True, saves error to JSON file for persistence.
            context: Optional context for JSON logging (e.g., "api_call").

        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     logger.error("Operation failed", exception=e, save_to_json=True, context="data_load")
        """

        # Determine error log path
        error_path = path or self.log_path

        error_message = str(message)

        # Save to JSON if requested
        if save_to_json and exception:
            self.error_logger.log_error(
                exception,
                context=context,
                path=error_path,
                use_script_dir=use_script_dir
            )

            error_message = str(message) + f"\nSee {error_path} for details"

        self.logger.error(error_message)


# ============================================================================
# FILE OPERATIONS
# ============================================================================


class FileHandler:
    """
    Handles file operations with proper error handling and path validation.

    Supports:
    - JSON read/write
    - TXT read/write
    - Path validation and creation

    Example:
        >>> file_handler = FileHandler()
        >>> file_handler.save_json({"key": "value"}, "data/output.json")
        >>> data = file_handler.read_json("data/output.json")
    """

    def __init__(self, logger: Logger | None = None) -> None:
        """
        Initialize file handler.

        Args:
            logger: Optional Logger instance for logging operations.
        """
        self.logger = logger or Logger()

    def get_parent_path(
        self,
        levels_up: int = 1,
        start_path: PathLike | None = None
    ) -> Path:
        """
        Get path to parent directory N levels up from CALLER's script location.

        Uses inspect to find where YOUR script is located, not utils.py!
        Returns Path object so you can use with ANY save method.

        Args:
            levels_up: Number of parent levels to navigate up (default: 1)
            start_path: Starting point (default: caller's script directory)

        Returns:
            Path object pointing to parent directory

        Raises:
            ValueError: If levels_up is negative

        Example:
            >>> # Your script: my-project/src/scripts/process.py
            >>> 
            >>> handler = FileHandler()
            >>> 
            >>> # Get my-project/ (2 levels up: scripts → src → my-project)
            >>> project_dir = handler.get_parent_path(levels_up=2)
            >>> print(project_dir)
            /home/user/my-project
            >>> 
            >>> # Use with FileHandler
            >>> handler.save_json(data, project_dir / "output.json")
            >>> 
            >>> # Use with DataSaver
            >>> from haashi_pkg.data_engine import DataSaver
            >>> saver = DataSaver()
            >>> saver.save_csv(df, project_dir / "data.csv")
        """
        if levels_up < 0:
            raise ValueError(
                f"levels_up must be non-negative, got {levels_up}")

        if start_path is None:
            # Get the CALLER's file location using inspect
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back
                caller_file = caller_frame.f_globals.get('__file__')

                if caller_file:
                    current = Path(caller_file).resolve().parent
                else:
                    # Fallback to current working directory
                    current = Path.cwd()
                    self.logger.debug(
                        "Could not detect caller file, using cwd")
            else:
                current = Path.cwd()
                self.logger.debug(
                    "Could not access caller frame, using cwd")
        else:
            current = Path(start_path).resolve()

        # Navigate up N levels
        for _ in range(levels_up):
            current = current.parent

        self.logger.debug(f"Navigated up {levels_up} levels to: {current}")
        return current

    def get_ancestor_by_name(
        self,
        folder_name: str,
        start_path: PathLike | None = None,
        max_levels: int = 10
    ) -> Path | None:
        """
        Find ancestor directory by folder name, starting from CALLER's location.

        Uses inspect to find where YOUR script is located, then walks up
        the directory tree looking for a folder with the specified name.

        More stable than counting levels - finds folder by exact name.
        Works even if project structure changes!

        Args:
            folder_name: Name of ancestor folder to find (case-sensitive)
            start_path: Starting point (default: caller's script directory)
            max_levels: Maximum levels to search upward (default: 10)

        Returns:
            Path to named ancestor folder, or None if not found within max_levels

        Example:
            >>> # Your script: my-project/src/modules/analysis.py
            >>> 
            >>> handler = FileHandler()
            >>> 
            >>> # Find "my-project" folder by name
            >>> # Starts from analysis.py's location, walks up until found
            >>> project_root = handler.get_ancestor_by_name("my-project")
            >>> print(project_root)
            /home/user/my-project
            >>> 
            >>> # Use with any save method
            >>> if project_root:
            ...     handler.save_json(data, project_root / "output.json")
            ...     # Saves to: my-project/output.json
            >>> 
            >>> # Works even if structure changes!
            >>> # Old: my-project/src/modules/analysis.py
            >>> # New: my-project/lib/src/modules/analysis.py
            >>> # Still finds my-project/ correctly! 
            >>> 

        """
        if start_path is None:
            # Get the CALLER's file location using inspect
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back
                caller_file = caller_frame.f_globals.get('__file__')

                if caller_file:
                    current = Path(caller_file).resolve().parent
                    self.logger.debug(
                        f"Starting search from caller's location: {current}")
                else:
                    # Fallback to current working directory
                    current = Path.cwd()
                    self.logger.debug(
                        "Could not detect caller file, starting from cwd")
            else:
                current = Path.cwd()
                self.logger.debug(
                    "Could not access caller frame, starting from cwd")
        else:
            current = Path(start_path).resolve()

        levels_checked = 0

        # Walk up directory tree
        while levels_checked < max_levels:
            # Check if current folder matches target name
            if current.name == folder_name:
                self.logger.debug(
                    f"Found ancestor '{folder_name}' at: {current} "
                    f"({levels_checked} levels up from caller)"
                )
                return current

            # Move to parent
            parent = current.parent

            # Check if reached filesystem root
            if parent == current:
                self.logger.warning(
                    f"Reached filesystem root without finding '{folder_name}'"
                )
                return None

            current = parent
            levels_checked += 1

        # Max levels reached without finding folder
        self.logger.warning(
            f"Folder '{folder_name}' not found within {max_levels} levels up from caller"
        )
        return None

    def get_script_dir(self) -> Path:
        """
        Get the directory where the executed script is located.

        Returns the directory of the main Python script that was run,
        NOT the current working directory. This ensures files are saved
        with the script regardless of where the command is executed from.

        Returns:
            Path: Directory containing the executed script

        Example:
            >>> # Script location: /home/user/project/process.py
            >>> handler = FileHandler()
            >>> script_dir = handler.get_script_dir()
            >>> print(script_dir)
            /home/user/project
            >>> 
            >>> # Save file in script's directory
            >>> log_path = script_dir / "logs/output.json"
            >>> handler.save_json(data, log_path)
            >>> # Saves to: /home/user/project/logs/output.json
            >>> 
            >>> # Works the same regardless of where you run from:
            >>> # Run from /home/user/project → saves to /home/user/project/logs/
            >>> # Run from /home/user → saves to /home/user/project/logs/
            >>> # Run from anywhere → saves to /home/user/project/logs/

        Note:
            Falls back to current working directory if main script
            cannot be detected (e.g., in interactive Python sessions).
        """

        # Get the main script file that was executed
        if hasattr(sys.modules['__main__'], '__file__'):
            main_file = sys.modules['__main__'].__file__
            if main_file:
                script_dir = Path(main_file).resolve().parent
                self.logger.debug(f"Script directory detected: {script_dir}")
                return script_dir

        # Fallback to current working directory
        fallback = Path.cwd()
        self.logger.warning(
            "Could not detect main script location, using current directory"
        )
        return fallback

    def ensure_writable_path(self, path: PathLike) -> Path:
        """
        Ensure a file path is writable by creating parent directories.

        Args:
            path: File path to validate/create.

        Returns:
            Path object with guaranteed parent directories.

        Raises:
            FileOperationError: If path creation fails.
        """
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        except Exception as e:
            raise FileOperationError(
                f"Failed to create path {path}: {e}") from e

    def ensure_readable_file(self, path: PathLike) -> Path:
        """
        Ensure a file exists and is readable.

        Args:
            path: File path to validate.

        Returns:
            Path object if file exists and is readable.

        Raises:
            FileNotFoundError: If file doesn't exist.
            FileOperationError: If path exists but is not a file.
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise FileOperationError(f"Not a file: {path}")

        return path

    def save_json(
        self,
        data: JsonFormat,
        path: PathLike,
        mode: str = "w",
        indent: int = 4
    ) -> None:
        """
        Save dictionary to JSON file.

        Args:
            data: Dictionary to save.
            path: Destination file path.
            mode: File open mode ('w' for overwrite, 'a' for append - note: 'a' creates invalid JSON).
            indent: JSON indentation level.

        Raises:
            FileOperationError: If save operation fails.
        """
        try:
            path = self.ensure_writable_path(path)
            with open(path, mode) as f:
                json.dump(data, f, indent=indent)
            self.logger.debug(f"JSON saved → {path}")
        except Exception as e:
            raise FileOperationError(
                f"Failed to save JSON to {path}: {e}") from e

    def read_json(self, path: PathLike) -> JsonFormat:
        """
        Read JSON file into dictionary.

        Args:
            path: Path to JSON file.

        Returns:
            Dictionary containing JSON data.

        Raises:
            FileNotFoundError: If file doesn't exist.
            FileOperationError: If JSON is invalid or read fails.
        """
        try:
            path = self.ensure_readable_file(path)
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise FileOperationError(f"Invalid JSON in {path}: {e}") from e
        except Exception as e:
            raise FileOperationError(
                f"Failed to read JSON from {path}: {e}") from e

    def save_txt(
        self,
        data: str,
        path: PathLike,
        mode: str = "w",
        add_newline_prefix: bool = True
    ) -> None:
        """
        Save string to text file.

        Args:
            data: String content to save.
            path: Destination file path.
            mode: File open mode ('w' for overwrite, 'a' for append).
            add_newline_prefix: If True, adds newline before content.

        Raises:
            FileOperationError: If save operation fails.
        """
        try:
            path = self.ensure_writable_path(path)
            with open(path, mode) as f:
                if add_newline_prefix:
                    f.write("\n")
                f.write(data)
            self.logger.debug(f"TXT saved → {path}")
        except Exception as e:
            raise FileOperationError(
                f"Failed to save TXT to {path}: {e}") from e

    def read_txt(self, path: PathLike) -> str:
        """
        Read text file into string.

        Args:
            path: Path to text file.

        Returns:
            String containing file contents.

        Raises:
            FileNotFoundError: If file doesn't exist.
            FileOperationError: If read fails.
        """
        try:
            path = self.ensure_readable_file(path)
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            raise FileOperationError(
                f"Failed to read TXT from {path}: {e}") from e


# ============================================================================
# UI/UX UTILITIES
# ============================================================================

class ScreenUtil:
    """
    Terminal/console screen manipulation utilities.

    Provides:
    - Screen clearing (cross-platform)
    - Line clearing (ANSI escape codes)
    - Loading animations
    - Text wrapping/formatting

    Example:
        >>> screen = ScreenUtil()
        >>> screen.animate(text="Loading data", cycles=3)
        >>> screen.clear_screen(timeout=1.0)
    """

    @staticmethod
    def clear_screen(timeout: float = 0) -> None:
        """
        Clear the terminal screen (cross-platform).

        Args:
            timeout: Seconds to wait before clearing.
        """
        time.sleep(timeout)
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def clear_line(n: int = 1, timeout: float = 0.5) -> None:
        """
        Clear the previous N lines in the terminal using ANSI codes.

        Args:
            n: Number of lines to erase upward.
            timeout: Delay before clearing (for visual effect).

        Note:
            Uses ANSI escape codes:
            - \\033[1A → move cursor up one line
            - \\033[2K → clear entire current line
        """
        time.sleep(timeout)
        for _ in range(n):
            sys.stdout.write("\033[1A")    # Move cursor up
            sys.stdout.write("\r\033[2K")  # Clear line
        sys.stdout.flush()

    @staticmethod
    def animate(
        text: str = "Loading",
        cycles: int = 2,
        delay: float = 0.5
    ) -> None:
        """
        Display a simple CLI loading animation with dots.

        Args:
            text: Prefix text to display (e.g., "Loading").
            cycles: Number of animation cycles (1 cycle = 3 dots).
            delay: Seconds between each dot.

        Example:
            >>> ScreenUtil.animate("Processing", cycles=3, delay=0.3)
            # Output: Processing... Processing... Processing...
        """
        for _ in range(cycles):
            for dots in range(1, 4):
                sys.stdout.write(f'\r{text}{"." * dots}')
                sys.stdout.flush()
                time.sleep(delay)

    @staticmethod
    def wait_and_enter(message: str = "Press Enter to continue...") -> None:
        """
        Pause execution until user presses Enter.

        Useful for interactive scripts that need manual intervention or 
        confirmation between steps. Commonly used in pipelines to review
        output before proceeding.

        Args:
            message: Custom prompt message (default: "Press Enter to continue...")

        Raises:
            KeyboardInterrupt: If user interrupts with Ctrl+C

        Example:
            >>> from haashi_pkg.utility import FileHandler
            >>> 
            >>> handler = FileHandler()
            >>> 
            >>> # Simple pause
            >>> handler.wait_and_enter()
            Press Enter to continue...
            [User presses Enter]
            >>> 
            >>> # Custom message
            >>> handler.wait_and_enter("Review the output above before continuing")
            Review the output above before continuing
            [User presses Enter]
            >>> 
            >>> # Use in pipeline
            >>> def run_pipeline():
            ...     step_1()
            ...     handler.wait_and_enter("Check step 1 output. Press Enter for step 2...")
            ...     step_2()
            ...     handler.wait_and_enter("Check step 2 output. Press Enter to finish...")
            ...     step_3()
        """
        try:
            input(message)
        except KeyboardInterrupt:
            print("\nProcess interrupted by user")
            raise

    @staticmethod
    def format_text(text: str, width: int = 70) -> str:
        """
        Wrap long text to fit within specified character width.

        Args:
            text: Text to wrap.
            width: Maximum characters per line.

        Returns:
            Wrapped text with newlines inserted appropriately.

        Example:
            >>> long_text = "This is a very long line that needs wrapping."
            >>> wrapped = ScreenUtil.format_text(long_text, width=20)
        """
        wrapper = textwrap.TextWrapper(width=width)
        formatted: list[str] = []

        for line in text.split("\n"):
            if not line.strip():
                formatted.append("")
            else:
                formatted.append(wrapper.fill(line))

        return "\n".join(formatted)

    @staticmethod
    def space(lines: int = 1) -> None:
        """
        Print newlines.

        Args:
            lines: Number of newlines to print.

        Example:
            >>> ScreenUtil.space(3)
            >>> # Output:
            >>> # 
            >>> #
        """
        print("\n" * lines, end="")


class Colors:
    """
    ANSI color codes for terminal output

    Usage:
        >>> print(f"{Colors.GREEN}Success!{Colors.RESET}")
        >>> print(f"{Colors.BOLD}{Colors.BLUE}Important{Colors.RESET}")
        >>> print(Colors.error("Error!"))
    """

    # Reset
    RESET = '\033[0m'

    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright text colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'

    @classmethod
    def colored(
            cls, text: str, color: str, style: str | None = None) -> str:
        """
        Return colored text

        Args:
            text: Text to color
            color: Color code
            style: Optional style code

        Returns:
            Colored text string
        """
        if style:
            return f"{style}{color}{text}{cls.RESET}"
        return f"{color}{text}{cls.RESET}"

    # Convenience methods
    @classmethod
    def success(cls, text: str) -> str:
        """Success message (bold green)"""
        return f"{cls.BOLD}{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def error(cls, text: str) -> str:
        """Error message (bold red)"""
        return f"{cls.BOLD}{cls.RED}{text}{cls.RESET}"

    @classmethod
    def warning(cls, text: str) -> str:
        """Warning message (bold yellow)"""
        return f"{cls.BOLD}{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        """Info message (bold blue)"""
        return f"{cls.BOLD}{cls.BLUE}{text}{cls.RESET}"

    @classmethod
    def header(cls, text: str) -> str:
        """Header (bold cyan with underline)"""
        return f"{cls.BOLD}{cls.UNDERLINE}{cls.CYAN}{text}{cls.RESET}"


# ============================================================================
# DATETIME UTILITIES
# ============================================================================

class DateTimeUtil:
    """
    Datetime helper utilities.

    Provides UTC-based time with timezone offset support.

    Example:
        >>> dt_util = DateTimeUtil()
        >>> current_date = dt_util.get_current_time(utc_offset_hours=1, only_date=True)
        >>> timestamp = dt_util.get_current_time(only_date=False)
    """

    @staticmethod
    def get_current_time(
        utc_offset_hours: int = 0,
        string_format: bool = True,
        only_date: bool = True
    ) -> str | datetime:
        """
        Get current time with optional UTC offset.

        Args:
            utc_offset_hours: Hours to offset from UTC (e.g., +1 for WAT/Nigeria).
            only_date: If True, returns only date (YYYY-MM-DD). 
                       If False, returns datetime (YYYY-MM-DD HH:MM:SS).

        Returns:
            Formatted datetime string.

        Example:
            >>> DateTimeUtil.get_current_time(utc_offset_hours=1, only_date=False)
            '2025-02-04 15:30:45'
        """

        format = "%Y-%m-%d %H:%M:%S"
        if only_date and string_format:
            format = "%Y-%m-%d"

        current_time = (datetime.now(timezone.utc) +
                        timedelta(hours=utc_offset_hours))

        return current_time.strftime(format) if string_format else current_time


# ============================================================================
# BENCHMARK UTILITIES
# ============================================================================

class Benchmark:
    """
    Performance benchmarking and timing utilities.

    Provides methods to measure execution time and profile functions.

    Example:
        >>> from haashi_pkg.benchmark import Benchmark
        >>> 
        >>> bench = Benchmark()
        >>> 
        >>> def my_function():
        ...     return sum(range(1000000))
        >>> 
        >>> avg_time = bench.measure_time(my_function, run_times=10)
        [INFO] Average execution time: 0.0234 seconds
        >>> print(f"Function took {avg_time:.4f}s on average")
        Function took 0.0234s on average
    """

    def __init__(self, logger: Logger | None = None) -> None:
        """
        Initialize Benchmark with optional logger.

        Args:
            logger: Optional Logger instance (default: creates INFO logger)
        """
        self.logger = logger or Logger(level=logging.INFO)

    @contextmanager
    def _suppress_output(self):
        with open(os.devnull, "w") as null:
            with redirect_stdout(null), redirect_stderr(null):
                logging.disable(logging.CRITICAL)
                try:
                    yield
                finally:
                    logging.disable(logging.NOTSET)

    def _warmup(
        self,
        func: Callable[[], Any] | None,
        times: int = 3,
        suppress_output: bool = True,
    ) -> None:
        """
        Warm up a function by running it multiple times.

        This is useful for ensuring the function is optimized and ready for benchmarking.

        Args:
            func: Callable function to warm up (must take no arguments)
            times: Number of times to run the function (default: 3)

        """
        # Validate inputs
        if times < 1:
            raise ValueError(f"times must be at least 1, got {times}")

        if not callable(func):
            raise InvalidFunctionError(
                f"Expected callable function, got {type(func).__name__}"
            )

        self.logger.debug(f"Warming up function {times} times...")

        ctx = self._suppress_output() if suppress_output else nullcontext()
        with ctx:
            for _ in range(times):
                func()

        self.logger.debug("Warmup complete.")

    def measure_time(
        self,
        func: Callable[[], Any] | None,
        warmup_times: int = 3,
        run_times: int = 5,
        repeat_times: int = 1,
        suppress_output: bool = True,
    ) -> float:
        """
        Measure average execution time of a function.

        Runs the function multiple times and returns the average execution time.
        Useful for performance testing and optimization.

        Args:
            func: Callable function to measure (must take no arguments)
            run_times: Number of times to run for averaging (default: 5)

        Returns:
            Average execution time in seconds (float)

        Raises:
            ValueError: If run_times is less than 1
            InvalidFunctionError: If func is not callable
            BenchmarkError: If function execution fails

        Example:
            >>> bench = Benchmark()
            >>> def expensive_operation():
            ...     result = 0
            ...     for i in range(1000000):
            ...         result += i
            ...     return result
            >>> 
            >>> # Measure with default 5 runs
            >>> time_taken = bench.measure_time(expensive_operation)
            [INFO] Average execution time: 0.0456 seconds
            >>> 
            >>> # Measure with 10 runs for better accuracy
            >>> time_taken = bench.measure_time(expensive_operation, run_times=10)
            [INFO] Average execution time: 0.0449 seconds
        """
        # Validate inputs
        if run_times < 1:
            raise ValueError(f"run_times must be at least 1, got {run_times}")
        if repeat_times < 1:
            raise ValueError(
                f"repeat_times must be at least 1, got {repeat_times}")

        if not callable(func):
            raise InvalidFunctionError(
                f"Expected callable function, got {type(func).__name__}"
            )

        try:

            # Warm up the function
            self._warmup(
                func, times=warmup_times, suppress_output=suppress_output)

            self.logger.debug(f"Running benchmark {run_times} times...")

            # Use timeit for accurate timing

            ctx = self._suppress_output() if suppress_output else nullcontext()
            with ctx:
                times = timeit.repeat(
                    func, number=run_times, repeat=repeat_times)

            average_time = min(times) / run_times

            self.logger.debug(
                f"Average execution time: {average_time:.4f} seconds")

            return average_time

        except InvalidFunctionError:
            # Re-raise our custom exception
            raise

        except Exception as e:
            error_msg = f"Failed to benchmark function: {e!s}"
            self.logger.error(error_msg)
            raise BenchmarkError(error_msg) from e
