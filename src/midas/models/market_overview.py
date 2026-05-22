"""MarketOverview dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketOverview:
    trading_date: str  # YYYY-MM-DD
    taiex_close: float
    taiex_change: float
    taiex_change_pct: float
    volume_b: float  # 成交量（億元）
    sector_rankings: list[dict]  # [{rank, name, change_pct, direction}]
    institutional: dict  # {foreign_net_b, trust_net_b, dealer_net_b}
    source_name: str
    fetched_at: datetime
    volume_5d_avg_b: float | None = None
    id: int | None = None
