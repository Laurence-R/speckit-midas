"""Unit tests for WatchlistService."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from midas.exceptions import WatchlistLimitError
from midas.models.tracked_stock import TrackedStock
from midas.services.watchlist_service import WatchlistService


def _make_stock(symbol: str, name: str = "Test Corp") -> TrackedStock:
    return TrackedStock(
        symbol=symbol,
        company_name=name,
        added_at=datetime.now(),
        memo="",
        sort_order=0,
    )


@pytest.fixture()
def mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_all.return_value = []
    # add() accepts a TrackedStock and returns None; WatchlistService now returns the stock it built
    repo.add.return_value = None
    return repo


@pytest.fixture()
def mock_agent() -> MagicMock:
    agent = MagicMock()
    agent.get_stock_info.return_value = {
        "symbol": "2330",
        "company_name": "台積電",
        "industry": "半導體",
    }
    return agent


@pytest.fixture()
def svc(mock_repo: MagicMock, mock_agent: MagicMock) -> WatchlistService:
    return WatchlistService(repo=mock_repo, market_agent=mock_agent)


class TestAddSymbol:
    def test_add_valid_4_digit_symbol(
        self, svc: WatchlistService, mock_repo: MagicMock, mock_agent: MagicMock
    ) -> None:
        result = svc.add("2330")
        mock_repo.add.assert_called_once()
        assert result.symbol == "2330"
        assert result.company_name == "台積電"

    def test_add_valid_6_digit_symbol(
        self, svc: WatchlistService, mock_agent: MagicMock
    ) -> None:
        mock_agent.get_stock_info.return_value = {"symbol": "006208", "company_name": "富邦台50"}
        result = svc.add("006208")
        assert result.symbol == "006208"

    def test_invalid_symbol_raises_value_error(self, svc: WatchlistService) -> None:
        with pytest.raises(ValueError):
            svc.add("TSMC")

    def test_3_digit_symbol_raises_value_error(self, svc: WatchlistService) -> None:
        with pytest.raises(ValueError):
            svc.add("233")

    def test_7_digit_symbol_raises_value_error(self, svc: WatchlistService) -> None:
        with pytest.raises(ValueError):
            svc.add("2330000")


class TestWatchlistLimit:
    def test_30_stocks_allowed(
        self, svc: WatchlistService, mock_repo: MagicMock, mock_agent: MagicMock
    ) -> None:
        mock_repo.get_all.return_value = [_make_stock(str(i)) for i in range(30)]
        with pytest.raises(WatchlistLimitError):
            svc.add("9999")

    def test_29_stocks_can_add_one_more(
        self, svc: WatchlistService, mock_repo: MagicMock
    ) -> None:
        mock_repo.get_all.return_value = [_make_stock(str(i)) for i in range(29)]
        # Should NOT raise
        svc.add("9999")


class TestUpdateMemo:
    def test_valid_memo_saved(
        self, svc: WatchlistService, mock_repo: MagicMock
    ) -> None:
        svc.update_memo("2330", "長期持有")
        mock_repo.update_memo.assert_called_once_with("2330", "長期持有")

    def test_501_char_memo_raises_value_error(self, svc: WatchlistService) -> None:
        with pytest.raises(ValueError):
            svc.update_memo("2330", "x" * 501)

    def test_500_char_memo_allowed(
        self, svc: WatchlistService, mock_repo: MagicMock
    ) -> None:
        svc.update_memo("2330", "x" * 500)
        mock_repo.update_memo.assert_called_once()


class TestSearch:
    def test_delegates_to_repo(
        self, svc: WatchlistService, mock_repo: MagicMock
    ) -> None:
        mock_repo.search_by_symbol_or_name.return_value = [_make_stock("2330")]
        result = svc.search("2330")
        mock_repo.search_by_symbol_or_name.assert_called_once_with("2330")
        assert len(result) == 1


class TestRemove:
    def test_delegates_to_repo(
        self, svc: WatchlistService, mock_repo: MagicMock
    ) -> None:
        svc.remove("2330")
        mock_repo.remove.assert_called_once_with("2330")
