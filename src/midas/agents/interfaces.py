"""Agent ABC definitions."""
from __future__ import annotations

from abc import ABC, abstractmethod

from midas.models.financial_metric import FinancialMetric
from midas.models.market_event import MarketEvent
from midas.models.market_overview import MarketOverview


class IMarketAgent(ABC):
    @abstractmethod
    def fetch_overview(self, trading_date: str) -> MarketOverview:
        """Raises: DataFetchError on failure."""
        ...

    @abstractmethod
    def get_stock_info(self, symbol: str) -> dict:
        """Returns {'symbol': str, 'company_name': str, 'industry': str}.

        Raises: DataFetchError if the symbol is not found or the API fails.
        """
        ...

    @abstractmethod
    def get_latest_price(self, symbol: str, trading_date: str) -> dict | None:
        """Return latest price info dict or None if unavailable.

        Returns: {'close': float, 'open': float, 'date': str, 'change_pct': float | None}
        """
        ...


class IAnnouncementAgent(ABC):
    @abstractmethod
    def fetch_announcements(self, symbol: str, date: str) -> list[MarketEvent]:
        """Fetches from FinMind TaiwanStockNews. Returns empty list on no events."""
        ...


class IFinancialAgent(ABC):
    @abstractmethod
    def fetch_and_calculate(self, symbol: str) -> list[FinancialMetric]:
        """Fetches raw data from FinMind, calculates all 5 metrics,
        applies ±5% direction rule. Returns up to 12 quarters per metric type.
        """
        ...


class ISummarizationAgent(ABC):
    @abstractmethod
    def summarize_events(
        self, symbol: str, events: list[MarketEvent]
    ) -> list[MarketEvent]:
        """Calls LLM once per symbol (batch). Returns updated events.

        Skips quietly if daily LLM quota is exceeded.
        """
        ...

    @abstractmethod
    def get_daily_usage(self) -> tuple[int, int]:
        """Returns (calls_made_today, tokens_used_today)."""
        ...
