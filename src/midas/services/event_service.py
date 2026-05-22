"""EventService: retrieves market events from the repository."""
from __future__ import annotations

from midas.models.market_event import MarketEvent
from midas.repositories.interfaces import IMarketEventRepository
from midas.services.interfaces import IEventService
from midas.utils.trading_date import get_effective_date


class EventService(IEventService):
    """Retrieves and sorts market events for one or many symbols."""

    def __init__(self, repo: IMarketEventRepository) -> None:
        self._repo = repo

    def get_today_events(self, symbols: list[str]) -> list[MarketEvent]:
        """Return today's events for *symbols*, sorted by priority then time."""
        today = get_effective_date()
        events = self._repo.get_today_events_for_symbols(symbols, today)
        return sorted(
            events,
            key=lambda e: (e.event_type.priority, e.occurred_at),
            reverse=False,
        )

    def get_events_for_stock(self, symbol: str, date: str) -> list[MarketEvent]:
        """Return events for a single stock on *date* (YYYY-MM-DD)."""
        events = self._repo.get_by_symbol_date(symbol, date)
        return sorted(
            events,
            key=lambda e: (e.event_type.priority, e.occurred_at),
        )
