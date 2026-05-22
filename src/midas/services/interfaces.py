"""Service layer abstract base classes (contracts)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from midas.models.financial_metric import FinancialMetric
from midas.models.market_event import MarketEvent
from midas.models.market_overview import MarketOverview
from midas.models.tracked_stock import TrackedStock


class IWatchlistService(ABC):
    @abstractmethod
    def get_all(self) -> list[TrackedStock]: ...

    @abstractmethod
    def add(self, symbol: str) -> TrackedStock:
        """Raises: ValueError if symbol invalid, WatchlistLimitError if >= 30."""
        ...

    @abstractmethod
    def remove(self, symbol: str) -> None: ...

    @abstractmethod
    def update_memo(self, symbol: str, memo: str) -> None:
        """Raises: ValueError if memo > 500 chars."""
        ...

    @abstractmethod
    def search(self, query: str) -> list[TrackedStock]: ...


class IEventService(ABC):
    @abstractmethod
    def get_today_events(self, symbols: list[str]) -> list[MarketEvent]:
        """Returns events sorted by (event_type_priority ASC, occurred_at DESC)."""
        ...

    @abstractmethod
    def get_events_for_stock(self, symbol: str, date: str) -> list[MarketEvent]:
        """date format: YYYY-MM-DD."""
        ...


class IFinancialService(ABC):
    @abstractmethod
    def get_metrics(
        self, symbol: str, quarters: int = 12
    ) -> dict[str, list[FinancialMetric]]:
        """Returns dict keyed by MetricType value, values are quarter-ordered (oldest first)."""
        ...


class IMarketService(ABC):
    @abstractmethod
    def get_today_overview(self) -> Optional[MarketOverview]:
        """Returns None if no data available."""
        ...


class IUpdateService(ABC):
    @abstractmethod
    def check_needs_update(self) -> bool: ...

    @abstractmethod
    def start_background_update(self) -> None: ...
