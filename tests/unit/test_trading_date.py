"""Unit tests for midas.utils.trading_date.get_effective_date()."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

from midas.utils.trading_date import get_effective_date, _UPDATE_HOUR


def _today() -> str:
    return str(date.today())


def _yesterday() -> str:
    return str(date.today() - timedelta(days=1))


def _mock_now(hour: int, minute: int = 0):
    """Return a datetime with today's date but a specific hour/minute."""
    now = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return now


class TestGetEffectiveDate:
    def test_before_15_returns_yesterday(self) -> None:
        fake_now = _mock_now(hour=8, minute=30)
        with patch("midas.utils.trading_date.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = get_effective_date()
        assert result == _yesterday()

    def test_after_15_returns_today(self) -> None:
        fake_now = _mock_now(hour=16, minute=0)
        with patch("midas.utils.trading_date.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = get_effective_date()
        assert result == _today()

    def test_exactly_15_returns_today(self) -> None:
        """15:00:00 exactly is treated as 'after close'."""
        fake_now = _mock_now(hour=_UPDATE_HOUR, minute=0)
        with patch("midas.utils.trading_date.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = get_effective_date()
        assert result == _today()

    def test_midnight_returns_yesterday(self) -> None:
        fake_now = _mock_now(hour=0, minute=0)
        with patch("midas.utils.trading_date.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = get_effective_date()
        assert result == _yesterday()

    def test_14_59_returns_yesterday(self) -> None:
        fake_now = _mock_now(hour=14, minute=59)
        with patch("midas.utils.trading_date.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = get_effective_date()
        assert result == _yesterday()

    def test_returns_yyyy_mm_dd_format(self) -> None:
        fake_now = _mock_now(hour=16)
        with patch("midas.utils.trading_date.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = get_effective_date()
        # Validate ISO format YYYY-MM-DD
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"
