

# __init__.py
"""
Utility Module for haashi_pkg
==============================

Provides utility classes for common operations including logging, file I/O,
screen manipulation, datetime helpers, and clipboard operations.

Main Classes:
    Logger: Console logging with multiple log levels and JSON error persistence
    ErrorLogger: JSON-based error logging with automatic rotation
    FileHandler: File operations (JSON, TXT) with validation
    ScreenUtil: Terminal screen manipulation and animations
    DateTimeUtil: Datetime utilities and formatting
    ClipboardUtil: Termux clipboard operations (Android)
    
Legacy Class (Deprecated):
    Utility: Backward-compatible wrapper for all utilities
             Will be removed in version 2.0.0

Custom Exceptions:
    UtilityError: Base exception for utility errors
    FileOperationError: File operation failures
    ClipboardError: Clipboard operation failures (Termux-specific)

Recommended Usage (Modern):
    >>> from haashi_pkg.utility import Logger, FileHandler
    >>> import logging
    >>> 
    >>> logger = Logger(level=logging.INFO)
    >>> file_handler = FileHandler(logger=logger)
    >>> 
    >>> logger.info("Processing started")
    >>> data = file_handler.read_json("config.json")
    >>> file_handler.save_json(results, "output.json")

Legacy Usage (Deprecated - still works with warnings):
    >>> from haashi_pkg.utility import Utility
    >>> 
    >>> ut = Utility(level=logging.INFO)
    >>> ut.info("Processing started")
    >>> data = ut.read_json("config.json")
"""

from haashi_pkg.utility.utils import (
    ClipboardError,
    ClipboardUtil,
    Colors,
    DateTimeUtil,
    ErrorLogger,
    FileHandler,
    FileOperationError,
    # Modern classes (recommended)
    Logger,
    ScreenUtil,
    # Legacy class (deprecated)
    Utility,
    # Exceptions
    UtilityError,
)

__all__ = [
    # Modern classes
    'Logger',
    'ErrorLogger',
    'FileHandler',
    'ScreenUtil',
    'DateTimeUtil',
    'ClipboardUtil',
    'Colors',

    # Legacy
    'Utility',

    # Exceptions
    'UtilityError',
    'FileOperationError',
    'ClipboardError',
]

__version__ = '1.5.0'
