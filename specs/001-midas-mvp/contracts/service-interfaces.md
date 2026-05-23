# Service & Agent Interfaces (Contracts)

**Phase**: 1 — Design
**Date**: 2026-05-19
**Feature**: [spec.md](../spec.md)

這些 ABC 是架構的合約邊界。所有 Service 和 Agent 必須實作對應介面，以確保可 Mock 替換（Testability Gate）。

---

## Service Interfaces

### IWatchlistService

```python
# src/midas/services/interfaces.py
from abc import ABC, abstractmethod
from typing import Optional
from midas.models.tracked_stock import TrackedStock

class IWatchlistService(ABC):
    @abstractmethod
    def get_all(self) -> list[TrackedStock]: ...

    @abstractmethod
    def add(self, symbol: str) -> TrackedStock:
        """Raises: ValueError if symbol invalid, LimitExceededError if >= 30"""
        ...

    @abstractmethod
    def remove(self, symbol: str) -> None: ...

    @abstractmethod
    def update_memo(self, symbol: str, memo: str) -> None:
        """Raises: ValueError if memo > 500 chars"""
        ...

    @abstractmethod
    def search(self, query: str) -> list[TrackedStock]: ...
```

### IEventService

```python
from midas.models.market_event import MarketEvent

class IEventService(ABC):
    @abstractmethod
    def get_today_events(self, symbols: list[str]) -> list[MarketEvent]:
        """Returns events sorted by (event_type_priority ASC, occurred_at DESC)"""
        ...

    @abstractmethod
    def get_events_for_stock(self, symbol: str, date: str) -> list[MarketEvent]:
        """date format: YYYY-MM-DD"""
        ...
```

### IFinancialService

```python
from midas.models.financial_metric import FinancialMetric

class IFinancialService(ABC):
    @abstractmethod
    def get_metrics(self, symbol: str, quarters: int = 12) -> dict[str, list[FinancialMetric]]:
        """Returns dict keyed by MetricType, values are quarter-ordered list (oldest first)"""
        ...
```

### IMarketService

```python
from midas.models.market_overview import MarketOverview

class IMarketService(ABC):
    @abstractmethod
    def get_today_overview(self) -> Optional[MarketOverview]:
        """Returns None if no data available (pre-market or no cache)"""
        ...
```

### IUpdateService

```python
from midas.models.update_job import UpdateJob
from typing import Callable

class IUpdateService(ABC):
    @abstractmethod
    def check_needs_update(self) -> bool:
        """True if post-market (>=15:00) and today's data not yet fetched"""
        ...

    @abstractmethod
    def start_background_update(
        self,
        on_progress: Callable[[int, int, str], None],  # (step, total, label)
        on_complete: Callable[[UpdateJob], None],
        on_error: Callable[[str], None],
    ) -> None: ...

    @abstractmethod
    def get_latest_job(self) -> Optional[UpdateJob]: ...
```

---

## Agent Interfaces

### IMarketAgent

```python
# src/midas/agents/interfaces.py
from abc import ABC, abstractmethod
from midas.models.market_overview import MarketOverview

class IMarketAgent(ABC):
    @abstractmethod
    def fetch_overview(self, trading_date: str) -> MarketOverview:
        """Raises: DataFetchError on failure"""
        ...

    @abstractmethod
    def get_stock_info(self, symbol: str) -> dict:
        """
        Returns {'symbol': str, 'company_name': str, 'industry': str}.
        Used by WatchlistService to retrieve company name on add().
        Raises: DataFetchError if symbol not found.
        """
        ...
```

### IAnnouncementAgent

```python
from midas.models.market_event import MarketEvent

class IAnnouncementAgent(ABC):
    @abstractmethod
    def fetch_announcements(self, symbol: str, date: str) -> list[MarketEvent]:
        """
    Fetches from FinMind TaiwanStockNews. Returns empty list on no events.
    May swallow fetch failures and return empty list for pipeline resilience.
        """
        ...
```

### IFinancialAgent

```python
from midas.models.financial_metric import FinancialMetric

class IFinancialAgent(ABC):
    @abstractmethod
    def fetch_and_calculate(self, symbol: str) -> list[FinancialMetric]:
        """
        Fetches raw data from FinMind, calculates all 5 metrics,
        applies ±5% direction rule. Returns 12 quarters per metric type.
        """
        ...
```

### ISummarizationAgent

```python
from midas.models.market_event import MarketEvent

class ISummarizationAgent(ABC):
    @abstractmethod
    def summarize_events(self, symbol: str, events: list[MarketEvent]) -> list[MarketEvent]:
        """
        Calls LLM once per symbol (batch). Mutates ai_summary + sentiment on each event.
        Returns updated events. Skips if daily LLM quota exceeded.
        """
        ...

    @abstractmethod
    def get_daily_usage(self) -> tuple[int, int]:
        """Returns (calls_made_today, tokens_used_today)"""
        ...
```

### IOrchestrator

```python
from midas.models.update_job import UpdateJob
from typing import Callable

class IOrchestrator(ABC):
    @abstractmethod
    def run(
        self,
        symbols: list[str],
        on_progress: Callable[[int, int, str], None],
    ) -> UpdateJob:
        """
        Code-based orchestration pipeline (NOT LLM-driven).
        Executes: MarketAgent → AnnouncementAgent (per symbol) →
                  FinancialAgent (per symbol, if cache expired) →
                  SummarizationAgent (per symbol with events).
        Returns completed UpdateJob.
        """
        ...
```

---

## Repository Interfaces

```python
# src/midas/repositories/interfaces.py
from abc import ABC, abstractmethod

class ITrackedStockRepository(ABC):
    @abstractmethod
    def get_all(self) -> list: ...
    @abstractmethod
    def insert(self, stock) -> None: ...
    @abstractmethod
    def delete(self, symbol: str) -> None: ...
    @abstractmethod
    def update_memo(self, symbol: str, memo: str) -> None: ...
    @abstractmethod
    def count(self) -> int: ...

class IMarketEventRepository(ABC):
    @abstractmethod
    def get_by_date(self, date: str, symbols: list[str]) -> list: ...
    @abstractmethod
    def get_by_symbol_date(self, symbol: str, date: str) -> list: ...
    @abstractmethod
    def upsert_many(self, events: list) -> None: ...

class IFinancialMetricRepository(ABC):
    @abstractmethod
    def get_by_symbol(self, symbol: str, limit_quarters: int) -> list: ...
    @abstractmethod
    def upsert_many(self, metrics: list) -> None: ...
    @abstractmethod
    def is_cache_valid(self, symbol: str) -> bool: ...

class IMarketOverviewRepository(ABC):
    @abstractmethod
    def get_by_date(self, date: str): ...
    @abstractmethod
    def upsert(self, overview) -> None: ...

class IUpdateJobRepository(ABC):
    @abstractmethod
    def create(self, job) -> int: ...
    @abstractmethod
    def update_progress(self, job_id: int, completed: int, total: int, label: str) -> None: ...
    @abstractmethod
    def complete(self, job_id: int, llm_calls: int, llm_tokens: int) -> None: ...
    @abstractmethod
    def fail(self, job_id: int, error: str) -> None: ...
    @abstractmethod
    def get_latest(self): ...
```

---

## Error Types

```python
# src/midas/utils/errors.py
class MidasError(Exception): pass

class DataFetchError(MidasError):
    """External API / scraping failure"""
    def __init__(self, source: str, reason: str, retryable: bool = True):
        self.source = source
        self.reason = reason
        self.retryable = retryable

class LLMQuotaExceededError(MidasError):
    """Daily LLM call limit reached"""
    pass

class CacheExpiredError(MidasError):
    """Cache exists but is stale"""
    pass

class WatchlistLimitError(MidasError):
    """Watchlist has reached 30-stock limit"""
    pass
```
