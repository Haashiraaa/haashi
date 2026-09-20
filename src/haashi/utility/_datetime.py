# src/haashi/utility/_datetime.py

"""Timezone-aware "now" helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, overload

_MIN_OFFSET = -12.0
_MAX_OFFSET = 14.0  # UTC+14 (Line Islands) is the highest real offset


class DateTime:
    """Datetime helpers.

    Example:
        >>> DateTime.get_current_time(utc_offset_hours=1)
        '2026-09-19'
        >>> DateTime.get_current_time(5.5, only_date=False)
        '2026-09-19 22:41:07'
        >>> DateTime.get_current_time(1, string_format=False).tzinfo
        datetime.timezone(datetime.timedelta(seconds=3600))
    """

    @classmethod
    def _validate_utc_offset_hours(cls, utc_offset_hours: float) -> float:
        if not _MIN_OFFSET <= utc_offset_hours <= _MAX_OFFSET:
            raise ValueError(
                f"utc_offset_hours must be between {_MIN_OFFSET:g} and "
                f"{_MAX_OFFSET:g}, got {utc_offset_hours}"
            )
        return utc_offset_hours

    @overload
    @classmethod
    def get_current_time(
        cls,
        utc_offset_hours: float = ...,
        string_format: Literal[True] = ...,
        only_date: bool = ...,
    ) -> str: ...

    @overload
    @classmethod
    def get_current_time(
        cls,
        utc_offset_hours: float = ...,
        *,
        string_format: Literal[False],
        only_date: bool = ...,
    ) -> datetime: ...

    @classmethod
    def get_current_time(
        cls,
        utc_offset_hours: float = 0,
        string_format: bool = True,
        only_date: bool = True,
    ) -> str | datetime:
        """Get the current time at a fixed UTC offset.

        Args:
            utc_offset_hours: Offset from UTC, -12 to +14. Fractions are
                allowed (e.g. 5.5 for India).
            string_format: If True return a string, otherwise a
                timezone-aware ``datetime``.
            only_date: With ``string_format=True``: ``YYYY-MM-DD`` when True,
                ``YYYY-MM-DD HH:MM:SS`` when False. Ignored for datetimes.

        Raises:
            ValueError: If the offset is out of range.
        """
        offset = cls._validate_utc_offset_hours(utc_offset_hours)
        now = datetime.now(timezone(timedelta(hours=offset)))
        if not string_format:
            return now
        return now.strftime("%Y-%m-%d" if only_date else "%Y-%m-%d %H:%M:%S")
