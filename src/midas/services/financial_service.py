"""FinancialService: retrieves financial metrics grouped by MetricType."""
from __future__ import annotations

from datetime import datetime

from midas.models.financial_metric import FinancialMetric, MetricType
from midas.repositories.interfaces import IFinancialMetricRepository
from midas.services.interfaces import IFinancialService


class FinancialService(IFinancialService):
    """Provides financial metrics grouped by MetricType, oldest-first per type."""

    def __init__(self, repo: IFinancialMetricRepository) -> None:
        self._repo = repo

    def get_metrics(
        self, symbol: str, quarters: int = 12
    ) -> dict[str, list[FinancialMetric]]:
        """Return a dict keyed by MetricType.value, values sorted oldest-first.

        Excludes the current in-progress month so only complete periods are shown.
        """
        current_ym = datetime.now().strftime("%Y-%m")
        all_metrics = self._repo.get_by_symbol(symbol)
        grouped: dict[str, list[FinancialMetric]] = {
            t.value: [] for t in MetricType
        }
        for m in all_metrics:
            if m.period >= current_ym:  # skip current incomplete month
                continue
            key = m.metric_type.value
            grouped.setdefault(key, []).append(m)

        # Sort each group oldest-first and trim to requested quarters
        for key in grouped:
            grouped[key] = sorted(grouped[key], key=lambda m: m.period)[-quarters:]

        return grouped
