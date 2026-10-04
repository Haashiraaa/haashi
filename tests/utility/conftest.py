
"""Shared pytest fixtures."""

import pytest

from haashi.utility import FileHandler


@pytest.fixture
def fh() -> FileHandler:
    return FileHandler()
