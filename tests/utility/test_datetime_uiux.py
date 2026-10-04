
import re
from datetime import datetime, timedelta

import pytest

from haashi.utility import Colors, DateTime, ScreenUtil


class TestDateTime:
    def test_default_is_date_only(self) -> None:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DateTime.get_current_time())

    def test_full_timestamp_string(self) -> None:
        value = DateTime.get_current_time(only_date=False)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value)

    def test_datetime_is_aware_with_requested_offset(self) -> None:
        value = DateTime.get_current_time(1, string_format=False)
        assert isinstance(value, datetime)
        assert value.utcoffset() == timedelta(hours=1)

    def test_fractional_offsets_and_range(self) -> None:
        assert DateTime.get_current_time(5.5, string_format=False).utcoffset() == timedelta(
            hours=5, minutes=30)
        assert DateTime.get_current_time(14, string_format=False).utcoffset() == timedelta(
            hours=14)
        for bad in (-12.5, 14.5, 99):
            with pytest.raises(ValueError):
                DateTime.get_current_time(bad)


class TestColors:
    def test_colored(self) -> None:
        assert Colors.colored(
            "hi", Colors.RED) == f"{Colors.RED}hi{Colors.RESET}"
        styled = Colors.colored("hi", Colors.RED, Colors.BOLD)
        assert styled == f"{Colors.BOLD}{Colors.RED}hi{Colors.RESET}"
        assert Colors.error("x").startswith(Colors.BOLD + Colors.RED)


class TestScreenUtil:
    def test_format_text_wraps_and_keeps_blank_lines(self) -> None:
        out = ScreenUtil.format_text("aaa bbb ccc\n\nddd", width=7)
        assert out.split("\n") == ["aaa bbb", "ccc", "", "ddd"]

    def test_animate_writes_dots(self, capsys: pytest.CaptureFixture[str]) -> None:
        ScreenUtil.animate("Wait", cycles=1, delay=0)
        out = capsys.readouterr().out
        assert "Wait." in out and "Wait..." in out
