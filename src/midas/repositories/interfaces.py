"""Repository ABC definitions for all domain entities."""
from __future__ import annotations

from abc import ABC, abstractmethod

from midas.models.financial_metric import FinancialMetric
from midas.models.market_event import MarketEvent
from midas.models.market_overview import MarketOverview
from midas.models.tracked_stock import TrackedStock
from midas.models.update_job import UpdateJob


class ITrackedStockRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[TrackedStock]: ...

    @abstractmethod
    def get_by_symbol(self, symbol: str) -> TrackedStock | None: ...

    @abstractmethod
    def add(self, stock: TrackedStock) -> None:
        """Uses INSERT OR IGNORE to prevent overwriting added_at on duplicate."""
        ...

    @abstractmethod
    def remove(self, symbol: str) -> None: ...

    @abstractmethod
    def update_memo(self, symbol: str, memo: str) -> None: ...

    @abstractmethod
    def update_price(
        self,
        symbol: str,
        last_price: float,
        last_price_change_pct: float | None,
        last_price_date: str,
    ) -> None:
        """Update last known price fields for a tracked stock."""
        ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def search_by_symbol_or_name(self, query: str) -> list[TrackedStock]: ...


class IAppSettingRepository(ABC):
    @abstractmethod
    def get_value(self, key: str, default: str = "") -> str: ...

    @abstractmethod
    def set_value(self, key: str, value: str) -> None: ...

    @abstractmethod
    def has_value(self, key: str) -> bool: ...


class IMarketEventRepository(ABC):
    @abstractmethod
    def get_by_date(self, date: str, symbols: list[str]) -> list[MarketEvent]: ...

    @abstractmethod
    def get_by_symbol_date(self, symbol: str, date: str) -> list[MarketEvent]: ...

    @abstractmethod
    def get_today_events_for_symbols(
        self, symbols: list[str], date: str
    ) -> list[MarketEvent]: ...

    @abstractmethod
    def upsert_many(self, events: list[MarketEvent]) -> None:
        """Uses INSERT OR IGNORE with UNIQUE(symbol, event_date, source_url)."""
        ...

    @abstractmethod
    def update_summary(self, event: MarketEvent) -> None:
        """Update AI summary, sentiment and generated_at for an existing event."""
        ...


class IFinancialMetricRepository(ABC):
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> list[FinancialMetric]: ...

    @abstractmethod
    def upsert_many(self, metrics: list[FinancialMetric]) -> None: ...


class IMarketOverviewRepository(ABC):
    @abstractmethod
    def get_by_date(self, date: str) -> MarketOverview | None: ...

    @abstractmethod
    def get_latest(self) -> MarketOverview | None: ...

    @abstractmethod
    def upsert(self, overview: MarketOverview) -> None: ...


class IUpdateJobRepository(ABC):
    @abstractmethod
    def create(self, job: UpdateJob) -> int:
        """Persist the job and return the assigned DB id."""
        ...

    @abstractmethod
    def update_progress(
        self,
        job_id: int,
        completed_steps: int,
        total_steps: int,
        label: str = "",
    ) -> None: ...

    @abstractmethod
    def complete(
        self, job_id: int, llm_calls: int = 0, llm_tokens: int = 0
    ) -> None: ...

    @abstractmethod
    def fail(self, job_id: int, error_msg: str) -> None: ...

    @abstractmethod
    def get_latest(self) -> UpdateJob | None: ...

    @abstractmethod
    def get_latest_success(self) -> UpdateJob | None: ...

    @abstractmethod
    def get_history(self, limit: int = 20) -> list[UpdateJob]: ...
