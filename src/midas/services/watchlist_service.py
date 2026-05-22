"""WatchlistService: manages the user's tracked stock list."""
from __future__ import annotations

import re
from datetime import date, timedelta

from midas.agents.interfaces import IMarketAgent
from midas.exceptions import WatchlistLimitError
from midas.models.tracked_stock import TrackedStock
from midas.repositories.interfaces import ITrackedStockRepository
from midas.services.interfaces import IWatchlistService

_SYMBOL_RE = re.compile(r"^\d{4,6}$")
_WATCHLIST_MAX = 30
_MEMO_MAX_CHARS = 500


class WatchlistService(IWatchlistService):
    """Manages the tracked-stock watchlist with validation and 30-stock cap."""

    def __init__(
        self,
        repo: ITrackedStockRepository,
        market_agent: IMarketAgent,
    ) -> None:
        self._repo = repo
        self._agent = market_agent

    def get_all(self) -> list[TrackedStock]:
        return self._repo.get_all()

    def add(self, symbol: str) -> TrackedStock:
        if not _SYMBOL_RE.match(symbol):
            raise ValueError(f"Invalid symbol '{symbol}': must be 4–6 digits.")

        existing = self._repo.get_all()
        if len(existing) >= _WATCHLIST_MAX:
            raise WatchlistLimitError(
                f"Watchlist is full ({_WATCHLIST_MAX} stocks maximum)."
            )

        # Fetch company name via MarketAgent
        info = self._agent.get_stock_info(symbol)
        company_name: str = info.get("company_name", symbol)

        from datetime import datetime
        from midas.models.tracked_stock import TrackedStock
        stock = TrackedStock(
            symbol=symbol,
            company_name=company_name,
            added_at=datetime.now(),
            memo="",
            sort_order=0,
        )
        self._repo.add(stock)

        # Immediately fetch latest price so the row shows up with data right away
        for days_back in (0, 1, 2, 3, 4, 5):
            try:
                price_date = str(date.today() - timedelta(days=days_back))
                price_info = self._agent.get_latest_price(symbol, price_date)
                if price_info:
                    self._repo.update_price(
                        symbol,
                        price_info["close"],
                        price_info.get("change_pct"),
                        price_info["date"],
                    )
                    stock.last_price = price_info["close"]
                    stock.last_price_change_pct = price_info.get("change_pct")
                    stock.last_price_date = price_info["date"]
                    break
            except Exception:  # noqa: BLE001
                pass

        return stock

    def remove(self, symbol: str) -> None:
        self._repo.remove(symbol)

    def update_memo(self, symbol: str, memo: str) -> None:
        if len(memo) > _MEMO_MAX_CHARS:
            raise ValueError(
                f"Memo exceeds {_MEMO_MAX_CHARS} characters (got {len(memo)})."
            )
        self._repo.update_memo(symbol, memo)

    def search(self, query: str) -> list[TrackedStock]:
        return self._repo.search_by_symbol_or_name(query)
