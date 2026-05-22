"""FinancialMetric dataclass, MetricType and Direction enums."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    # Free-tier metrics from TaiwanStockPER (daily, grouped monthly)
    PER = "PER"                           # 本益比
    PBR = "PBR"                           # 股價淨值比
    DIVIDEND_YIELD = "DIVIDEND_YIELD"     # 殖利率
    # Free-tier metrics from TaiwanStockMonthRevenue
    MONTHLY_REVENUE = "MONTHLY_REVENUE"   # 月營收
    REVENUE_YOY = "REVENUE_YOY"           # 月營收年增率

    @property
    def display_name(self) -> str:
        return {
            MetricType.PER: "本益比",
            MetricType.PBR: "股價淨值比",
            MetricType.DIVIDEND_YIELD: "殖利率",
            MetricType.MONTHLY_REVENUE: "月營收",
            MetricType.REVENUE_YOY: "月營收年增率",
        }[self]

    @property
    def unit(self) -> str:
        return {
            MetricType.PER: "倍",
            MetricType.PBR: "倍",
            MetricType.DIVIDEND_YIELD: "%",
            MetricType.MONTHLY_REVENUE: "億元",
            MetricType.REVENUE_YOY: "%",
        }[self]


class Direction(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class FinancialMetric:
    symbol: str
    metric_type: MetricType
    period: str  # 'YYYY-QN', e.g. '2025-Q4'
    value: float | None
    is_unreported: bool
    source_name: str
    fetched_at: datetime
    direction: Direction | None = None
    change_pct: float | None = None
    id: int | None = None
