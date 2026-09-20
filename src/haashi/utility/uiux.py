# src/haashi/utility/uiux.py

"""Terminal helpers: loading animation, text wrapping, ANSI colors."""

from __future__ import annotations

import sys
import textwrap
import time


class ScreenUtil:
    """Terminal output helpers."""

    @staticmethod
    def animate(text: str = "Loading", cycles: int = 2, delay: float = 0.5) -> None:
        """Display a simple CLI loading animation with dots.

        Args:
            text: Prefix text to display (e.g. "Loading").
            cycles: Number of animation cycles (1 cycle = 3 dots).
            delay: Seconds between each dot.

        Example:
            >>> ScreenUtil.animate("Processing", cycles=3, delay=0.3)
        """
        for _ in range(cycles):
            for dots in range(1, 4):
                sys.stdout.write(f"\r{text}{'.' * dots}")
                sys.stdout.flush()
                time.sleep(delay)

    @staticmethod
    def format_text(text: str, width: int = 70) -> str:
        """Wrap long text to ``width`` characters per line, keeping blank lines.

        Example:
            >>> ScreenUtil.format_text("This is a very long line.", width=10)
            'This is a\\nvery long\\nline.'
        """
        wrapper = textwrap.TextWrapper(width=width)
        lines = [wrapper.fill(line) if line.strip() else ""
                 for line in text.split("\n")]
        return "\n".join(lines)


class Colors:
    """ANSI color codes for terminal output.

    Example:
        >>> print(f"{Colors.GREEN}Success!{Colors.RESET}")
        >>> print(Colors.error("Error!"))
    """

    RESET = "\033[0m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    STRIKETHROUGH = "\033[9m"

    @classmethod
    def colored(cls, text: str, color: str, style: str | None = None) -> str:
        """Wrap ``text`` in a color code (and optional style), then reset."""
        prefix = f"{style}{color}" if style else color
        return f"{prefix}{text}{cls.RESET}"

    @classmethod
    def debug(cls, text: str) -> str:
        """Debug message (dim cyan)."""
        return f"{cls.DIM}{cls.CYAN}{text}{cls.RESET}"

    @classmethod
    def success(cls, text: str) -> str:
        """Success message (bold green)."""
        return f"{cls.BOLD}{cls.GREEN}{text}{cls.RESET}"

    @classmethod
    def error(cls, text: str) -> str:
        """Error message (bold red)."""
        return f"{cls.BOLD}{cls.RED}{text}{cls.RESET}"

    @classmethod
    def warning(cls, text: str) -> str:
        """Warning message (bold yellow)."""
        return f"{cls.BOLD}{cls.YELLOW}{text}{cls.RESET}"

    @classmethod
    def info(cls, text: str) -> str:
        """Info message (bold blue)."""
        return f"{cls.BOLD}{cls.BLUE}{text}{cls.RESET}"

    @classmethod
    def header(cls, text: str) -> str:
        """Header (bold cyan with underline)."""
        return f"{cls.BOLD}{cls.UNDERLINE}{cls.CYAN}{text}{cls.RESET}"
