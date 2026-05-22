"""StockDetailViewModel: loads events and financial metrics for one stock."""
from __future__ import annotations

from midas.models.financial_metric import FinancialMetric
from midas.models.market_event import MarketEvent
from midas.services.interfaces import IEventService, IFinancialService
from midas.utils.trading_date import get_effective_date


class StockDetailViewModel:
    """Provides event and financial data for the stock detail page."""

    def __init__(
        self,
        event_service: IEventService,
        financial_service: IFinancialService,
    ) -> None:
        self._event_svc = event_service
        self._financial_svc = financial_service

    def load_events(
        self, symbol: str, on_date: str | None = None
    ) -> list[MarketEvent]:
        """Load events for *symbol* on *on_date* (default: effective trading date)."""
        target = on_date or get_effective_date()
        return self._event_svc.get_events_for_stock(symbol, target)

    def load_metrics(
        self, symbol: str
    ) -> dict[str, list[FinancialMetric]]:
        """Load last 12 quarters of financial metrics, oldest-first per type."""
        return self._financial_svc.get_metrics(symbol, quarters=12)
