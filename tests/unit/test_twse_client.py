"""Unit tests for TWSEClient and its helpers.

All network calls are mocked — no real HTTP requests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from midas.integrations.twse_client import TWSEClient, roc_to_iso


# ---------------------------------------------------------------------------
# roc_to_iso helper
# ---------------------------------------------------------------------------

class TestRocToIso:
    def test_standard_conversion(self) -> None:
        assert roc_to_iso("1150519") == "2026-05-19"

    def test_year_boundary(self) -> None:
        # ROC year 112 = Gregorian 2023
        assert roc_to_iso("1121231") == "2023-12-31"

    def test_non_digit_passthrough(self) -> None:
        # Non-standard format should pass through unchanged
        assert roc_to_iso("2026-01-01") == "2026-01-01"

    def test_wrong_length_passthrough(self) -> None:
        assert roc_to_iso("115051") == "115051"


# ---------------------------------------------------------------------------
# TWSEClient — network methods
# ---------------------------------------------------------------------------

_MI_INDEX_SAMPLE = [
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
]

_STOCK_DAY_ALL_SAMPLE = [
    {
        "Date": "1150519",
        "Code": "2330",
        "Name": "台積電",
        "TradeVolume": "20000000",
        "TradeValue": "5000000000",
        "OpeningPrice": "242.00",
        "HighestPrice": "248.00",
        "LowestPrice": "240.00",
        "ClosingPrice": "245.00",
        "Change": "-3.5000",
        "Transaction": "50000",
    },
    {
        "Date": "1150519",
        "Code": "2317",
        "Name": "鴻海",
        "TradeVolume": "10000000",
        "TradeValue": "1000000000",
        "OpeningPrice": "100.00",
        "HighestPrice": "102.00",
        "LowestPrice": "99.00",
        "ClosingPrice": "101.00",
        "Change": "1.0000",
        "Transaction": "20000",
    },
]


@pytest.fixture()
def client() -> TWSEClient:
    c = TWSEClient()
    # Clear the class-level cache to avoid test interference
    c._stock_day_cache = {}
    return c


class TestGetMarketIndex:
    def test_returns_list_of_dicts(self, client: TWSEClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _MI_INDEX_SAMPLE
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = client.get_market_index()

        mock_get.assert_called_once_with(
            "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX",
            timeout=15,
        )
        assert len(result) == 3
        assert result[0]["指數"] == "發行量加權股價指數"
        assert result[0]["收盤指數"] == "40175.56"

    def test_raises_on_http_error(self, client: TWSEClient) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(Exception, match="500"):
                client.get_market_index()


class TestGetStockDayAll:
    def test_lookup_existing_stock(self, client: TWSEClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _STOCK_DAY_ALL_SAMPLE
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            row = client.lookup_stock("2330", iso_date="2026-05-19")

        assert row is not None
        assert row["ClosingPrice"] == "245.00"
        assert row["Change"] == "-3.5000"

    def test_lookup_missing_stock_returns_none(self, client: TWSEClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _STOCK_DAY_ALL_SAMPLE
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            row = client.lookup_stock("9999", iso_date="2026-05-19")

        assert row is None

    def test_cache_prevents_second_http_call(self, client: TWSEClient) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _STOCK_DAY_ALL_SAMPLE
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp) as mock_get:
            client.lookup_stock("2330", iso_date="2026-05-19")
            client.lookup_stock("2317", iso_date="2026-05-19")

        # Should have called the API only once
        assert mock_get.call_count == 1
