"""DashboardViewModel: orchestrates data for the dashboard page."""
from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from midas.models.market_event import MarketEvent
from midas.models.market_overview import MarketOverview
from midas.models.tracked_stock import TrackedStock
from midas.services.interfaces import IEventService, IMarketService, IWatchlistService


class StockEventGroup(NamedTuple):
    """A tracked stock paired with today's events (may be empty)."""
    stock: TrackedStock
    events: list[MarketEvent]
    has_events: bool


class DashboardViewModel:
    """Combines watchlist, events, and market overview for the dashboard."""

    def __init__(
        self,
        market_service: IMarketService,
        event_service: IEventService,
        watchlist_service: IWatchlistService,
    ) -> None:
        self._market_svc = market_service
        self._event_svc = event_service
        self._watchlist_svc = watchlist_service

    def get_today_events(self) -> list[StockEventGroup]:
        """Return StockEventGroups sorted: stocks with events first, then rest.

        Within each stock, events are already ordered by EventService
        (priority ASC, occurred_at ASC).
        """
        stocks = self._watchlist_svc.get_all()
        if not stocks:
            return []

        symbols = [s.symbol for s in stocks]
        events_list = self._event_svc.get_today_events(symbols)

        # Group events by symbol
        by_symbol: dict[str, list[MarketEvent]] = {s.symbol: [] for s in stocks}
        for evt in events_list:
            if evt.symbol in by_symbol:
                by_symbol[evt.symbol].append(evt)

        groups = [
            StockEventGroup(
                stock=s,
                events=by_symbol[s.symbol],
                has_events=bool(by_symbol[s.symbol]),
            )
            for s in stocks
        ]

        # Stocks with events on top, stocks without events at the bottom
        return sorted(groups, key=lambda g: (not g.has_events,))

    def get_market_overview(self) -> MarketOverview | None:
        return self._market_svc.get_today_overview()

    def get_last_update_timestamp(self) -> str:
        overview = self._market_svc.get_today_overview()
        if overview is None:
            return "尚無更新資料"
        ts = overview.fetched_at
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M 更新")
        return str(ts)
