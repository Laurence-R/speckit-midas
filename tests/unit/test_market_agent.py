"""Unit tests for MarketAgent.

All external HTTP calls (TWSEClient, FinMindClient) are mocked.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from midas.agents.market_agent import MarketAgent, _parse_number


# ---------------------------------------------------------------------------
# _parse_number helper
# ---------------------------------------------------------------------------

class TestParseNumber:
    def test_plain_float(self) -> None:
        assert _parse_number("40175.56") == pytest.approx(40175.56)

    def test_comma_formatted(self) -> None:
        assert _parse_number("1,234.56") == pytest.approx(1234.56)

    def test_negative(self) -> None:
        assert _parse_number("-1.75") == pytest.approx(-1.75)

    def test_dash_returns_zero(self) -> None:
        assert _parse_number("--") == 0.0

    def test_empty_returns_zero(self) -> None:
        assert _parse_number("") == 0.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MI_INDEX_ROWS = [
    {
        "日期": "1150519",
        "指數": "發行量加權股價指數",
        "收盤指數": "40175.56",
        "漲跌": "-",
        "漲跌點數": "716.26",
        "漲跌百分比": "-1.75",
    },
    {
        "日期": "1150519",
        "指數": "半導體類指數",
        "收盤指數": "1234.56",
        "漲跌": "+",
        "漲跌點數": "15.00",
        "漲跌百分比": "1.23",
    },
    {
        "日期": "1150519",
        "指數": "金融保險類指數",
        "收盤指數": "2100.00",
        "漲跌": "-",
        "漲跌點數": "10.50",
        "漲跌百分比": "-0.50",
    },
    {
        # total-return variant — should be excluded from sector rankings
        "日期": "1150519",
        "指數": "半導體類報酬指數",
        "收盤指數": "9999.00",
        "漲跌": "+",
        "漲跌點數": "100.00",
        "漲跌百分比": "1.00",
    },
]

_TAIEX_DAILY_RESPONSE = {
    "data": [
        {
            "date": "2026-05-19",
            "stock_id": "TAIEX",
            "close": 40175.56,
            "open": 40500.00,
            "max": 40600.00,
            "min": 39900.00,
            "spread": -716.26,
            "Trading_money": 305789416200,  # ~3057億
            "Trading_Volume": 10000000000,
            "Trading_turnover": 500000,
        }
    ]
}

_INST_RESPONSE = {
    "data": [
        {"name": "Foreign_Investor", "buy": "200000000000", "sell": "150000000000", "date": "2026-05-19"},
        {"name": "Investment_Trust", "buy": "10000000000", "sell": "8000000000", "date": "2026-05-19"},
        {"name": "Dealer_self", "buy": "5000000000", "sell": "6000000000", "date": "2026-05-19"},
    ]
}

_STOCK_PRICE_2330 = {
    "data": [
        {
            "date": "2026-05-19",
            "stock_id": "2330",
            "Trading_Volume": 20000000,
            "Trading_money": 4900000000,
            "open": 242.0,
            "max": 248.0,
            "min": 240.0,
            "close": 245.0,
            "spread": -3.5,
            "Trading_turnover": 50000,
        }
    ]
}


@pytest.fixture()
def mock_twse() -> MagicMock:
    twse = MagicMock()
    twse.get_market_index.return_value = _MI_INDEX_ROWS
    return twse


@pytest.fixture()
def mock_finmind() -> MagicMock:
    fm = MagicMock()
    fm.get_taiex_daily.return_value = _TAIEX_DAILY_RESPONSE
    fm.get_institutional_investors.return_value = _INST_RESPONSE
    fm.get_stock_price.return_value = _STOCK_PRICE_2330
    return fm


@pytest.fixture()
def agent(mock_finmind: MagicMock, mock_twse: MagicMock) -> MarketAgent:
    return MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)


# ---------------------------------------------------------------------------
# fetch_overview
# ---------------------------------------------------------------------------

class TestFetchOverview:
    def test_taiex_close_parsed_correctly(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        assert ov.taiex_close == pytest.approx(40175.56)

    def test_taiex_change_negative(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        assert ov.taiex_change == pytest.approx(-716.26)

    def test_taiex_change_pct_negative(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        assert ov.taiex_change_pct == pytest.approx(-1.75)

    def test_sector_rankings_populated(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        # 半導體類指數 and 金融保險類指數 should appear; 報酬指數 excluded
        names = [s["name"] for s in ov.sector_rankings]
        assert "半導體" in names
        assert "金融保險" in names
        # Total-return variant must be excluded
        assert "半導體類報酬" not in names

    def test_sector_sorted_descending(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        pcts = [s["change_pct"] for s in ov.sector_rankings]
        assert pcts == sorted(pcts, reverse=True)

    def test_institutional_foreign_net(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        # (200B - 150B) / 1e8 = 500 億
        assert ov.institutional["foreign_investor_net"] == pytest.approx(500.0)

    def test_source_name_is_finmind(self, agent: MarketAgent) -> None:
        ov = agent.fetch_overview("2026-05-19")
        assert ov.source_name == "FinMind"

    def test_missing_taiex_data_returns_zeros(
        self, mock_finmind: MagicMock, mock_twse: MagicMock
    ) -> None:
        mock_finmind.get_taiex_daily.return_value = {"data": []}  # empty
        a = MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)
        ov = a.fetch_overview("2026-05-19")
        assert ov.taiex_close == 0.0
        assert ov.taiex_change == 0.0

    def test_propagates_taiex_fetch_exception(
        self, mock_finmind: MagicMock, mock_twse: MagicMock
    ) -> None:
        mock_finmind.get_taiex_daily.side_effect = RuntimeError("network error")
        a = MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)
        with pytest.raises(RuntimeError, match="network error"):
            a.fetch_overview("2026-05-19")

    def test_twse_failure_does_not_propagate(
        self, mock_finmind: MagicMock, mock_twse: MagicMock
    ) -> None:
        mock_twse.get_market_index.side_effect = RuntimeError("network error")
        a = MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)
        ov = a.fetch_overview("2026-05-19")  # should NOT raise
        assert ov.taiex_close == pytest.approx(40175.56)  # FinMind data still available
        assert ov.sector_rankings == []  # sectors empty on TWSE failure


# ---------------------------------------------------------------------------
# get_latest_price
# ---------------------------------------------------------------------------

class TestGetLatestPrice:
    def test_returns_close_price(self, agent: MarketAgent) -> None:
        result = agent.get_latest_price("2330", "2026-05-19")
        assert result is not None
        assert result["close"] == pytest.approx(245.0)

    def test_returns_open_price(self, agent: MarketAgent) -> None:
        result = agent.get_latest_price("2330", "2026-05-19")
        assert result["open"] == pytest.approx(242.0)

    def test_change_pct_calculated(self, agent: MarketAgent) -> None:
        # spread=-3.5, close=245 → prev_close=248.5 → change_pct=-3.5/248.5*100 ≈ -1.41
        result = agent.get_latest_price("2330", "2026-05-19")
        assert result["change_pct"] == pytest.approx(-1.41, abs=0.01)

    def test_date_returned_from_finmind(self, agent: MarketAgent) -> None:
        result = agent.get_latest_price("2330", "2026-05-19")
        assert result["date"] == "2026-05-19"

    def test_returns_none_when_stock_not_found(
        self, mock_finmind: MagicMock, mock_twse: MagicMock
    ) -> None:
        mock_finmind.get_stock_price.return_value = {"data": []}
        a = MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)
        assert a.get_latest_price("9999", "2026-05-19") is None

    def test_returns_none_for_halted_stock(
        self, mock_finmind: MagicMock, mock_twse: MagicMock
    ) -> None:
        mock_finmind.get_stock_price.return_value = {
            "data": [{"date": "2026-05-19", "stock_id": "XXXX", "close": 0, "spread": 0, "open": 0}]
        }
        a = MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)
        assert a.get_latest_price("XXXX", "2026-05-19") is None

    def test_returns_none_on_exception(
        self, mock_finmind: MagicMock, mock_twse: MagicMock
    ) -> None:
        mock_finmind.get_stock_price.side_effect = RuntimeError("boom")
        a = MarketAgent(finmind_client=mock_finmind, twse_client=mock_twse)
        assert a.get_latest_price("2330", "2026-05-19") is None
