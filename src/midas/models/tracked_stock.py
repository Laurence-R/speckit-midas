"""TrackedStock dataclass."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrackedStock:
    symbol: str
    company_name: str
    added_at: datetime = field(default_factory=datetime.now)
    memo: str = ""
    sort_order: int = 0
    last_price: float | None = None
    last_price_change_pct: float | None = None
    last_price_date: str | None = None
    id: int | None = None
